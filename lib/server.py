import logging
import os
from queue import Queue, Empty
from lib.exceptions import DuplicatedACKError, WindowFullError
from lib.file_controller import FileController
from socket import socket, AF_INET, SOCK_DGRAM
from threading import Thread
from lib.constants import DATA_SIZE, LOCAL_HOST, MAX_TIMEOUT_RETRIES
from lib.constants import READ_MODE, BUFFER_SIZE, TIMEOUT
from lib.constants import WRITE_MODE, DEFAULT_FOLDER, ERROR_EXISTING_FILE
from lib.flags import CLOSE_ACK, HI, HI_ACK, CLOSE
from lib.commands import Command
from lib.message import Message
from lib.selective_repeat import SelectiveRepeatProtocol
from lib.utils import get_file_name, select_protocol
from lib.message_utils import send_close


class Server:
    def __init__(self, ip, port, args):
        self.ip = ip
        self.port = port
        self.clients = {}
        self.protocol = None
        storage = args.storage
        self.storage = storage if storage is not None else DEFAULT_FOLDER

        if not os.path.isdir(self.storage):
            os.makedirs(self.storage, exist_ok=True)

    def start(self):
        self.socket = socket(AF_INET, SOCK_DGRAM)
        self.socket.bind((self.ip, self.port))
        logging.info(f"Server {self.ip} is running on port {self.port}")
        try:
            self.handle_socket_messages()
        except Exception as e:
            logging.error(f"Error in server: {e}")
            raise e

    def handle_socket_messages(self):
        while True:
            encoded_message, client_address = self.socket.recvfrom(BUFFER_SIZE)
            client_port = client_address[1]
            try:
                client_msg_queue = self.clients[client_port]
                client_msg_queue.put(encoded_message)

            except KeyError:  # client not in clients
                client_msg_queue = Queue()
                client_msg_queue.put(encoded_message)
                self.clients[client_port] = client_msg_queue
                args = (encoded_message, client_address, client_msg_queue)
                try:
                    client = Thread(target=self.handle_client_message,
                                    args=args)
                    client.start()
                except Exception as e:
                    logging.error(f"Error in thread {e}")

    def handle_client_message(self, encoded_msg, client_address, msg_queue):
        try:
            encoded_msg = msg_queue.get(block=True, timeout=TIMEOUT)
            decoded_msg = Message.decode(encoded_msg)
            if decoded_msg.flags == HI.encoded:
                self.three_way_handshake(client_address, msg_queue,
                                         decoded_msg)
        except Exception as e:  # possible Empty exception
            logging.error(f"Error handling client message: {e}")
            raise e

    def three_way_handshake(self, client_address, msg_queue, decoded_msg):
        client_port = client_address[1]
        protocol_RDT = decoded_msg.data.decode()
        logging.debug(
            f"Client {client_port}: wants to connect, sending confirmation, "
            + f"message type: {decoded_msg.command}. Protocol: {protocol_RDT}"
        )
        self.protocol = select_protocol(protocol_RDT)
        self.protocol = self.protocol(self.socket)
        self.send_hi_ack(client_address, decoded_msg)

        try:
            print("Antes del queue block en el handshake")
            encoded_message = msg_queue.get(block=True)
            decoded_msg = Message.decode(encoded_message)
            print("Despues del queue block en el handshake")
            if decoded_msg.flags == HI_ACK.encoded:
                self.init_file_transfer_operation(
                    msg_queue, decoded_msg, client_address
                )
            else:
                self.close_client_connection(client_address)
        except Exception as e:
            del self.clients[client_port]
            logging.error(f"Client {client_port}: {e}")
            logging.info(
                f"Client {client_port}: handshake timeout." +
                " Closing connection."
            )
            raise e

    def close_client_connection(self, client_address):
        client_port = client_address[1]
        del self.clients[client_port]
        logging.info(f"Client {client_port}: Timeout or unknown message")

    def init_file_transfer_operation(
        self, client_msg_queue, decoded_msg, client_address
    ):
        client_port = client_address[1]
        logging.info(
            f"Client {client_port}: is online, message type: "
            + f"{decoded_msg.command}"
        )
        self.clients[client_port] = client_msg_queue
        if decoded_msg.command == Command.DOWNLOAD:
            self.handle_download(client_address, client_msg_queue)
        elif decoded_msg.command == Command.UPLOAD:
            self.handle_upload(client_port, client_msg_queue)
        else:
            logging.info(
                f"Client {client_port}: unknown command "
                + "closing connection"
            )
            self.close_client_connection(client_port)
            send_close(self.socket, decoded_msg.command, client_address)

    def send_hi_ack(self, client_address, decoded_msg):
        hi_ack = Message.hi_ack_msg(decoded_msg.command)
        self.socket.sendto(hi_ack, client_address)

    def handle_download(self, client_address, msg_queue):
        client_port = client_address[1]
        msg = self.dequeue_encoded_msg(msg_queue)
        command = msg.command

        file_path = os.path.join(self.storage, msg.file_name)
        if not os.path.exists(file_path):
            self.protocol.send_error(command, client_port, ERROR_EXISTING_FILE)
            logging.error(f"File {msg.file_name} does not exist, try again")
            return
        file_controller = FileController.from_file_name(file_path, READ_MODE)
        data = file_controller.read()
        file_size = file_controller.get_file_size()

        if type(self.protocol) == SelectiveRepeatProtocol:
            args = (msg_queue, client_port,)
            ack_thread = Thread(
                target=self.protocol.receive_acks, args=args
            )
            ack_thread.start()
            self.protocol.set_window_size(int(file_size / DATA_SIZE))
            while file_size > 0:
                try:
                    self.protocol.send(command, client_port,
                                       data, file_controller)
                except WindowFullError:
                    continue
                file_size -= len(data)
                data = file_controller.read()
            ack_thread.join()

            retries = 0
            while retries <= MAX_TIMEOUT_RETRIES:
                try:
                    msg = msg_queue.get(block=True, timeout=1.5)
                    if Message.decode(msg).flags == CLOSE_ACK.encoded:
                        break
                except Empty:
                    logging.error("Timeout! Retrying to send CLOSE...")
                    client_address = (LOCAL_HOST, client_port)
                    close_msg = Message.close_msg(Command.DOWNLOAD)
                    self.socket.sendto(close_msg, client_address)
                    retries += 1
            file_controller.close()
            logging.info(f"Closing connection to client {client_port}")
        else:
            while file_size > 0:
                data_length = len(data)
                try:
                    self.protocol.send(
                        Command.DOWNLOAD,
                        client_port,
                        data,
                        file_controller,
                        lambda: self.dequeue_encoded_msg_download(msg_queue),
                    )
                except DuplicatedACKError:
                    logging.error("Duplicated ACK! Retrying...")
                    continue
                except Empty:
                    logging.error("Timeout! Retrying...")
                    print("Timeout!")
                    continue
                data = file_controller.read()
                file_size -= data_length

        send_close(self.socket, command, client_address)
        retries = 0
        while retries <= MAX_TIMEOUT_RETRIES:
            try:
                msg = msg_queue.get(block=True, timeout=1.5)
                if Message.decode(msg).flags == CLOSE_ACK.encoded:
                    break
            except Empty:
                logging.error("Timeout! Retrying to send CLOSE...")
                client_address = (LOCAL_HOST, client_port)
                close_msg = Message.close_msg(Command.DOWNLOAD)
                self.socket.sendto(close_msg, client_address)
                retries += 1
        file_controller.close()

    def handle_upload(self, client_port, client_msg_queue):
        msg = self.dequeue_encoded_msg(client_msg_queue)  # first upload msg
        file_name = get_file_name(self.storage, msg.file_name)
        logging.info(f"Uploading file to: {file_name}")
        file_controller = FileController.from_file_name(file_name, WRITE_MODE)
        while msg.flags != CLOSE.encoded:
            self.protocol.receive(msg, client_port, file_controller)
            msg = self.dequeue_encoded_msg(client_msg_queue)
        logging.info(f"File {file_name} uploaded, closing connection")
        file_controller.close()

    def dequeue_encoded_msg(self, client_msg_queue):
        # Sacamos el timeout de la cola porque en el upload
        # trababa y no funcionaba.
        # Quiza haya que agregarlo para el download, hay que ponerle
        # timeout en la Queue y manejar la excepcion que se levanta
        # en un except
        encoded_msg = client_msg_queue.get(block=True)
        return Message.decode(encoded_msg)

    def dequeue_encoded_msg_download(self, client_msg_queue):
        encoded_msg = client_msg_queue.get(block=True, timeout=TIMEOUT)

        return Message.decode(encoded_msg)

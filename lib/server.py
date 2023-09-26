import logging
import os
from lib.exceptions import DuplicatedACKError
from lib.file_controller import FileController
from socket import socket, AF_INET, SOCK_DGRAM
from threading import Thread
from queue import Queue
from lib.constants import READ_MODE, TIMEOUT, BUFFER_SIZE
from lib.constants import WRITE_MODE, DEFAULT_FOLDER, ERROR_EXISTING_FILE
from lib.flags import HI, HI_ACK, CLOSE
from lib.commands import Command
from lib.message import Message
from lib.utils import get_file_name, select_protocol


class Server:
    def __init__(self, ip, port, args):
        self.ip = ip
        self.port = port
        self.clients = {}
        self.protocol = select_protocol(args.protocol)
        storage = args.storage
        self.storage = storage if storage is not None else DEFAULT_FOLDER

        if not os.path.isdir(self.storage):
            os.makedirs(self.storage, exist_ok=True)

    def start(self):
        self.socket = socket(AF_INET, SOCK_DGRAM)
        self.socket.bind((self.ip, self.port))
        self.protocol = self.protocol(self.socket)
        logging.info(f"Server {self.ip} is running on port {self.port}")
        self.handle_socket_messages()

    def handle_socket_messages(self):
        while True:
            encoded_message, client_address = self.socket.recvfrom(BUFFER_SIZE)
            client_port = client_address[1]
            try:
                client_msg_queue = self.clients[client_port]
                client_msg_queue.put(encoded_message)
            except KeyError:
                client_msg_queue = Queue()
                client_msg_queue.put(encoded_message)
                self.clients[client_port] = client_msg_queue
                args = (encoded_message, client_address, client_msg_queue)
                Thread(target=self.handle_client_message, args=args).start()

    def handle_client_message(self, encoded_msg, client_address, msg_queue):
        encoded_msg = msg_queue.get()
        decoded_msg = Message.decode(encoded_msg)
        if decoded_msg.flags == HI.encoded:
            self.three_way_handshake(client_address, msg_queue, decoded_msg)

    def three_way_handshake(self, client_address, msg_queue, decoded_msg):
        client_port = client_address[1]
        logging.debug(
            f"Client {client_port}: wants to connect, sending confirmation, " +
            "message type: {decoded_msg.command}")
        self.send_HI_ACK(client_address, decoded_msg)
        try:
            encoded_message = msg_queue.get(block=True, timeout=300)
            decoded_msg = Message.decode(encoded_message)

            if decoded_msg.flags == HI_ACK.encoded:
                self.init_file_transfer_operation(
                    msg_queue, decoded_msg, client_port)
            else:
                self.close_client_connection(
                    decoded_msg.command, client_address)
        except Exception:
            del self.clients[client_port]

    def close_client_connection(self, command, client_address):
        client_port = client_address[1]
        del self.clients[client_port]
        self.send_CLOSE(command, client_address)
        logging.info(f"Client {client_port}: Timeout or unknown message")

    def init_file_transfer_operation(
        self,
        client_msg_queue,
        decoded_msg,
        client_port
    ):
        logging.info(f"Client {client_port}: is online, message type:" +
                     f"{decoded_msg.command}")
        self.clients[client_port] = client_msg_queue
        if decoded_msg.command == Command.DOWNLOAD:
            self.handle_download(client_port, client_msg_queue)
        elif decoded_msg.command == Command.UPLOAD:
            self.handle_upload(client_port, client_msg_queue)
        else:
            logging.info(
                f"Client {client_port}: unknown command " +
                "closing connection")
            self.close_client_connection(decoded_msg.command, client_port)

    def send_HI_ACK(self, client_address, decoded_msg):
        hi_ack = Message.hi_ack_msg(decoded_msg.command)
        self.socket.sendto(hi_ack, client_address)

    def send_CLOSE(self, command, client_address):
        self.socket.sendto(Message.close_msg(command), client_address)

    def handle_download(self, client_port, client_msg_queue):
        logging.debug("ESPERANDO EL MENSAJE")
        msg = self.dequeue_encoded_msg(client_msg_queue)
        logging.debug("LLEGA EL MENSAJE de la cola")
        command = msg.command

        logging.debug(f"El file name es {msg.file_name}")

        file_path = os.path.join(self.storage, msg.file_name)
        if not os.path.exists(file_path):
            self.protocol.send_error(command, client_port, ERROR_EXISTING_FILE)
            logging.error(f"File {msg.file_name} does not exist, try again")
            return
        file_controller = FileController.from_file_name(file_path, READ_MODE)
        data = file_controller.read()
        file_size = file_controller.get_file_size()
        logging.info(f"EL FILE SIZE ES {file_size}")

        while file_size > 0:
            logging.debug("ENTRA EN EL WHILE SEL SERVIDOR")
            # data = file_controller.read()
            # self.protocol.send(command, client_port, data, file_controller)
            # file_size -= len(data)
            data_length = len(data)
            try:
                self.protocol.send(Command.DOWNLOAD, client_port, data,
                                   file_controller)
            except DuplicatedACKError:
                continue
            except TimeoutError:
                logging.error("Timeout! Retrying...")
                print("Timeout!")
                continue
            data = file_controller.read()
            file_size -= data_length

        self.protocol.send(command, client_port, CLOSE.encoded,
                           file_controller)

    def handle_upload(self, client_port, client_msg_queue):
        msg = self.dequeue_encoded_msg(client_msg_queue)  # first upload msg
        file_name = get_file_name(self.storage, msg.file_name)
        logging.info(f"Uploading file to: {file_name}")
        file_controller = FileController.from_file_name(file_name, WRITE_MODE)

        while msg.flags != CLOSE.encoded:
            self.protocol.receive(msg, client_port, file_controller)
            msg = self.dequeue_encoded_msg(client_msg_queue)
        logging.info(f"File {file_name} uploaded successfully")

    def dequeue_encoded_msg(self, client_msg_queue):
        encoded_msg = client_msg_queue.get(block=True, timeout=TIMEOUT)
        return Message.decode(encoded_msg)

import logging
from lib.file_controller import FileController
from lib.log import prepare_logging
from socket import socket, AF_INET, SOCK_DGRAM
from threading import Thread
from queue import Queue
from lib.constants import FIRST_SQN, READ_MODE, TIMEOUT, BUFFER_SIZE, LOCAL_HOST, LOCAL_PORT, WRITE_MODE
from flags import ACK, HI, HI_ACK, CLOSE
from lib.commands import Command
from message import Message
from lib.utils import parse_args_upload, select_protocol


class Server:
    def __init__(self, ip, port, protocol):
        self.ip = ip
        self.port = port
        self.clients = {}
        self.files = []
        self.protocol = select_protocol(protocol)

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
                Thread(target=self.handle_client_message, args=(encoded_message, client_address, client_msg_queue)).start()

    def handle_client_message(self, encoded_message, client_address, client_msg_queue):
        encoded_message = client_msg_queue.get()
        decoded_msg = Message.decode(encoded_message)
        if decoded_msg.flags == HI.encoded:
            self.three_way_handshake(client_address, client_msg_queue, decoded_msg)

    def three_way_handshake(self, client_address, client_msg_queue, decoded_msg):
        client_port = client_address[1]
        logging.debug(f"Client {client_port}: wants to connect, sending confirmation, message type: {decoded_msg.command}")
        self.send_HI_ACK(client_address, decoded_msg)
        try:
            encoded_message = client_msg_queue.get(block=True, timeout=300)
            decoded_msg = Message.decode(encoded_message)

            if decoded_msg.flags == HI_ACK.encoded:
                self.init_file_transfer_operation(client_msg_queue, decoded_msg, client_port)
            else:
                self.close_client_connection(decoded_msg.command, client_address)
        except:
            del self.clients[client_port]

    def close_client_connection(self, command, client_address):
        client_port = client_address[1]
        del self.clients[client_port]
        self.send_CLOSE(command, client_address)
        logging.info(f"Client {client_port}: Timeout or unknown message")

    def init_file_transfer_operation(self, client_msg_queue, decoded_msg, client_port):
        logging.info(f"Client {client_port}: is online, message type: {decoded_msg.command}")
        self.clients[client_port] = client_msg_queue
        if decoded_msg.command == Command.DOWNLOAD:
            self.handle_download(client_port, client_msg_queue)
        elif decoded_msg.command == Command.UPLOAD:
            self.handle_upload(client_port, client_msg_queue)
        else:
            logging.info(f"Client {client_port}: unknown command, closing connection")
            self.close_client_connection(decoded_msg.command, client_port)

    def send_HI_ACK(self, client_address, decoded_msg):
        self.socket.sendto(Message(decoded_msg.command, HI_ACK, 0, None, b"").encode(), client_address)

    def send_CLOSE(self, command, client_address):
        self.socket.sendto(Message(command, CLOSE, 0, "", b"", 0, 0).encode(), client_address)

    def handle_download(self, client_port, client_msg_queue):
        file_name = msg.file_name
        file_controller = FileController.from_file_name(file_name, READ_MODE)
        file_size = file_controller.get_file_size()
    #TODO adaptar al send del protocolo
        while file_size > 0:
            self.protocol.send(msg, client_port, file_controller.read())
            msg = self.dequeue_encoded_msg(client_msg_queue)
            file_size -= BUFFER_SIZE

    def handle_upload(self, client_port, client_msg_queue):
        msg = self.dequeue_encoded_msg(client_msg_queue) #first upload msg
        if msg.file_name not in self.files:
            self.files.append(msg.file_name)
        else:
            logging.info(f"File {msg.file_name} already exists")
            return
        # wait for sqn = 0
        while msg.seq_number != FIRST_SQN:
            self.socket.sendto(Message(msg.command, ACK, 0, None, b"", 0, 0).encode(), (LOCAL_HOST, client_port))
            msg = self.dequeue_encoded_msg(client_msg_queue)

        logging.info(f"Uploading file to: {msg.file_name }")
        file_controller = FileController.from_file_name(msg.file_name, WRITE_MODE)
        while msg.flags != CLOSE.encoded:
            self.protocol.receive(msg, client_port, file_controller)
            msg = self.dequeue_encoded_msg(client_msg_queue)

    def dequeue_encoded_msg(self, client_msg_queue):
        encoded_msg = client_msg_queue.get(block=True, timeout=TIMEOUT)
        return Message.decode(encoded_msg)


if __name__ == "__main__":
    args = parse_args_upload()
    prepare_logging(args)
    server = Server(LOCAL_HOST, LOCAL_PORT, args.protocol)

    server.start()
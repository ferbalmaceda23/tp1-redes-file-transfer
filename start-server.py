import logging
from lib.log import setup_logging
from socket import socket, AF_INET, SOCK_DGRAM
from threading import Thread
from queue import Queue
from lib.constants import TIMEOUT, BUFFER_SIZE
from flags import ACK, HI, HI_ACK, CLOSE
from lib.commands import Command
from message import Message
from lib.utils import parse_args_upload
from time import sleep

LOCAL_HOST = "127.0.0.1"
LOCAL_PORT = 8080

class Server:
    def __init__(self, ip, port):
        self.ip = ip
        self.port = port
        self.clients = {}
        self.files = []

    def start(self):
        self.socket = socket(AF_INET, SOCK_DGRAM)
        self.socket.bind((self.ip, self.port))
        print("before loggin")
        logging.info(f"Server {self.ip} is running on port {self.port}")
        print("after loggin")
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
            self.handle_download(decoded_msg, client_port, client_msg_queue)
        elif decoded_msg.command == Command.UPLOAD:
            self.handle_upload(decoded_msg, client_port, client_msg_queue)

    def send_HI_ACK(self, client_address, decoded_msg):
        self.socket.sendto(Message(decoded_msg.command, HI_ACK, 0, None, b"").encode(), client_address)

    def send_CLOSE(self, command, client_address):
        self.socket.sendto(Message(command, CLOSE, 0, "", b"", 0, 0).encode(), client_address)

    def handle_download(self, msg, client_address, client_msg_queue):
        logging.info(f"Manejo descarga de {msg.file_name}")

    def handle_upload(self, msg, client_port, client_msg_queue):
        if msg.file_name not in self.files:
            self.files.append(msg.file_name)
        else:
            logging.info(f"File {msg.file_name} already exists")
            return
        
        ack_number = 1
        
        logging.info(f"Started receiving file: {msg.file_name}")

        first_upload_msg = client_msg_queue.get(block=True, timeout=TIMEOUT)
        msg = Message.decode(first_upload_msg)
        logging.info(f"Client {client_port}: received {len(msg.data)} bytes, seq_number: {msg.seq_number}")
        # chequear que el SEQ number es el ACK que queremos
        while msg.seq_number != ack_number - 1:
            self.socket.sendto(Message(msg.command, ACK, 0, None, b"", 0, 0).encode(), (LOCAL_HOST, client_port))
            first_upload_msg = client_msg_queue.get(block=True, timeout=TIMEOUT)
            msg = Message.decode(first_upload_msg)
        ack_number += 1
        file.write(msg.data)
        logging.info(f"Client file name: {msg.file_name }")
        with open(msg.file_name, "wb") as file:
            while msg.flags != CLOSE.encoded:
                
                encoded_message = client_msg_queue.get(block=True, timeout=TIMEOUT)
                msg = Message.decode(encoded_message)
                if msg.seq_number != ack_number -1:
                    logging.info(f"Client {client_port}: received {len(msg.data)} bytes, seq_number: {msg.seq_number}")
                    self.socket.sendto(Message(msg.command, ACK, 0, "", b"", 0, ack_number).encode(), (LOCAL_HOST, client_port))
                    continue
                else:
                    file.write(msg.data)
                    ack_number += 1
                    logging.info(f"Client {client_port}: received {len(msg.data)} bytes, seq_number: {msg.seq_number}")
                    self.socket.sendto(Message(msg.command, ACK, 0, "", b"", 0, ack_number).encode(), (LOCAL_HOST, client_port))
                sleep(1)


if __name__ == "__main__":
    args = parse_args_upload()
    setup_logging(args)
    server = Server(LOCAL_HOST, LOCAL_PORT)

    server.start()
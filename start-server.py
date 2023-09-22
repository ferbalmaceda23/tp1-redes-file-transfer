from socket import socket, AF_INET, SOCK_DGRAM
from threading import Thread
from queue import Queue
from lib.constants import TIMEOUT, BUFFER_SIZE
from flags import ACK, HI, HI_ACK, CLOSE
from lib.commands import Command
from lib.log import LOG
from message import Message

LOCAL_HOST = "127.0.0.1"
LOCAL_PORT = 8080

class Server:
    def __init__(self, ip, port):
        self.ip = ip
        self.port = port
        self.clients = {}

    def start(self):
        self.socket = socket(AF_INET, SOCK_DGRAM)
        self.socket.bind((self.ip, self.port))
        LOG.info(f"Server {self.ip} is running on port {self.port}")
        self.handle_socket_messages()
    
    def handle_socket_messages(self):
        while True:
            encoded_message, client_address = self.socket.recvfrom(BUFFER_SIZE) 
            client_port = client_address[1]
            try:
                client_queue = self.clients[client_port]
                client_queue.put(encoded_message)
            except KeyError:
                client_queue = Queue()
                client_queue.put(encoded_message)
                self.clients[client_port] = client_queue
                Thread(target=self.handle_client_message, args=(encoded_message, client_address, client_queue)).start()

    def handle_client_message(self, encoded_message, client_address, client_queue):
        encoded_message = client_queue.get()
        decoded_msg = Message.decode(encoded_message)
        if decoded_msg.flags == HI.encoded:
            self.three_way_handshake(client_address, client_queue, decoded_msg)

    def three_way_handshake(self, client_address, client_queue, decoded_msg):
        client_port = client_address[1]
        LOG.info(f"Client {client_port}: wants to connect, sending confirmation, message type: {decoded_msg.command}")
        self.send_HI_ACK(client_address, decoded_msg)
        try:
            encoded_message = client_queue.get(block=True, timeout=300)
            decoded_msg = Message.decode(encoded_message)

            if decoded_msg.flags == HI_ACK.encoded:
                self.init_file_transfer_operation(client_queue, decoded_msg, client_port)
            else:
                self.close_client_connection(decoded_msg.command, client_address)
        except:
            del self.clients[client_port]

    def close_client_connection(self, command, client_address):
        client_port = client_address[1]
        del self.clients[client_port]
        self.send_CLOSE(command, client_address)
        LOG.info(f"Client {client_port}: Timeout or unknown message")

    def send_CLOSE(self, command, client_address):
        self.socket.sendto(Message(command, CLOSE, 0, "", b"", 0, 0).encode(), client_address)

    def init_file_transfer_operation(self, client_queue, decoded_msg, client_port):
        LOG.info(f"Client {client_port}: is online, message type: {decoded_msg.command}")
        self.clients[client_port] = client_queue
        if decoded_msg.command == Command.DOWNLOAD:
            self.handle_download(decoded_msg, client_port, client_queue)
        elif decoded_msg.command == Command.UPLOAD:
            self.handle_upload(decoded_msg, client_port, client_queue)

    def send_HI_ACK(self, client_address, decoded_msg):
        self.socket.sendto(Message(decoded_msg.command, HI_ACK, 0, None, b"").encode(), client_address)

    def handle_download(self, msg, client_address, client_queue):
        LOG.info(f"Manejo descarga de {msg.file_name}")

    def handle_upload(self, msg, client_port, client_queue):
        LOG.info(f"Started receiving file: {msg.file_name}")

        first_upload_msg = client_queue.get(block=True, timeout=TIMEOUT)
        msg = Message.decode(first_upload_msg)
    
        LOG.info(f"Client file name: {msg.file_name }")
        with open(msg.file_name, "wb") as file:
            while msg.flags != CLOSE.encoded:
                LOG.info(f"Client {client_port} received message: {msg}")
                LOG.info(f"Client {client_port}: received {len(msg.data)} ")
                file.write(msg.data)
                encoded_message = client_queue.get(block=True, timeout=TIMEOUT)
                msg = Message.decode(encoded_message)
                LOG.info(f"Client {client_port}: received close file {msg.file_name}")
                    




if __name__ == "__main__":
    server = Server(LOCAL_HOST, LOCAL_PORT)

    server.start()
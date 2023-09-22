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
                self.init_file_transfer_operation(client_address, client_queue, decoded_msg, client_port)
            else:
                self.close_client_connection(client_address, client_port)
        except:
            del self.clients[client_port]

    def close_client_connection(self, client_address, client_port):
        del self.clients[client_port]
        self.socket.sendto(Message(Command.UPLOAD, CLOSE, 0, "", b"", 0, 0).encode(), client_address)
        LOG.info(f"Cliente {client_port}: Timeout or unknown message")

    def init_file_transfer_operation(self, client_address, client_queue, decoded_msg, client_port):
        LOG.info(f"Client {client_port}: is online, message type: {decoded_msg.command}")
        self.clients[client_port] = client_queue
        if decoded_msg.command == Command.DOWNLOAD:
            self.handle_download(decoded_msg, client_address, client_queue)
        elif decoded_msg.command == Command.UPLOAD:
            self.handle_upload(decoded_msg, client_address, client_queue)

    def send_HI_ACK(self, client_address, decoded_msg):
        self.socket.sendto(Message(decoded_msg.command, HI_ACK, 0, None, b"").encode(), client_address)

    def handle_download(self, msg, client_address, client_queue):
        LOG.info(f"Manejo descarga de {msg.file_name}")

    def handle_upload(self, msg, client_address, client_queue):
        LOG.info(f"Started receiving file: {msg.file_name}")

        #encoded_message = client_queue.get(block=True, timeout=TIMEOUT)
        #msg = Message.decode(encoded_message)
    
        LOG.info(f"Cliente file name es {msg.file_name }")
        with open("image_test.jpg", "wb") as file:
            while True:
                LOG.info(f"Cliente le llego el mensaje {msg}")
                encoded_message = client_queue.get(block=True, timeout=TIMEOUT)
                msg = Message.decode(encoded_message)
                client_port = client_address[1]
                if msg.flags == CLOSE.encoded:
                    # simulo que le mando close
                    LOG.info(f"Cliente {client_port}: received close file {msg.file_name}")
                else:
                    LOG.info(f"Cliente {client_port}: received {len(msg.data)} ")
                    file.write(msg.data)
                    




if __name__ == "__main__":
    server = Server(LOCAL_HOST, LOCAL_PORT)

    server.start()
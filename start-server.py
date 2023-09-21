import logging
from socket import socket, AF_INET, SOCK_DGRAM
from threading import Thread
from queue import Queue
from flags import ACK, HI, HI_ACK, NO_FLAGS, CLOSE
from lib.commands import Command
from lib.log import LOG
from message import Message

LOCAL_HOST = "127.0.0.1"
LOCAL_PORT = 8080
BUFFER_SIZE = 2048

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
            try:
                client_queue = self.clients[client_address[1]]
                client_queue.put(encoded_message)
            except KeyError:
                client_queue = Queue()
                client_queue.put(encoded_message)
                Thread(target=self.handle_client_message, args=(encoded_message, client_address, client_queue)).start()

    def handle_client_message(self, encoded_message, client_address, client_queue):
        while True:
            encoded_message = client_queue.get()
            msg = Message.decode(encoded_message)
            if msg.flags == HI.encoded:
                LOG.info(f"Cliente {client_address[1]}: wants to connect, sending confirmation, message type: {msg.command}")
                self.socket.sendto(Message(msg.command, HI_ACK, 0, None, b"").encode(), client_address)
            elif msg.flags == HI_ACK.encoded:
                LOG.info(f"Cliente {client_address[1]}: is online, message type: {msg.command}")
                self.clients[client_address[1]] = client_queue
            else:
                if msg.command == Command.DOWNLOAD:
                    self.handle_download(msg, client_address, client_queue)
                elif msg.command == Command.UPLOAD:
                    self.handle_upload(msg, client_address, client_queue)
            #sleep(5)??

    def handle_download(self, msg, client_address, client_queue):
        LOG.info(f"Manejo descarga de {msg.file_name}")

    def handle_upload(self, msg, client_address, client_queue):
        LOG.info(f"Start receiving file: {msg.file_name}")
        encoded_message = client_queue.get()
        msg = Message.decode(encoded_message)
        if msg.flags == CLOSE.encoded:
            # simulo que le mando close
            LOG.info(f"Cliente {client_address[1]}: received close file {msg.file_name}")
        else:
            LOG.info(f"Cliente {client_address[1]}: received {msg} ")
            


if __name__ == "__main__":
    server = Server(LOCAL_HOST, LOCAL_PORT)

    server.start()
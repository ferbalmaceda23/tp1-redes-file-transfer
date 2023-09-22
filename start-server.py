from socket import socket, AF_INET, SOCK_DGRAM
from threading import Thread
from queue import Queue
from lib.constants import TIMEOUT
from flags import ACK, HI, HI_ACK, CLOSE
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
                self.clients[client_address[1]] = client_queue
                Thread(target=self.handle_client_message, args=(encoded_message, client_address, client_queue)).start()

    def handle_client_message(self, encoded_message, client_address, client_queue):
        encoded_message = client_queue.get()
        msg = Message.decode(encoded_message)
        if msg.flags == HI.encoded:
            LOG.info(f"Cliente {client_address[1]}: wants to connect, sending confirmation, message type: {msg.command}")
            self.socket.sendto(Message(msg.command, HI_ACK, 0, None, b"").encode(), client_address)
            try:
                encoded_message = client_queue.get(block=True, timeout=300)
                msg = Message.decode(encoded_message)

                if msg.flags == HI_ACK.encoded:
                    LOG.info(f"Cliente {client_address[1]}: is online, message type: {msg.command}")
                    self.clients[client_address[1]] = client_queue
                    if msg.command == Command.DOWNLOAD:
                        self.handle_download(msg, client_address, client_queue)
                    elif msg.command == Command.UPLOAD:
                        self.handle_upload(msg, client_address, client_queue)
                else:
                    del self.clients[client_address[1]]
                    self.socket.sendto(Message(Command.UPLOAD, CLOSE, 0, "", b"", 0, 0).encode(), client_address)
                    LOG.info(f"Cliente {client_address[1]}: Timeout or unknown message")
            except:
                del self.clients[client_address[1]]

            
        #sleep(5)?? zzz

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
                if msg.flags == CLOSE.encoded:
                    # simulo que le mando close
                    LOG.info(f"Cliente {client_address[1]}: received close file {msg.file_name}")
                else:
                    LOG.info(f"Cliente {client_address[1]}: received {len(msg.data)} ")
                    file.write(msg.data)
                    




if __name__ == "__main__":
    server = Server(LOCAL_HOST, LOCAL_PORT)

    server.start()
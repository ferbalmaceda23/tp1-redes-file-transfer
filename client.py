from socket import socket, AF_INET, SOCK_DGRAM
from exceptions import ServerConnectionError
from flags import Flag, HI, CLOSE, ACK, CORRUPTED_PACKAGE, NO_FLAGS
from lib.log import LOG
from message import Message


class Client:
    def __init__(self, ip, port):
        self.ip = ip
        self.port = port
    
    # handshake start
    def connect(self, command):
        self.socket = socket(AF_INET, SOCK_DGRAM)
        #self.socket.settimeout(3)
        self.send(Message(command, HI, 0, "", b""))
        LOG.info("Le mando al server")
        enconded_message, _ = self.socket.recvfrom(2048)
        if self.socket.timeout:
            LOG.error("Server is offline")
            raise ServerConnectionError
        if enconded_message.decode().flags == ACK.encoded:
            LOG.info("Server is online")
            self.socket.send(Message(command, ACK, 0, None, b"").encode(), (self.ip, self.port))
        # handshake end 
        self.start()
    
    def start(self, action):
        action()

    def send(self, message):
        self.socket.sendto(message.encode(), (self.ip, self.port))

# if __name__ == "__main__":
#     client = Client("0.0.0.0", 8080)
#     client.connect()
#     client.start()
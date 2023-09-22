from socket import socket, AF_INET, SOCK_DGRAM
from exceptions import ServerConnectionError
from flags import Flag, HI, HI_ACK, CLOSE, ACK, CORRUPTED_PACKAGE, NO_FLAGS
from lib.constants import BUFFER_SIZE
from lib.log import LOG
from message import Message
import time

class Client:
    def __init__(self, ip, port):
        self.ip = ip
        self.port = port
    
    # handshake start
    def start(self, command, action):
        self.socket = socket(AF_INET, SOCK_DGRAM)
        #self.socket.settimeout(3)
        hi_msg = Message(command, HI, 0, "", b"")
        self.send(hi_msg)
        print(hi_msg)
        LOG.info("Sent HI to server")
        enconded_message, _ = self.socket.recvfrom(BUFFER_SIZE)
        hi_msg = Message.decode(enconded_message)
        if self.socket.timeout:
            LOG.error("Server is offline")
            raise ServerConnectionError
        if hi_msg.flags == HI_ACK.encoded:
            self.send(Message(command, HI_ACK, 0, None, b""))
            LOG.info("Server is online")
        # handshake
        action()

    def send(self, message):
        self.socket.sendto(message.encode(), (self.ip, self.port))

# if __name__ == "__main__":
#     client = Client("0.0.0.0", 8080)
#     client.connect()
#     client.start()
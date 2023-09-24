import logging
from socket import socket, AF_INET, SOCK_DGRAM
from lib.exceptions import ServerConnectionError
from flags import Flag, HI, HI_ACK, CLOSE, ACK, CORRUPTED_PACKAGE, NO_FLAGS
from lib.constants import BUFFER_SIZE
from message import Message
import time

class Client:
    def __init__(self, ip, port):
        self.ip = ip
        self.port = port
    
    # handshake start
    def start(self, command, action):
        self.socket = socket(AF_INET, SOCK_DGRAM)
        #self.socket.settimeout(3) #ajustar timeout
        hi_msg = Message(command, HI, 0, "", b"")
        self.send(hi_msg)
        print(hi_msg)
        logging.info("Sent HI to server")
        try: 
            enconded_message, _ = self.socket.recvfrom(BUFFER_SIZE)
            hi_msg = Message.decode(enconded_message)
        except:
            logging.error("Server is offline")
            raise ServerConnectionError
        if hi_msg.flags == HI_ACK.encoded:
            self.send(Message(command, HI_ACK, 0, None, b""))
            logging.info("Server is online")
        # handshake
        action()

    def send(self, message):
        self.socket.sendto(message.encode(), (self.ip, self.port))
    
    def receive(self):
        return self.socket.recvfrom(BUFFER_SIZE)

# if __name__ == "__main__":
#     client = Client("0.0.0.0", 8080)
#     client.connect()
#     client.start()
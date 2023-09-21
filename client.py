from socket import socket, AF_INET, SOCK_DGRAM
from exceptions import ServerConnectionError
from flags import Flag, HI, HI_ACK, CLOSE, ACK, CORRUPTED_PACKAGE, NO_FLAGS
from lib.log import LOG
from message import Message


class Client:
    def __init__(self, ip, port):
        self.ip = ip
        self.port = port
    
    # handshake start
    def start(self, command, action):
        self.socket = socket(AF_INET, SOCK_DGRAM)
        #self.socket.settimeout(3)
        msg = Message(command, HI, 0, "", b"")
        self.send(msg)
        print(msg)
        LOG.info("Le mando al server")
        enconded_message, _ = self.socket.recvfrom(2048)
        msg = Message.decode(enconded_message)
        if self.socket.timeout:
            LOG.error("Server is offline")
            raise ServerConnectionError
        if msg.flags == HI_ACK.encoded:
            LOG.info("Server is online")
            self.send(Message(command, HI_ACK, 0, None, b""))
        # handshake 
        action()

    def send(self, message):
        self.socket.sendto(message.encode(), (self.ip, self.port))

# if __name__ == "__main__":
#     client = Client("0.0.0.0", 8080)
#     client.connect()
#     client.start()
from socket import socket, AF_INET, SOCK_DGRAM
from exceptions import ServerConnectionError
from flags import Flag, HI, CLOSE, ACK, CORRUPTED_PACKAGE, NO_FLAGS
from message import Message


class Client:
    def __init__(self, ip, port):
        self.ip = ip
        self.port = port
    
    def connect(self, command):
        self.socket = socket(AF_INET, SOCK_DGRAM)
        #self.socket.settimeout(3)
        self.send(Message(command, HI, 0, None, b"").encode())
        enconded_message, _ = self.socket.recvfrom(2048)
        if self.socket.timeout:
            print("Server is offline")
            raise ServerConnectionError
        if enconded_message.decode().flags == ACK.encoded:
            print("Server is online")
            self.socket.send(Message(command, ACK, 0, None, b"").encode(), (self.ip, self.port))
        print("Client started")
    
    def start(self, action):
        action()

    def send(self, message):
        print(message)
        self.socket.sendto(message, (self.ip, self.port))

# if __name__ == "__main__":
#     client = Client("0.0.0.0", 8080)
#     client.connect()
#     client.start()
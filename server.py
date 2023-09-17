from socket import *
from threading import Thread
from time import sleep

class Server:
    def __init__(self, ip, port):
        self.ip = ip
        self.port = port
        self.socket = None

    def start(self):
        self.socket = socket(AF_INET, SOCK_DGRAM)
        self.socket.bind((self.ip, self.port))
        print("Server is running")
        self.handleSocketMessages()
    
    def handleSocketMessages(self):
        while True:
            encodedMessage, clientAddress = self.socket.recvfrom(2048)
            Thread(target=self.handleClientMessage, args=(encodedMessage, clientAddress)).start()

    def handleClientMessage(self, encodedMessage, clientAddress):
        print(f"{clientAddress[1]}: {encodedMessage.decode()}")
        sleep(5)


if __name__ == "__main__":
    server = Server("localhost", 8080)
    server.start()
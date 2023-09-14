import sys
import time
from socket import *
from threading import Thread

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
            message, clientAddress = self.socket.recvfrom(2048)
            Thread(target=self.handleClientMessage, args=(message, clientAddress)).start()

    def handleClientMessage(self, message, clientAddress):
        print(f"{clientAddress}: {message}")
        #time.sleep(5)

if __name__ == "__main__":
    server = Server("localhost", 8080)
    server.start()
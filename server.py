from socket import socket, AF_INET, SOCK_DGRAM
from threading import Thread
from queue import Queue
#from time import sleep

class Server:
    def __init__(self, ip, port):
        self.ip = ip
        self.port = port
        self.clients = {}

    def start(self):
        self.socket = socket(AF_INET, SOCK_DGRAM)
        self.socket.bind((self.ip, self.port))
        print("Server is running")
        self.handleSocketMessages()
    
    def handleSocketMessages(self):
        while True:
            encodedMessage, clientAddress = self.socket.recvfrom(2048)
            try:
                clientQueue = self.clients[clientAddress[1]]
                clientQueue.put(encodedMessage)
            except KeyError:
                clientQueue = Queue()
                self.clients[clientAddress[1]] = clientQueue
                clientQueue.put(encodedMessage)
                Thread(target=self.handleClientMessage, args=(encodedMessage, clientAddress, clientQueue)).start()

    def handleClientMessage(self, encodedMessage, clientAddress, clientQueue):
        while True:
            encodedMessage = clientQueue.get()
            print(f"{clientAddress[1]}: {encodedMessage.decode()}")
        #sleep(5)


if __name__ == "__main__":
    server = Server("localhost", 8080)
    server.start()
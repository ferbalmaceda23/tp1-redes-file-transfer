from socket import socket, AF_INET, SOCK_DGRAM

class Client:
    def __init__(self, ip, port):
        self.ip = ip
        self.port = port
    
    def connect(self):
        self.socket = socket(AF_INET, SOCK_DGRAM)
        print("Client is connected")
    
    def receive_from_terminal(self):
        while True:
            out = input("Write a message: ")
            self.send(out)

    def send(self, message):
        self.socket.sendto(message.encode(),(self.ip, self.port))
        print("sent")


if __name__ == "__main__":
    client = Client("localhost", 8080)
    client.connect()
    client.receive_from_terminal()
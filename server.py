from socket import socket, AF_INET, SOCK_DGRAM
from threading import Thread
from queue import Queue
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
        print(f"Server {self.ip} is running on port {self.port}")
        self.handle_socket_messages()
    
    def handle_socket_messages(self):
        while True:
            encoded_message, client_address = self.socket.recvfrom(BUFFER_SIZE) 
            try:
                client_queue = self.clients[client_address[1]]
                client_queue.put(encoded_message)
            except KeyError:
                client_queue = Queue()
                self.clients[client_address[1]] = client_queue
                client_queue.put(encoded_message)
                Thread(target=self.handle_client_message, args=(encoded_message, client_address, client_queue)).start()

    def handle_client_message(self, encoded_message, client_address, client_queue):
        while True:
            encoded_message = client_queue.get()
            msg = Message.decode(encoded_message)
            print(f"{client_address[1]}: {msg}")
        #sleep(5)??


if __name__ == "__main__":
    server = Server(LOCAL_HOST, LOCAL_PORT)
    server.start()
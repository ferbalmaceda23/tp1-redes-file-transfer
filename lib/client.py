import logging
from socket import socket, AF_INET, SOCK_DGRAM
from lib.exceptions import ServerConnectionError
from lib.flags import HI_ACK
from lib.constants import BUFFER_SIZE
from lib.utils import select_protocol
from lib.message import Message
import time

class Client:
    def __init__(self, ip, port, protocol):
        self.ip = ip
        self.port = port
        self.protocol = select_protocol(protocol)

    # handshake
    def start(self, command, action):
        self.socket = socket(AF_INET, SOCK_DGRAM)
        # self.socket.settimeout(3)
        self.protocol = self.protocol(self.socket)

        self.send_hi_ack_to_server(command, self.protocol)

        try:
            enconded_message, _ = self.socket.recvfrom(BUFFER_SIZE)
            maybe_hi_ack = Message.decode(enconded_message)
        except Exception as e:
            logging.error(f"Server is offline: {e}")
            raise ServerConnectionError

        if maybe_hi_ack.flags == HI_ACK.encoded:
            self.send(Message.hi_ack_msg(command))
            logging.info("Server is online")

        action()

    def send_hi_ack_to_server(self, command, protocol):
        hi_msg = Message.hi_msg(command, protocol)
        self.send(hi_msg)
        logging.info("Sent HI to server")

    def send(self, message):
        self.socket.sendto(message, (self.ip, self.port))

    def receive(self):
        return self.socket.recvfrom(BUFFER_SIZE)

# if __name__ == "__main__":
#     client = Client("0.0.0.0", 8080)
#     client.connect()
#     client.start()

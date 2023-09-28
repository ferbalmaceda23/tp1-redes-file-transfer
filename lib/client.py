import logging
from socket import socket, AF_INET, SOCK_DGRAM
from lib.commands import Command
from lib.exceptions import ServerConnectionError
from lib.flags import HI_ACK
from lib.constants import BUFFER_SIZE, TIMEOUT, MAX_TIMEOUT_RETRIES
from lib.utils import select_protocol
from lib.message import Message


class Client:
    def __init__(self, ip, port, protocol):
        self.ip = ip
        self.port = port
        self.protocol = select_protocol(protocol)

    # handshake
    def start(self, command, action):
        self.socket = socket(AF_INET, SOCK_DGRAM)
        if command == Command.UPLOAD:
            self.socket.settimeout(TIMEOUT)
        self.protocol = self.protocol(self.socket)

        hi_tries = 0
        while hi_tries < MAX_TIMEOUT_RETRIES:
            try:
                self.send_hi_ack_to_server(command, self.protocol)
                enconded_message, _ = self.socket.recvfrom(BUFFER_SIZE)
                maybe_hi_ack = Message.decode(enconded_message)
                break
            except socket.timeout:
                logging.error("Timeout waiting for HI server response. Retrying...")
                hi_tries += 1
            except Exception as e:
                logging.error(f"Server is offline: {e}")
                raise ServerConnectionError

        if hi_tries == MAX_TIMEOUT_RETRIES:
            logging.error("HI response T.O, max retries reached")
            raise ServerConnectionError

        if maybe_hi_ack.flags == HI_ACK.encoded:
            self.send(Message.hi_ack_msg(command))
            logging.info("Connected to server")

        action()

    def send_hi_ack_to_server(self, command, protocol):
        hi_msg = Message.hi_msg(command, protocol)
        self.send(hi_msg)
        logging.info("Sent HI to server")

    def send(self, message):
        self.socket.sendto(message, (self.ip, self.port))

    def receive(self):
        return self.socket.recvfrom(BUFFER_SIZE)

import logging
import socket
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
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        if command == Command.UPLOAD:
            self.socket.settimeout(TIMEOUT)
        self.protocol = self.protocol(self.socket)

        hi_tries = 0
        while hi_tries < MAX_TIMEOUT_RETRIES:
            try:
                self.send_hi_to_server(command, self.protocol)
                print("Waiting for server response...")
                enconded_message, _ = self.socket.recvfrom(BUFFER_SIZE)
                print("Received server response")
                maybe_hi_ack = Message.decode(enconded_message)
                break
                
            except ValueError as e:
                # Manejo específico para la excepción ValueError
                print(f"Error de valor: {e}")
            except TypeError as e:
                # Manejo específico para la excepción TypeError (nunca se ejecutará en este caso)
                print(f"Error de tipo: {e}")
            # except Exception as e:
            #     logging.error(f"Server is offline: {e}")
            #     raise ServerConnectionError
            except socket.timeout:
                logging.error("Timeout waiting for HI server " +
                              "response. Retrying...")
                hi_tries += 1

        if hi_tries == MAX_TIMEOUT_RETRIES:
            logging.error("HI response T.O, max retries reached")
            raise ServerConnectionError

        if maybe_hi_ack.flags == HI_ACK.encoded:
            self.send(Message.hi_ack_msg(command))
            logging.info("Connected to server")

        action()

    def send_hi_to_server(self, command, protocol):
        hi_msg = Message.hi_msg(command, protocol)
        self.send(hi_msg)
        logging.info("Sent HI to server")

    def send(self, message):
        self.socket.sendto(message, (self.ip, self.port))

    def receive(self):
        return self.socket.recvfrom(BUFFER_SIZE)

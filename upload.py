import logging
import os
from time import sleep
from flags import CLOSE, NO_FLAGS
from lib.log import setup_logging
from message import Command, Message
from client import Client
from lib.utils import parse_args_upload
from lib.constants import DATA_SIZE
from lib.file_controller import FileController

def upload(client, path):
    file_name = args.src
    file_size = os.path.getsize(file_name)

    file = FileController(file_name)
    
    with open(file_name, "rb") as file:
        seq_number = 0
        data = file.read(DATA_SIZE)
        while file_size > 0:
            length = len(data)
            if not data:
                client.send(Message(Command.UPLOAD, CLOSE, length, path, data))
                break
            
            logging.debug("Sending {} bytes".format(length))
            msg = Message(Command.UPLOAD, NO_FLAGS,
                        length, path, data, seq_number, 0)
            client.send(msg)
            logging.debug("Sent {} msg with seq_number".format(seq_number))
            sleep(1) #va?
            encoded_message, _ = client.receive()
            msg_received = Message.decode(encoded_message)
            if msg_received.ack_number <= seq_number:
                print("DUPLICATED ACK RECEIVED")
                client.send(msg)
                continue
            else:
                data = file.read(DATA_SIZE)
                seq_number += 1
                file_size -= length
           


if __name__ == "__main__":
    args = parse_args_upload()
    setup_logging(args)
    client = Client(args.host, args.port)
    path = "imagen_nueva.jpg"
    client.start(Command.UPLOAD, lambda: upload(client, path))

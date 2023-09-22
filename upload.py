import os
from lib.log import LOG
from flags import CLOSE, NO_FLAGS
from message import Command, Message
from client import Client
from lib.utils import parse_args_upload
from lib.constants import DATA_SIZE

def upload(client, path):
    file_size = os.path.getsize(args.src)
    with open(args.src, "rb") as file:
        seq_number = 0
        ack_number = 0
        while file_size > 0:
            data = file.read(DATA_SIZE)
            length = len(data)
            if not data:
                client.send(Message(Command.UPLOAD, CLOSE,
                            length, path, data))
            LOG.info("Sending {} bytes".format(length))
            client.send(Message(Command.UPLOAD, NO_FLAGS,
                        length, path, data, seq_number, ack_number))
            file_size -= length
            seq_number += 1
    #TODO agregar esperar al ACK


if __name__ == "__main__":
    args = parse_args_upload()
    client = Client(args.host, args.port)
    path = "imagen_nueva.jpg"
    client.start(Command.UPLOAD, lambda: upload(client, path))

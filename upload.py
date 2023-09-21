import os
from flags import CLOSE, NO_FLAGS
from message import Command, Message
from client import Client
from lib.utils import parse_args_upload
from lib.constants import DATA_SIZE

def upload(client):
    file_size = os.path.getsize(args.src)
    with open(args.src, "rb") as file:
        while file_size > 0:
            data = file.read(DATA_SIZE)
            length = len(data)
            if not data:
                client.send(Message(Command.UPLOAD, CLOSE,
                            length, args.name, data))
                break
            client.send(Message(Command.UPLOAD, NO_FLAGS,
                        length, args.name, data))
            

if __name__ == "__main__":
    args = parse_args_upload()
    client = Client(args.host, args.port)
    client.connect(Command.UPLOAD)
    client.start(lambda: upload(client))

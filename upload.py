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
                            length,  args.name if args.name else args.src, data))
            client.send(Message(Command.UPLOAD, NO_FLAGS,
                        length, args.name if args.name else args.src, data))
            file_size -= length
    
    client.send(Message(Command.UPLOAD, CLOSE, 0, "", b"", 0, 0))


if __name__ == "__main__":
    args = parse_args_upload()
    client = Client(args.host, args.port)
    client.start(Command.UPLOAD, lambda: upload(client))

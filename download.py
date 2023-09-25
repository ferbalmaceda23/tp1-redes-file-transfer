from lib.commands import Command
from lib.file_controller import FileController
from lib.message import Message
import logging
from lib.client import Client
from lib.utils import parse_args_download

def download(client):
    file_controller = FileController(args)
    while True:
        encoded_message, _ = client.receive()
        message = Message.decode(encoded_message)
        ack_number = 1
        if message.command == Command.DOWNLOAD:
            logging.info(f"Received from server to download: ",message.data)
            file_controller.write(message.data)
            
        else:
            logging.error(f"Received unexpected command: {message.command}")

    

if __name__ == "__main__":
    args = parse_args_download()
    client = Client(args.host, args.port)
    client.start(Command.DOWNLOAD, lambda: download(client))
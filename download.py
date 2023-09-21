from click import Command
from client import Client
from lib.utils import parse_args_download

def download(client):
    print(args.src)
    

if __name__ == "__main__":
    args = parse_args_download()
    client = Client(args.host, args.port)
    client.connect(Command.DOWNLOAD)
    client.start(lambda: download(client))
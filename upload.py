from lib.log import prepare_logging
from lib.message import Command
from lib.client import Client
from lib.utils import parse_args_upload


def upload(client):
    client.protocol.upload(args)


if __name__ == "__main__":
    args = parse_args_upload()
    prepare_logging(args)
    client = Client(args.host, args.port, args.protocol)
    client.start(Command.UPLOAD, lambda: upload(client))

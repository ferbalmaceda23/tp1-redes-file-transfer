import logging
from lib.log import prepare_logging
from lib.message import Command
from lib.client import Client
from lib.args_parser import parse_args_upload
import sys


def upload(client):
    client.protocol.upload(args, server_address=client.server_address)


if __name__ == "__main__":
    try:
        args = parse_args_upload()
        prepare_logging(args)
        client = Client(args.host, args.port, args.RDTprotocol)
        client.start(Command.UPLOAD, lambda: upload(client))
    except KeyboardInterrupt:
        print("\nExiting...")
        sys.exit(0)
    except Exception as e:
        logging.error(f"An error occurred. Server is not available. {e}")
        sys.exit(1)

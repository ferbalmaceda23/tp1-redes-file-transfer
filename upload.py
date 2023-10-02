import logging
from lib.constants import LOCAL_PORT
from lib.log import prepare_logging
from lib.message import Command
from lib.client import Client
from lib.args_parser import parse_args_upload
import sys

from lib.message_utils import send_close_and_wait_ack


def upload(client):
    client.protocol.send_file(args)
    # solo funciona con sw arreglar con sr
    send_close_and_wait_ack(socket_=client.socket, msq_queue=None,
                            client_port=LOCAL_PORT, command=Command.UPLOAD)


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

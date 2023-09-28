from lib.commands import Command
from lib.constants import WRITE_MODE
from lib.file_controller import FileController
from lib.message import Message
from lib.log import prepare_logging
from lib.constants import LOCAL_PORT
from lib.client import Client
<<<<<<< HEAD
from lib.args_parser import parse_args_download
from lib.utils import send_ack
from lib.flags import CLOSE, NO_FLAGS
=======
from lib.utils import parse_args_download
from lib.flags import CLOSE, NO_FLAGS, ACK
from lib.message_utils import send_ack
>>>>>>> 312d1f4506ee21549b31e7d4bf5cf76596b315de
import sys
import logging


# TODO: pasar esto a stop and wait
def download(client, args):
    file_controller = FileController.from_args(args.dst, args.name, WRITE_MODE)
    msg_to_send = Message(Command.DOWNLOAD, NO_FLAGS, 0, args.name, b"")
    # msg_to_send = Message.download_msg(args.name)
    client.send(msg_to_send.encode())
    ack_number = 1

    encoded_messge, _ = client.receive()
    message = Message.decode(encoded_messge)
    while message.flags != CLOSE.encoded:
        if message.seq_number > ack_number - 1:
            logging.error("Not expected sqn")
            send_ack(Command.DOWNLOAD, LOCAL_PORT, ack_number - 1, client.socket)
        else:
            logging.info("Received message with sqn: %s", message.seq_number)
            file_controller.write_file(message.data)
            send_ack(Command.DOWNLOAD, LOCAL_PORT, ack_number, client.socket)
            ack_number += 1
        encoded_messge, _ = client.receive()
        message = Message.decode(encoded_messge)
    logging.info("Finished download")


if __name__ == "__main__":
    try:
        args = parse_args_download()
        prepare_logging(args)
        client = Client(args.host, args.port, args.RDTprotocol)
        client.start(Command.DOWNLOAD, lambda: download(client, args))
    except KeyboardInterrupt:
        logging.info("\nExiting...")
        sys.exit(0)
    except Exception as e:
        logging.error(f"An error occurred: {e}")
        sys.exit(1)

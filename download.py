import socket
from lib.commands import Command
from lib.constants import DOWNLOADS_DIR, SELECTIVE_REPEAT
from lib.constants import STOP_AND_WAIT, WRITE_MODE
from lib.exceptions import ServerConnectionError
from lib.file_controller import FileController
from lib.message import Message
from lib.log import prepare_logging
from lib.constants import LOCAL_PORT
from lib.client import Client
from lib.args_parser import parse_args_download
from lib.flags import CLOSE, LIST, NO_FLAGS
import sys
import logging
import os
from lib.utils import get_file_name


def download(client, args):
    if args.files:
        print("Server will show files...")
        show_server_files(client)
        sys.exit(0)

    try:
        if not os.path.isdir(DOWNLOADS_DIR):
            os.makedirs(DOWNLOADS_DIR, exist_ok=True)
        file_name = get_file_name(DOWNLOADS_DIR, args.dst)
        file_controller = FileController.from_file_name(file_name,
                                                        WRITE_MODE)
        download_using_protocol(client, args, file_controller)
    except ServerConnectionError:
        logging.error("Server is offline")
        sys.exit(1)
    except Exception as e:
        logging.error(f"An error occurred: {e}")
        sys.exit(1)


def show_server_files(client):
    msg_to_send = Message(Command.DOWNLOAD, LIST, 0, "", b"")
    client.send(msg_to_send.encode())


def download_using_protocol(client, args, file_controller):
    msg_to_send = Message(Command.DOWNLOAD, NO_FLAGS, 0, args.name, b"")
    # TODO usar el de message
    client.send(msg_to_send.encode())
    encoded_messge = None
    try:
        encoded_messge, _ = client.receive()
    except socket.timeout:
        logging.error("Connection error: HI_ACK not received") # FIXME no es por el HI_ACK solo. Puede ser q se pierda el primer download
        file_controller.delete()
        raise ServerConnectionError

    client.socket.settimeout(None)
    message = Message.decode(encoded_messge)
    while message.flags != CLOSE.encoded:  # TODO se esta perdiendo el close?
        client.protocol.receive(message, LOCAL_PORT, file_controller)
        encoded_messge, _ = client.receive()
        message = Message.decode(encoded_messge)
    client.send(Message.close_ack_msg(Command.DOWNLOAD))
    logging.info("Finished download")
    file_controller.close()


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

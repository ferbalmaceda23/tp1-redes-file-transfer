import socket
from lib.commands import Command
from lib.constants import BUFFER_SIZE, SELECTIVE_REPEAT, STOP_AND_WAIT, TIMEOUT, WRITE_MODE
from lib.exceptions import ServerConnectionError
from lib.file_controller import FileController
from lib.message import Message
from lib.log import prepare_logging
from lib.constants import LOCAL_PORT
from lib.client import Client
from lib.args_parser import parse_args_download
from lib.flags import CLOSE, CLOSE_ACK, NO_FLAGS
import sys
import logging
import os
from lib.utils import get_file_name


# TODO: pasar esto a stop and wait
def download(client, args):
    try:
        if not os.path.isdir("downloads"):
            os.makedirs("downloads", exist_ok=True)
        if args.RDTprotocol == STOP_AND_WAIT:
            download_sw(client, args)
        elif args.RDTprotocol == SELECTIVE_REPEAT:
            download_sr(client, args)
        else:
            logging.error("Invalid RDT protocol")
            sys.exit(1)
    except ServerConnectionError:
        logging.error("Server is offline")
        sys.exit(1)
    except Exception as e:
        print("corre denuevo esto es culpa de fernando")
        logging.error(f"An error occurred: {e}")
        sys.exit(1)

def download_sr(client, args):
    file_name = get_file_name("downloads", args.dst)
    file_controller = FileController.from_file_name(file_name, WRITE_MODE)
    msg_to_send = Message(Command.DOWNLOAD, NO_FLAGS, 0, args.name, b"")
    client.send(msg_to_send.encode())
    client.socket.settimeout(TIMEOUT)  # in case that HI_ACK is lost
    encoded_messge = None
    try:
        encoded_messge, _ = client.receive()
    except socket.timeout:
        logging.error("Connection error: HI_ACK not received")
        raise ServerConnectionError
    client.socket.settimeout(None)
    msg = Message.decode(encoded_messge)
    logging.info(f"Downloading file : {args.name}")
    while msg.flags != CLOSE.encoded:
        client.protocol.receive(msg, args.port, file_controller)
        encoded_messge, _ = client.receive()
        msg = Message.decode(encoded_messge)
    logging.info("Finished download")
    client.send(Message(Command.DOWNLOAD, CLOSE_ACK, 0, "", b"").encode())
    file_controller.close()


################### STOP AND WAIT ###################
def download_sw(client, args):
    file_controller = FileController.from_args(args.dst, args.name, WRITE_MODE)
    msg_to_send = Message(Command.DOWNLOAD, NO_FLAGS, 0, args.name, b"")
    client.send(msg_to_send.encode())
    encoded_messge = None
    try:
        encoded_messge, _ = client.receive()
    except socket.timeout:
        logging.error("Connection error: HI_ACK not received")
        raise ServerConnectionError
    client.socket.settimeout(None)
    message = Message.decode(encoded_messge)
    while message.flags != CLOSE.encoded:  # se esta perdiendo el close
        client.protocol.receive(message, LOCAL_PORT, file_controller)
        encoded_messge, _ = client.receive()
        message = Message.decode(encoded_messge)
    client.send(Message(Command.DOWNLOAD, CLOSE_ACK, 0, "", b"").encode())
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
        raise e
        logging.error(f"An error occurred: {e}")
        sys.exit(1)

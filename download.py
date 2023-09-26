from lib.commands import Command
from lib.constants import LOCAL_HOST, WRITE_MODE
from lib.file_controller import FileController
from lib.message import Message
from lib.log import prepare_logging
from lib.constants import LOCAL_PORT
from lib.client import Client
from lib.utils import parse_args_download
from lib.flags import CLOSE, NO_FLAGS
import logging


def download(client, args):
    file_controller = FileController.from_args(args.dst, args.name, WRITE_MODE)
    msg_to_send = Message(Command.DOWNLOAD, NO_FLAGS, 0,
                      args.name, b"")
    #msg_to_send = Message.download_msg(args.name)
    logging.info("Enviando mensaje para comenzar descarga al servidor :)")
    client.send(msg_to_send.encode())
    ack_number = 1
    logging.info("Enviado")
    
    logging.info("esperando recibir del servidor :)")
    encoded_messge, _ = client.receive()
    message = Message.decode(encoded_messge)
    logging.info("recibido")
    # server debe mandar el tamaño total del archivo para poder
    # finalizar el while
    while message.flags != CLOSE.encoded:
        if message.seq_number > ack_number - 1:
            logging.error("Not expected sqn")
            send_ack(client.socket, Command.DOWNLOAD, ack_number-1, LOCAL_PORT)
        else:
            logging.info("Received message with sqn: %s", message.seq_number)
            file_controller.write_file(message.data)
            send_ack(client.socket, Command.DOWNLOAD, ack_number, LOCAL_PORT)
            ack_number += 1
        encoded_messge, _ = client.receive()
        message = Message.decode(encoded_messge)


def send_ack(socket, command, ack_number, port):
    ack_msg = Message.ack_msg(command, ack_number)
    socket.sendto(ack_msg, (LOCAL_HOST, port))


if __name__ == "__main__":
    args = parse_args_download()
    prepare_logging(args)
    client = Client(args.host, args.port, args.protocol)
    client.start(Command.DOWNLOAD, lambda: download(client, args))

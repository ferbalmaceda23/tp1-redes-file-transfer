import logging
from lib.log import prepare_logging
from message import Command, Message
from client import Client
from lib.utils import parse_args_upload
from lib.constants import DATA_SIZE, LOCAL_PORT
from lib.file_controller import FileController
from lib.commands import Command
from lib.exceptions import DuplicatedACKError


def upload(client):
    file_controller = FileController.from_args(args)
    data = file_controller.read()
    file_size = file_controller.get_file_size()
    while file_size > 0:
        data_length = len(data)
        try:
            client.protocol.send(Command.UPLOAD, LOCAL_PORT, data, file_controller)
        except DuplicatedACKError:
            continue
        data = file_controller.read()
        file_size -= data_length

    """
    while file_size > 0:
        length = len(data)
        if not data:
            client.send(Message(Command.UPLOAD, CLOSE, length, file_controller.file_name, data))
            break
        
        logging.debug("Sending {} bytes".format(length))
        msg = Message(Command.UPLOAD, NO_FLAGS,
                    length, file_controller.file_name, data, seq_number, 0)
        client.send(msg)
        logging.debug("Sent {} msg with seq_number {}".format(seq_number, seq_number))
        sleep(1) #va?
        encoded_message, _ = client.receive()
        msg_received = Message.decode(encoded_message)
        if msg_received.ack_number <= seq_number:
            print("DUPLICATED ACK RECEIVED")
            client.send(msg)
            continue
        else:
            data = file_controller.read(DATA_SIZE)
            file_size -= length
    """


if __name__ == "__main__":
    args = parse_args_upload()
    prepare_logging(args)
    client = Client(args.host, args.port, args.protocol)
    client.start(Command.UPLOAD, lambda: upload(client))
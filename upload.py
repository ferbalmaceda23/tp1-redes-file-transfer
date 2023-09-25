import logging
from lib.log import prepare_logging
from lib.message import Command, Message
from lib.client import Client
from lib.utils import parse_args_upload
from lib.constants import LOCAL_PORT, READ_MODE, SELECTIVE_REPEAT
from lib.file_controller import FileController
from lib.commands import Command
from lib.exceptions import DuplicatedACKError


def upload_sw(protocol):
    file_controller = FileController.from_args(args, READ_MODE)
    data = file_controller.read()
    file_size = file_controller.get_file_size()
    while file_size > 0:
        data_length = len(data)
        try:
            protocol.send(Command.UPLOAD, LOCAL_PORT, data, file_controller)
        except DuplicatedACKError:
            continue
        except TimeoutError:
            logging.error("Timeout! Retrying...")
            print("Timeout!")
            continue
        data = file_controller.read()
        file_size -= data_length

def upload_sr(protocol):
    # TODO 
    pass

def upload(client):
    if(client.protocol.name == SELECTIVE_REPEAT):
        upload_sr(client.protocol)
    else: 
        upload_sw(client.protocol)
    

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
import logging
from lib.commands import Command
from lib.file_controller import FileController
from lib.flags import ACK, NO_FLAGS
from lib.constants import LOCAL_HOST, LOCAL_PORT
from lib.constants import READ_MODE, STOP_AND_WAIT
from lib.message import Message
from lib.exceptions import DuplicatedACKError
from lib.message_utils import receive_encoded_from_socket, send_ack
from lib.log import log_received_msg, log_sent_msg


class StopAndWaitProtocol():
    def __init__(self, socket):
        self.socket = socket
        self.seq_num = 0
        self.ack_num = 1
        self.name = STOP_AND_WAIT

    def receive(self, decoded_msg, port, file_controller):
        print(
            f"decoded_msg.seq_number: {decoded_msg.seq_number} " +
            "and self.ack_num: {self.ack_num}")
        if decoded_msg.seq_number > self.ack_num - 1:
            # it is not the expected sqn
            print("Not expected sqn")
            log_received_msg(decoded_msg, port)
            send_ack(decoded_msg.command, port, self.socket)
        else:
            file_controller.write_file(decoded_msg.data)
            log_received_msg(decoded_msg, port)
            # TEST
            # if decoded_msg.seq_number == 4:
            #     print(
            #         f"{decoded_msg.seq_number}")
            #     time.sleep(6)
            # TEST
            send_ack(decoded_msg.command, port, self.socket)
            self.ack_num += 1

    def send_error(self, command, port, error_msg):
        msg = Message.msg_error(command, error_msg)
        self.socket.sendto(msg.encode(), (LOCAL_HOST, port))
        log_sent_msg(msg, self.seq_num)

    def send(self, command, port, data, file_controller, receive=None):
        msg = Message(command, NO_FLAGS, len(data),
                      file_controller.file_name, data, self.seq_num, 0)
        self.socket.sendto(msg.encode(), (LOCAL_HOST, port))
        log_sent_msg(msg, self.seq_num)
        try:
            if receive:
                msg_received = receive()
            else:
                encoded_message = receive_encoded_from_socket(self.socket)
                msg_received = Message.decode(encoded_message)
            if msg_received.ack_number <= self.seq_num:
                logging.info(f"Client {port}: received duplicated ACK")
                raise DuplicatedACKError
            else:
                self.seq_num += 1
        except TimeoutError:
            logging.error("Timeout sending message")
            raise TimeoutError

    def upload(self, args):
        f_controller = FileController.from_args(args.src, args.name, READ_MODE)
        data = f_controller.read()
        file_size = f_controller.get_file_size()
        while file_size > 0:
            data_length = len(data)
            try:
                self.send(Command.UPLOAD, LOCAL_PORT, data, f_controller)
            except DuplicatedACKError:
                continue
            except TimeoutError:
                logging.error("Timeout! Retrying...")
                continue
            data = f_controller.read()
            file_size -= data_length
        self.socket.sendto(Message.close_msg(Command.UPLOAD),
                           (LOCAL_HOST, LOCAL_PORT))
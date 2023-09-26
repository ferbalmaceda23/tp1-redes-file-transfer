import logging
import threading
from lib.commands import Command
from lib.constants import BUFFER_SIZE, LOCAL_HOST
from lib.constants import LOCAL_PORT, READ_MODE, SELECTIVE_REPEAT
from lib.exceptions import DuplicatedACKError, WindowFullError
from lib.file_controller import FileController
from lib.flags import ACK, NO_FLAGS
from lib.message import Message


class SelectiveRepeatProtocol():
    def __init__(self, socket, N):
        self.socket = socket
        self.seq_num = 0
        self.ack_num = -1  # start with -1 bc first ack will be 0
        self.name = SELECTIVE_REPEAT
        self.send_base = 0  # it is the first packet in the window == its sqn
        self.rcv_base = 0
        self.window_size = N
        self.max_sqn = 0
        self.buffer = []
        self.not_acknowledged = 0  # n° packets sent but not acknowledged yet
        self.not_acknowledged_lock = threading.Lock()

    # Receives acks from server
    def receive_acks(self):
        while True:
            try:
                maybe_ack, _ = self.receive_from_socket()
                msg_received = Message.decode(maybe_ack)
                if msg_received.flags == ACK:
                    with self.not_acknowledged_lock:
                        self.not_acknowledged -= 1
                    self.log_received_msg(msg_received, LOCAL_PORT)
                    if msg_received.ack_number == self.send_base:
                        if self.send_base + self.window_size-1 != self.max_sqn:
                            self.move_send_window()
                        else:
                            logging.debug("Wont move window" +
                                          "because max was reached")
                    else:
                        logging.debug(
                            f"Received messy ACK: {msg_received.ack_number}")
                # TODO q pasa si recivo otro msg q no es ack?
            except Exception:  # TODO
                pass

    def receive_from_socket(self):  # TODO: pasar a otro archivo
        encoded_message, _ = self.socket.recvfrom(BUFFER_SIZE)
        return encoded_message

    def receive(self, decoded_msg, port, file):
        pass

    def send(self, command, port, data, file_controller):
        # TODO ver si aca va lock, creo q no:
        if self.not_acknowledged < self.window_size:
            msg = Message(command, NO_FLAGS, len(data),
                          file_controller.file_name, data, self.seq_num, 0)
            self.socket.sendto(msg.encode(), (LOCAL_HOST, port))
            self.log_sent_msg(msg)
            self.seq_num += 1
            with self.not_acknowledged_lock:
                self.not_acknowledged += 1
        else:
            logging.debug("Window is full, waiting for ACKs...")
            raise WindowFullError

    def upload(self, args):
        f_controller = FileController.from_args(args.src, args.name, READ_MODE)
        file_size = f_controller.get_file_size()
        self.set_window_size(int(file_size/BUFFER_SIZE))
        data = f_controller.read()
        ack_thread = threading.Thread(target=self.receive_acks)

        while file_size > 0:
            data_length = len(data)
            try:
                self.send(Command.UPLOAD, LOCAL_PORT, data, f_controller)
            except DuplicatedACKError:
                continue
            except TimeoutError:
                logging.error("Timeout! Retrying...")
                continue
            except WindowFullError:
                continue
            data = f_controller.read()
            file_size -= data_length
        self.socket.sendto(Message.close_msg(Command.UPLOAD),
                           (LOCAL_HOST, LOCAL_PORT))
        ack_thread.join()

    def move_rcv_window(self):
        self.rcv_base += 1

    def move_send_window(self):
        self.send_base += 1

    def set_window_size(self, number_of_packets):
        self.window_size = self.calculate_window_size(number_of_packets)
        self.max_sqn = number_of_packets - 1

    def calculate_window_size(self, number_of_packets):
        return number_of_packets/2

    def log_received_msg(self, msg, port):  # TODO pasar a otro archivo
        logging.info(
            f"Client {port}: received {len(msg.data)}" +
            f" bytes, seq_number: {msg.seq_number}")

    def log_sent_msg(self, msg):
        logging.debug(
            f"Sent {msg} msg with seq_number {self.seq_num}")

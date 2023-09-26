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
    def __init__(self, socket):
        self.socket = socket
        self.seq_num = 0
        self.name = SELECTIVE_REPEAT
        self.send_base = 0  # it is the first packet in the window == its sqn
        self.rcv_base = 0
        self.window_size = 0
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
                        if self.not_acknowledged > 0:
                            self.not_acknowledged -= 1
                            print(f"not_acknowledged DECREMENTED: {self.not_acknowledged}")
                    self.log_received_msg(msg_received, LOCAL_PORT)
                    if msg_received.ack_number == self.send_base:
                        self.move_send_window()
                    else:
                        logging.debug(
                            f"Received messy ACK: {msg_received.ack_number}")
                # TODO q pasa si recivo otro msg q no es ack?
            except Exception:  # TODO
                pass

    def receive_from_socket(self):  # TODO: pasar a otro archivo
        encoded_message, _ = self.socket.recvfrom(BUFFER_SIZE)
        return encoded_message

    def receive(self, decoded_msg, port, file_controller):
        if decoded_msg.seq_number == self.rcv_base:  # it is the expected sqn
            file_controller.write_file(decoded_msg.data)
            self.log_received_msg(decoded_msg, port)
            self.process_buffer()
        elif self.packet_is_within_window(decoded_msg):
            # it is not the expected sqn order but it is within the window
            self.buffer.append(decoded_msg)
        # otherwise it is not within the window and it is discarded
        # TODO in this case handle timeout in the client

        self.send_ack(decoded_msg.command, port, decoded_msg.seq_number)

    def process_buffer(self, file_controller):
        # write only those buffered pkt that are in order with the base
        # Those who are not in order correspond to other packet loss
        next_base = self.rcv_base + 1
        for packet in self.buffer:
            if packet == next_base:
                file_controller.write_file(packet.data)
                self.buffer.pop(packet)
                next_base += 1
            else:
                break

        self.move_rcv_window(next_base - self.rcv_base)

    def packet_is_within_window(self, decoded_msg):
        max_w_size = self.window_size-1  # TODO revisar -1
        is_before_max = decoded_msg.seq_number <= self.rcv_base + max_w_size
        is_after_base = decoded_msg.seq_number > self.rcv_base
        return is_after_base and is_before_max

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
            # logging.debug("Window is full, waiting for ACKs...")
            raise WindowFullError

    def upload(self, args):
        f_controller = FileController.from_args(args.src, args.name, READ_MODE)
        file_size = f_controller.get_file_size()
        # FIXME no se si esta bien asi:
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

    def move_rcv_window(self, shift):
        if self.rcv_base + self.window_size-1 != self.max_sqn:
            self.rcv_base += shift

    def move_send_window(self):
        if self.send_base + self.window_size-1 != self.max_sqn:
            self.send_base += 1

    def set_window_size(self, number_of_packets):
        self.window_size = self.calculate_window_size(number_of_packets)
        self.max_sqn = number_of_packets - 1
        print(f"Window size: {self.window_size}")

    def calculate_window_size(self, number_of_packets):
        return int(number_of_packets/2)

    def log_received_msg(self, msg, port):  # TODO pasar a otro archivo
        logging.info(
            f"Client {port}: received {len(msg.data)}" +
            f" bytes, seq_number: {msg.seq_number}")

    def log_sent_msg(self, msg):
        logging.debug(
            f"Sent {msg} msg with seq_number {self.seq_num}")

    def send_ack(self, command, port, ack_number):
        # ack_msg = Message.ack_msg(command, self.ack_num)
        # self.socket.sendto(ack_msg, (LOCAL_HOST, port))
        msg = Message(command, ACK, 0, "", b"", 0, ack_number)
        print(f"Sending ACK: {ack_number}")
        self.socket.sendto(msg.encode(), (LOCAL_HOST, port))

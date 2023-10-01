import logging
import socket
from threading import Thread, Lock
from lib.commands import Command
from lib.constants import DATA_SIZE, LOCAL_HOST, MAX_TIMEOUT_RETRIES, TIMEOUT
from lib.constants import LOCAL_PORT, READ_MODE, SELECTIVE_REPEAT
from lib.constants import MAX_WINDOW_SIZE, MAX_ACK_RESEND_TRIES
from lib.exceptions import WindowFullError
from lib.file_controller import FileController
from lib.flags import ACK, CLOSE_ACK, NO_FLAGS
from lib.message_utils import receive_encoded_from_socket, send_ack, send_close
from lib.log import log_received_msg, log_sent_msg
from lib.message import Message
from queue import Queue, Empty


class SelectiveRepeatProtocol:
    def __init__(self, socket):
        self.socket = socket
        self.seq_num = 0
        self.name = SELECTIVE_REPEAT
        self.send_base = 0  # it is the first packet in the window == its sqn
        self.rcv_base = 0
        self.window_size = 6  # TODO revisar
        self.buffer = []
        self.not_acknowledged = 0  # n° packets sent but not acknowledged yet
        self.not_acknowledged_lock = Lock()
        self.acks_map = {}
        self.thread_pool = {}
        self.acks_received = 0

    # Receives acks in client from server
    def receive_acks(self, msq_queue=None, client_port=LOCAL_PORT):
        continue_receiving = True
        tries = 0
        while continue_receiving:
            try:
                maybe_ack = None
                maybe_ack = self.receive_msg(msq_queue)
                msg_received = Message.decode(maybe_ack)
                if msg_received.flags == ACK.encoded:
                    ack_number = msg_received.ack_number
                    print(f"Received ACK: {ack_number}")
                    self.join_ack_thread(msg_received)
                    self.modify_not_acknowledged(-1)
                    self.acks_received += 1
                    log_received_msg(msg_received, client_port)
                    if self.is_base_ack(ack_number):
                        print("Moving send window."
                              + f"Current send base: {self.send_base}")
                        self.move_send_window()
                    else:
                        logging.debug(f"Received messy ACK: {ack_number}")
                    continue_receiving = self.acks_received <= self.max_sqn
            except socket.timeout or Empty:
                logging.error("Timeout on main thread ack")
                tries += 1
                if tries == MAX_ACK_RESEND_TRIES:
                    logging.error("Max tries reached for main ACK thread")
                    for thread in self.thread_pool.values():
                        thread.join()
                    continue_receiving = False
            except Exception as e:
                logging.error(f"Error receiving acks: {e}")
        logging.debug("Sending close msg")
        self.send_close_and_wait_ack(msq_queue, client_port)

    def send_close_and_wait_ack(self, msq_queue, client_port):
        close_tries = 0
        while close_tries < MAX_TIMEOUT_RETRIES:
            try:
                send_close(self.socket, Command.UPLOAD,
                           (LOCAL_HOST, client_port))
                maybe_close_ack = self.receive_msg(msq_queue)
                if Message.decode(maybe_close_ack).flags == CLOSE_ACK.encoded:
                    logging.debug("Received close ACK")
                break
            except socket.timeout or Empty:
                close_tries += 1

    def receive_msg(self, msq_queue):
        if msq_queue:
            maybe_ack = msq_queue.get(block=True, timeout=1.5)
                    # TODO ajustar TO o hacer cte
        else:
            maybe_ack = receive_encoded_from_socket(self.socket)
        return maybe_ack

    def is_base_ack(self, ack_number):
        return ack_number == self.send_base

    def join_ack_thread(self, msg_received):
        thread_is_alive = False
        while not thread_is_alive:
            try:
                ack_num = msg_received.ack_number
                self.acks_map[ack_num].put(ack_num)
                thread_is_alive = True
                logging.debug("Joining thread: %s", ack_num)
                self.thread_pool[ack_num].join()
                if self.thread_pool[ack_num].is_alive():
                    logging.debug("Failed to join thread")

                del self.acks_map[ack_num]
                del self.thread_pool[ack_num]
            except KeyError:
                continue

    def receive(self, decoded_msg, port, file_controller):
        print("Waiting for ack", self.rcv_base)

        if decoded_msg.seq_number == self.rcv_base:
            self.process_expected_packet(decoded_msg, port, file_controller)
        elif self.packet_is_within_window(decoded_msg):
            self.buffer_packet(decoded_msg, port)
        elif self.already_acknowledged(decoded_msg):
            # client lost ack, send ack again
            self.send_duplicated_ack(decoded_msg, port)
        else:
            # otherwise it is not within the window and it is discarded
            logging.error(f"Window starts at {self.rcv_base}"
                          + f" & ends at {self.rcv_base + self.window_size-1}")
            logging.error(f"Msg out of window: {decoded_msg.seq_number}")

    def process_expected_packet(self, decoded_msg, port, file_controller):
        logging.debug("Received expected sqn")
        self.write_to_file(file_controller, decoded_msg)
        log_received_msg(decoded_msg, port)
        self.process_buffer(file_controller)
        seq_num = decoded_msg.seq_number
        logging.debug(f"Sending ACK: {seq_num}")
        send_ack(decoded_msg.command, port, seq_num, self.socket)
        self.seq_num += 1

    def already_acknowledged(self, decoded_msg):
        return decoded_msg.seq_number < self.rcv_base

    def send_duplicated_ack(self, decoded_msg, port):
        seq_num = decoded_msg.seq_number
        logging.debug(f"Message was already acked: {seq_num}")
        send_ack(decoded_msg.command, port, seq_num, self.socket)

    def buffer_packet(self, decoded_msg, port):
        log_received_msg(decoded_msg, port)
        seq_num = decoded_msg.seq_number
        logging.debug(f"Received msg: {seq_num}")
        if self.ack_is_not_repeated(decoded_msg):
            self.buffer.append(decoded_msg)
        logging.debug(f"Sending ACK: {seq_num}")
        send_ack(decoded_msg.command, port, seq_num, self.socket)

    def ack_is_not_repeated(self, decoded_msg):
        unique_sqns = [x.seq_number for x in self.buffer]
        logging.debug(f"Buffered seq nums {unique_sqns}")
        return decoded_msg.seq_number not in unique_sqns

    def process_buffer(self, file_controller):
        """
        Write to file those buffered packets that are after
        rcv_base and before a "jump" (another loss) in their sqn.
        """
        self.buffer.sort(key=lambda x: x.seq_number)
        next_base = self.rcv_base + 1
        remaining_buffer = []

        for packet in self.buffer:
            if packet.seq_number == next_base:
                self.write_to_file(file_controller, packet)
                next_base += 1
            else:
                remaining_buffer.append(packet)

        self.buffer = remaining_buffer
        self.move_rcv_window(next_base - self.rcv_base)

    def write_to_file(self, file_controller, packet):
        logging.debug(f"Writing to file sqn: {packet.seq_number}")
        file_controller.write_file(packet.data)

    def packet_is_within_window(self, decoded_msg):
        max_w_size = self.window_size - 1
        is_before_max = decoded_msg.seq_number <= self.rcv_base + max_w_size
        is_after_base = decoded_msg.seq_number > self.rcv_base
        return is_after_base and is_before_max

    def send(self, command, port, data, file_controller):
        if self.window_is_not_full():
            msg = Message(
                command,
                NO_FLAGS,
                len(data),
                file_controller.file_name,
                data,
                self.seq_num,
                0,
            )
            self.socket.sendto(msg.encode(), (LOCAL_HOST, port))
            self.spawn_packet_ack_thread(port, msg)
            log_sent_msg(msg, self.seq_num, file_controller.get_file_size())
            self.seq_num += 1
            self.modify_not_acknowledged(1)
        else:
            raise WindowFullError

    def window_is_not_full(self):
        return self.not_acknowledged < self.window_size

    def spawn_packet_ack_thread(self, port, msg):
        ack_queue = Queue()
        self.acks_map[self.seq_num] = ack_queue
        args = (self.seq_num, ack_queue, msg.encode(), port)
        wait_ack_thread = Thread(target=self.wait_for_ack, args=args)
        wait_ack_thread.start()
        self.thread_pool[self.seq_num] = wait_ack_thread

    def modify_not_acknowledged(self, amount):
        self.not_acknowledged_lock.acquire()
        if (amount < 0 and self.not_acknowledged > 0) or amount > 0:
            self.not_acknowledged += amount
        self.not_acknowledged_lock.release()

    def upload(self, args):
        f_controller = FileController.from_args(args.src, args.name, READ_MODE)
        file_size = f_controller.get_file_size()
        self.set_window_size(int(file_size / DATA_SIZE))
        data = f_controller.read()
        ack_thread = Thread(target=self.receive_acks)
        ack_thread.start()

        while file_size > 0:
            data_length = len(data)
            try:
                self.send(Command.UPLOAD, LOCAL_PORT, data, f_controller)
            except WindowFullError:
                continue
            data = f_controller.read()
            file_size -= data_length

        ack_thread.join(timeout=10)
        print("Closing connection to clien 11efdt")

        f_controller.close()
        print("Closing connection to client")

    def move_rcv_window(self, shift):
        self.rcv_base += shift

    def move_send_window(self):
        self.send_base += 1

    def set_window_size(self, number_of_packets):
        self.window_size = self.calculate_window_size(number_of_packets)
        self.max_sqn = number_of_packets
        logging.debug(f"Window size: {self.window_size}")

    def calculate_window_size(self, number_of_packets):
        return min(int(number_of_packets / 2), MAX_WINDOW_SIZE)

    def wait_for_ack(self, ack_number, ack_queue, encoded_msg, port):
        logging.info(f"Wating for ack {ack_number}")
        succesfully_acked = False
        tries = 1
        while not succesfully_acked:
            try:
                ack_queue.get(block=True, timeout=TIMEOUT)
                print(f"[THREAD for ACK {ack_number}] succesfully acked")
                succesfully_acked = True
            except Empty:
                if tries == MAX_ACK_RESEND_TRIES:
                    logging.error(f"Max tries reached for ACK {ack_number}")
                    break
                else:
                    logging.error(f"Timeout for ACK {ack_number}")
                    msg = Message.decode(encoded_msg)
                    try:
                        logging.debug(f"Sending msg back to server: {msg}")
                        self.socket.sendto(encoded_msg, (LOCAL_HOST, port))
                    except Exception as e:
                        logging.error(f"Error sending msg back to server: {e}")
                    tries += 1

    def send_error(self, command, port, error_msg):
        encoded_msg = Message.error_msg(command, error_msg)
        self.socket.sendto(encoded_msg, (LOCAL_HOST, port))
        log_sent_msg(Message.decode(encoded_msg), self.seq_num)

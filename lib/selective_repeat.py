import logging
from threading import Thread, Lock
from lib.commands import Command
from lib.constants import BUFFER_SIZE, LOCAL_HOST, TIMEOUT
from lib.constants import LOCAL_PORT, READ_MODE, SELECTIVE_REPEAT
from lib.constants import MAX_WINDOW_SIZE
from lib.exceptions import WindowFullError
from lib.file_controller import FileController
from lib.flags import ACK, NO_FLAGS
from lib.message_utils import receive_encoded_from_socket, send_ack
from lib.log import log_received_msg, log_sent_msg
from lib.message import Message
from queue import Queue, Empty


class SelectiveRepeatProtocol():
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
        self.pending_acks = Lock()
        self.acks_map = {}
        self.thread_pool = {}

    # receive ACKs from client
    def receive_acks_from_queue(self, client_queue: Queue):
        while True:
            try:
                maybe_ack = client_queue.get(block=True)
                msg_received = Message.decode(maybe_ack)
                if msg_received.flags == ACK.encoded:
                    print(f"Received ACK: {msg_received.ack_number}")
                    self.acks_map[msg_received.ack_number].put(msg_received.ack_number)
                    self.thread_pool[msg_received.ack_number].join()
                    with self.not_acknowledged_lock:
                        if self.not_acknowledged > 0:
                            self.not_acknowledged -= 1
                    log_received_msg(msg_received, LOCAL_PORT)
                    if msg_received.ack_number == self.send_base:
                        self.move_send_window()
                    else:
                        logging.debug(
                            f"Received messy ACK: {msg_received.ack_number}")
            except Exception as e:
                logging.error("Error receiving ack: %s", e)
                print("Error receiving acks!")

    # Receives acks from server
    def receive_acks(self):
        continue_receiving = True
        while continue_receiving:
            try:
                maybe_ack = receive_encoded_from_socket(self.socket)
                msg_received = Message.decode(maybe_ack)
                if msg_received.flags == ACK.encoded:
                    print(f"Received ACK: {msg_received.ack_number}")
                    self.acks_map[msg_received.ack_number].put(msg_received.ack_number)
                    self.thread_pool[msg_received.ack_number].join()
                    logging.debug("Joined thread: %s", msg_received.ack_number)
                    with self.not_acknowledged_lock:
                        if self.not_acknowledged > 0:
                            self.not_acknowledged -= 1
                    log_received_msg(msg_received, LOCAL_PORT)
                    print("Received ACK:", msg_received.ack_number)
                    print("Send base:", self.send_base)
                    if msg_received.ack_number == self.send_base:
                        print("Moving send window")
                        continue_receiving = self.move_send_window()
                    else:
                        logging.debug(
                            f"Received messy ACK: {msg_received.ack_number}")
            except Exception as e:
                print(e)
                print("Error receiving acks")
        print("Finished receiving acks")

    def receive(self, decoded_msg, port, file_controller):
        if decoded_msg.seq_number == self.rcv_base:  # it is the expected sqn
            logging.debug("Received expected sqn")
            file_controller.write_file(decoded_msg.data)
            log_received_msg(decoded_msg, port)
            self.process_buffer(file_controller)
        elif self.packet_is_within_window(decoded_msg):
            print("Received msg:", decoded_msg.seq_number)
            # it is not the expected sqn order but it is within the window
            self.buffer.append(decoded_msg)
        # otherwise it is not within the window and it is discarded
        
        print(f"Sending ACK: {decoded_msg.seq_number}")
        send_ack(decoded_msg.command, port, self.seq_num, self.socket)
        self.seq_num += 1

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
        if self.not_acknowledged < self.window_size:
            msg = Message(command, NO_FLAGS, len(data),
                        file_controller.file_name, data, self.seq_num, 0)
            self.socket.sendto(msg.encode(), (LOCAL_HOST, port))

            ack_queue = Queue()
            self.acks_map[self.seq_num] = ack_queue
            args = (self.seq_num, ack_queue, msg.encode(), port) # hace falta pasarse la cola si esta en self?
            wait_ack_thread = Thread(target=self.wait_for_ack, args=args)
            wait_ack_thread.start()
            self.thread_pool[self.seq_num] = wait_ack_thread

            log_sent_msg(msg, self.seq_num, file_controller.get_file_size())
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
        print("Finished sending file")
        self.socket.sendto(Message.close_msg(Command.UPLOAD),
                           (LOCAL_HOST, LOCAL_PORT))
        ack_thread.join()

    def move_rcv_window(self, shift):
        self.rcv_base += shift

    def move_send_window(self):
        self.send_base += 1
        return self.send_base <= self.max_sqn

    def set_window_size(self, number_of_packets):
        self.window_size = self.calculate_window_size(number_of_packets)
        self.max_sqn = number_of_packets - 1
        logging.debug(f"Window size: {self.window_size}")

    def calculate_window_size(self, number_of_packets):
        return min(int(number_of_packets/2), MAX_WINDOW_SIZE)
    
    def wait_for_ack(self, ack_number, ack_queue, encoded_msg, port):
        logging.info(f"Wating for ack {ack_number}")
        succesfully_acked = False
        msg_dummy = Message.ack_msg(Command.UPLOAD, ack_number)
        while not succesfully_acked:
            try:
                ack = ack_queue.get(block=True, timeout=TIMEOUT)
                print(f"[THREAD for ACK {ack_number}] received ack")
                if ack == ack_number:
                    print(f"[THREAD for ACK {ack_number}] succesfully acked")
                    succesfully_acked = True
                    del self.acks_map[ack_number]
                # if ack == self.send_base:
                #     print(f"[THREAD for ACK {ack_number}] moving window")
                #     self.move_send_window()
            except TimeoutError:
                logging.error(f"Timeout for ACK {ack_number}")
                logging.debug("sending msg back to server")
                self.socket.sendto(msg_dummy, (LOCAL_HOST, port))
                logging.debug("sent")
            except Empty:
                logging.error(f"Timeout for ACK {ack_number}")
                logging.debug("sending msg back to server")
                self.socket.sendto(msg_dummy, (LOCAL_HOST, port))
                logging.debug("sent")
    
    def send_error(self, command, port, error_msg):
        encoded_msg = Message.error_msg(command, error_msg)
        self.socket.sendto(encoded_msg, (LOCAL_HOST, port))
        log_sent_msg(Message.decode(encoded_msg), self.seq_num)

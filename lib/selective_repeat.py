import logging
import socket
from threading import Thread, Lock
from lib.commands import Command
from lib.constants import DATA_SIZE, LOCAL_HOST, TIMEOUT
from lib.constants import LOCAL_PORT, READ_MODE, SELECTIVE_REPEAT
from lib.constants import MAX_WINDOW_SIZE, MAX_RESEND_TRIES
from lib.exceptions import WindowFullError
from lib.file_controller import FileController
from lib.flags import ACK, NO_FLAGS
from lib.message_utils import receive_encoded_from_socket, send_ack
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
                        logging.debug(f"Received messy ACK: {msg_received.ack_number}")
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
                    self.join_ack_thread(msg_received)
                    self.not_acknowledged_lock.acquire()
                    if self.not_acknowledged > 0:
                        self.not_acknowledged -= 1
                    self.not_acknowledged_lock.release()
                    self.acks_received += 1
                    log_received_msg(msg_received, LOCAL_PORT)
                    if msg_received.ack_number == self.send_base:
                        print("Moving send window. Current send base:", self.send_base)
                        self.move_send_window()
                    else:
                        logging.debug(f"Received messy ACK: {msg_received.ack_number}")
                    continue_receiving = self.acks_received <= self.max_sqn
            except socket.timeout:
                logging.error("Timeout on thread ack")
            except Exception as e:
                logging.error(f"Error receiving acks: {e}")
        self.socket.sendto(Message.close_msg(Command.UPLOAD), (LOCAL_HOST, LOCAL_PORT))  # TODO recibir comando por parametro?

        
    def join_ack_thread(self, msg_received):
        thread_is_alive = False
        while not thread_is_alive:
            try:
                self.acks_map[msg_received.ack_number].put(msg_received.ack_number)
                thread_is_alive = True
                logging.debug("Joining thread: %s", msg_received.ack_number)
                self.thread_pool[msg_received.ack_number].join()
                if self.thread_pool[msg_received.ack_number].is_alive():
                    logging.debug("Failed to join thread")

                del self.acks_map[msg_received.ack_number]
                del self.thread_pool[msg_received.ack_number]
            except KeyError:
                continue

    def receive(self, decoded_msg, port, file_controller):
        print("Waiting for ack", self.rcv_base)
        print("Buffered seq nums", [x.seq_number for x in self.buffer])
        print("el seq number es", decoded_msg.seq_number)
        if decoded_msg.seq_number == self.rcv_base:  # it is the expected sqn
            logging.debug("Received expected sqn")
            logging.debug(f"Escribiendo el archivo de seq number {decoded_msg.seq_number}")
            logging.debug(f"Escribiendo {len(decoded_msg.data)} bytes")
            file_controller.write_file(decoded_msg.data)
            log_received_msg(decoded_msg, port)
            self.process_buffer(file_controller)
            logging.debug(f"Sending ACK: {decoded_msg.seq_number}")
            send_ack(decoded_msg.command, port, decoded_msg.seq_number, self.socket)
            self.seq_num += 1
        elif self.packet_is_within_window(decoded_msg):
            log_received_msg(decoded_msg, port)
            # it is not the expected sqn order but it is within the window
            logging.debug(f"Received msg: {decoded_msg.seq_number}")
            if decoded_msg.seq_number not in [x.seq_number for x in self.buffer]:
                self.buffer.append(decoded_msg)
            logging.debug(f"Sending ACK: {decoded_msg.seq_number}")
            send_ack(decoded_msg.command, port, decoded_msg.seq_number, self.socket)
        elif decoded_msg.seq_number < self.rcv_base:  # client lost ack, send ack again
            logging.debug(f"Message is already acked: {decoded_msg.seq_number}")
            send_ack(decoded_msg.command, port, decoded_msg.seq_number, self.socket)
        else:
            logging.error(f"la ventana va de {self.rcv_base} hasta {self.rcv_base + self.window_size -1}")
            logging.error(f"Mensaje no esta dentro de la ventana {decoded_msg.seq_number}")
        # otherwise it is not within the window and it is discarded

    def process_buffer(self, file_controller):
        # write only those buffered pkt that are in order with the base
        # Those who are not in order correspond to other packet loss
        self.buffer.sort(key=lambda x: x.seq_number)
        next_base = self.rcv_base + 1
        buffer_restante = []

        for packet in self.buffer:
            if packet.seq_number == next_base:
                logging.debug(f"Escribiendo el archivo de seq number {packet.seq_number}")
                logging.debug(f"Escribiendo {len(packet.data)} bytes")
                file_controller.write_file(packet.data)
                next_base += 1
            else:
                buffer_restante.append(packet)

        self.buffer = buffer_restante
        self.move_rcv_window(next_base - self.rcv_base)

    def packet_is_within_window(self, decoded_msg):
        max_w_size = self.window_size - 1
        is_before_max = decoded_msg.seq_number <= self.rcv_base + max_w_size
        is_after_base = decoded_msg.seq_number > self.rcv_base
        return is_after_base and is_before_max

    def send(self, command, port, data, file_controller):
        if self.not_acknowledged < self.window_size:
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

            ack_queue = Queue()
            self.acks_map[self.seq_num] = ack_queue
            args = (self.seq_num, ack_queue, msg.encode(), port)
            wait_ack_thread = Thread(target=self.wait_for_ack, args=args)
            wait_ack_thread.start()
            self.thread_pool[self.seq_num] = wait_ack_thread

            log_sent_msg(msg, self.seq_num, file_controller.get_file_size())
            self.seq_num += 1
            self.not_acknowledged_lock.acquire()
            print("Incrementing not ack:", self.not_acknowledged)
            self.not_acknowledged += 1
            self.not_acknowledged_lock.release()
        else:
            raise WindowFullError

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
        ack_thread.join()
        f_controller.close()

    def move_rcv_window(self, shift):
        print("moviendo rcv window ", self.rcv_base + shift)
        #if (self.rcv_base + shift <= 16):
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
                if tries == MAX_RESEND_TRIES:
                    logging.error(f"Max tries reached for ACK {ack_number}")
                    break
                else:
                    logging.error(f"Timeout empty for ACK {ack_number}")
                    msg = Message.decode(encoded_msg)
                    try:
                        logging.debug(f"sending msg back to server with msg {msg}")
                        self.socket.sendto(encoded_msg, (LOCAL_HOST, port))
                    except Exception as e:
                        logging.error("Error sending msg back to server: %s", e)
                    tries += 1

    def send_error(self, command, port, error_msg):
        encoded_msg = Message.error_msg(command, error_msg)
        self.socket.sendto(encoded_msg, (LOCAL_HOST, port))
        log_sent_msg(Message.decode(encoded_msg), self.seq_num)

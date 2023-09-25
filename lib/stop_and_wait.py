import logging
from lib.flags import ACK, CLOSE, NO_FLAGS
from lib.constants import LOCAL_HOST, BUFFER_SIZE, STOP_AND_WAIT
from lib.message import Message
from lib.exceptions import DuplicatedACKError
import time

class StopAndWaitProtocol():
    def __init__(self, socket):
        self.socket = socket
        self.seq_num = 0
        self.ack_num = 1
        self.name = STOP_AND_WAIT

    def send_ack_sqn(self, msg, port):
        self.socket.sendto(Message(msg.command, ACK, 0, "", b"", 0, self.ack_num).encode(), (LOCAL_HOST, port))
    
    def receive(self, decoded_msg, port, file_controller):
        print(f"decoded_msg.seq_number: {decoded_msg.seq_number} and self.ack_num: {self.ack_num}")
        if decoded_msg.seq_number > self.ack_num - 1: #it is not the expected sqn
            print("Not expected sqn")
            self.log_received_msg(decoded_msg, port)
            self.send_ack_sqn(decoded_msg, port)
        else:
            file_controller.write_file(decoded_msg.data)
            self.log_received_msg(decoded_msg, port)
            ######### TEST
            prueba = False
            if decoded_msg.seq_number == 4 and prueba:
                print(f"prueba es {prueba} y decoded_msg es {decoded_msg.seq_number}")
                time.sleep(6)
                prueba = False
            ######### TEST
            self.send_ack_sqn(decoded_msg, port)
            self.ack_num += 1
    
    def send(self, command, port, data, file_controller):
        length = len(data)
        if not data:
            self.socket.sendto(Message(command, CLOSE, 0, "", b"", 0, 0).encode(), (LOCAL_HOST, port))
            return
        
        msg = Message(command, NO_FLAGS,
                    length, file_controller.file_name, data, self.seq_num, 0)
        self.socket.sendto(msg.encode(), (LOCAL_HOST, port))
        self.log_sent_msg(msg)
        try: 
            encoded_message, _ = self.socket.recvfrom(BUFFER_SIZE)
            msg_received = Message.decode(encoded_message)
            if msg_received.ack_number <= self.seq_num:
                logging.info(f"Client {port}: received duplicated ACK")
                raise DuplicatedACKError
            else:
                self.seq_num += 1
        except:
            raise TimeoutError
            

    def log_received_msg(self, msg, port):
        logging.info(f"Client {port}: received {len(msg.data)} bytes, seq_number: {msg.seq_number}")

    def log_sent_msg(self, msg):
        logging.debug("Sent {} msg with seq_number {}".format(msg, self.seq_num))

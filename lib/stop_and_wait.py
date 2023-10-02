import logging
from queue import Empty
import socket
from lib.commands import Command
from lib.file_controller import FileController
from lib.flags import CLOSE, NO_FLAGS
from lib.constants import LOCAL_HOST, LOCAL_PORT
from lib.constants import MAX_TIMEOUT_RETRIES, WRITE_MODE
from lib.constants import READ_MODE, STOP_AND_WAIT
from lib.message import Message
from lib.exceptions import DuplicatedACKError, TimeoutsRetriesExceeded
from lib.message_utils import receive_msg, send_ack, send_close_and_wait_ack
from lib.log import log_received_msg, log_sent_msg


class StopAndWaitProtocol():
    def __init__(self, socket):
        self.socket = socket
        self.seq_num = 0
        self.ack_num = 1
        self.tries_send = 0
        self.name = STOP_AND_WAIT

    def receive(self, decoded_msg, port, file_controller):
        print(
            f"decoded_msg.seq_number: {decoded_msg.seq_number} " +
            f"and self.ack_num: {self.ack_num}")

        # dos escenarios:
        # 1) El cliente manda el upload y no llega
        # En este caso el server se queda esperando (Le sacamos el timeout)
        # y al cliente
        # se le timeoutea el socket. Entonces vuelve a mandar con el mismo
        # seq number y aca no paso nada
        # 2) El cliente manda upload, el server manda ACK y se pierde
        # En este caso nosotros aumentamos nuestro ACK pero como nunca llega
        # al cliente el seq_number se mantiene
        # Por eso nos llega un seq_number dos veces menor que nuestro ACK,
        # en ese caso devolvemos el seq_number + 1 y no hacemos nada pq
        # ya tenemos ese paquete
        # Si llega un seq que es solamente 1 numero mayor ejecutamos normal
        # Nunca va a llegar un seq mayor al ack por el escenario 1)
        if self.ack_num > decoded_msg.seq_number + 1:
            log_received_msg(decoded_msg, port)
            send_ack(decoded_msg.command, port, decoded_msg.seq_number + 1,
                     self.socket)
        else:
            file_controller.write_file(decoded_msg.data)
            log_received_msg(decoded_msg, port)
            send_ack(decoded_msg.command, port, self.ack_num, self.socket)
            self.ack_num += 1

    def send_error(self, command, port, error_msg):
        msg = Message.error_msg(command, error_msg)
        self.socket.sendto(msg.encode(), (LOCAL_HOST, port))
        log_sent_msg(msg, self.seq_num)

    def send(self, command, port, data, file_controller, msg_queue=None):
        if self.tries_send >= MAX_TIMEOUT_RETRIES:
            print(self.tries_send)
            logging.error("Max timeout retries reached")
            raise TimeoutsRetriesExceeded
        self.tries_send += 1
        msg = Message(command, NO_FLAGS, len(data),
                      file_controller.file_name, data, self.seq_num, 0)
        self.socket.sendto(msg.encode(), (LOCAL_HOST, port))
        log_sent_msg(msg, self.seq_num, file_controller.get_file_size())
        try:
            encoded_message = receive_msg(msg_queue, self.socket)
            if Message.decode(encoded_message).ack_number <= self.seq_num:
                logging.info(f"Client {port}: received duplicated ACK")
                raise DuplicatedACKError
            else:
                self.tries_send = 0
                self.seq_num += 1
        except socket.timeout:
            logging.error("Timeout receiving ACK message")
            raise socket.timeout
        except Empty:
            logging.error("Timeout receiving ACK message")
            raise Empty

    def upload(self, args=None, msq_queue=None,
               client_port=LOCAL_PORT, file_path=None):
        f_controller = None
        command = Command.UPLOAD
        if file_path:
            f_controller = FileController.from_file_name(file_path, READ_MODE)
            command = Command.DOWNLOAD
        else:
            f_controller = FileController.from_args(args.src,
                                                    args.name, READ_MODE)
        data = f_controller.read()
        file_size = f_controller.get_file_size()
        while file_size > 0:
            data_length = len(data)
            try:
                self.send(command, client_port, data, f_controller, msq_queue)
            except DuplicatedACKError:
                continue
            except socket.timeout:
                logging.error("Timeout! Retrying...")
                continue
            except Empty:
                logging.error("Timeout! Retrying...")
                continue
            data = f_controller.read()
            file_size -= data_length
        send_close_and_wait_ack(self.socket, msq_queue, client_port, command)
        f_controller.close()

    def download(self, first_encoded_msg,
                 file_path, command, client_port=LOCAL_PORT):
        f_controller = FileController.from_file_name(file_path, WRITE_MODE)
        self.socket.settimeout(None)
        encoded_messge = first_encoded_msg
        decoded_message = Message.decode(encoded_messge)

        while decoded_message.flags != CLOSE.encoded:
            self.receive(decoded_message, client_port, f_controller)
            encoded_messge = receive_msg(None, self.socket)
            decoded_message = Message.decode(encoded_messge)
        send_close_and_wait_ack(self.socket, None, client_port, command)
        f_controller.close()

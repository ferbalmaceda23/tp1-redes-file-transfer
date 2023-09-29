import logging
import socket
from lib.commands import Command
from lib.file_controller import FileController
from lib.flags import NO_FLAGS
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
            f"and self.ack_num: {self.ack_num}")

        # dos escenarios: 
        # 1) El cliente manda el upload y no llega
        # En este caso el server se queda esperando (Le sacamos el timeout) y al cliente
        # se le timeoutea el socket. Entonces vuelve a mandar con el mismo seq number y aca no paso nada
        # 2) El cliente manda upload, el server manda ACK y se pierde
        # En este caso nosotros aumentamos nuestro ACK pero como nunca llega al cliente el seq_number se mantiene
        # Por eso nos llega un seq_number dos veces menor que nuestro ACK, en ese caso devolvemos el seq_number + 1 y no hacemos nada pq
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
        except socket.timeout:
            logging.error("Timeout sending message")
            raise socket.timeout

    def upload(self, args):
        f_controller = FileController.from_args(args.src, args.name, READ_MODE)
        data = f_controller.read()
        file_size = f_controller.get_file_size()
        print("EN el upload")
        while file_size > 0:
            data_length = len(data)
            try:
                self.send(Command.UPLOAD, LOCAL_PORT, data, f_controller)
            except DuplicatedACKError:
                continue
            except socket.timeout:
                logging.error("Timeout! Retrying...")
                continue
            # except Exception as e:
            #     print("ninguna de esas", e)
            data = f_controller.read()
            file_size -= data_length
        self.socket.sendto(Message.close_msg(Command.UPLOAD),
                           (LOCAL_HOST, LOCAL_PORT))

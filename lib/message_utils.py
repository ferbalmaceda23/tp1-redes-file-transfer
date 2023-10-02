from queue import Empty
from lib.constants import BUFFER_SIZE, LOCAL_HOST, MAX_TIMEOUT_RETRIES, TIMEOUT
from lib.flags import CLOSE_ACK
from lib.message import Message
from lib.log import logging


def receive_encoded_from_socket(socket):
    encoded_message, _ = socket.recvfrom(BUFFER_SIZE)
    return encoded_message


def send_ack(command, port, ack_number, socket):
    try:
        ack_msg = Message.ack_msg(command, ack_number)
        socket.sendto(ack_msg, (LOCAL_HOST, port))
    except Exception as e:
        logging.error(f"Error sending ACK: {e}")


def send_close(socket, command, client_address):
    socket.sendto(Message.close_msg(command), client_address)


def send_close_and_wait_ack(socket, msq_queue, client_port, command, server_address=None):
    close_tries = 0
    while close_tries < MAX_TIMEOUT_RETRIES:
        try:
            if server_address:
                send_close(socket, command, server_address)
            else:
                send_close(socket, command,
                       (LOCAL_HOST, client_port))
            maybe_close_ack = receive_msg(msq_queue, socket)
            if Message.decode(maybe_close_ack).flags == CLOSE_ACK.encoded:
                logging.debug("Received close ACK")
            break
        except socket.timeout:
            close_tries += 1
        except Empty:
            close_tries += 1


def receive_msg(msq_queue, socket):
    """
    Receive message from socket (client is receiving)
    or from queue (server is receiving)
    """
    if msq_queue:
        maybe_ack = msq_queue.get(block=True, timeout=TIMEOUT)
    else:
        maybe_ack = receive_encoded_from_socket(socket)
    return maybe_ack

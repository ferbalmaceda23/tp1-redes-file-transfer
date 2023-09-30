from lib.constants import BUFFER_SIZE, LOCAL_HOST
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

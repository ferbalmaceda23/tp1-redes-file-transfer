from lib.constants import BUFFER_SIZE, LOCAL_HOST
from lib.message import Message

def receive_encoded_from_socket(socket): 
    encoded_message, _ = socket.recvfrom(BUFFER_SIZE)
    return encoded_message

def send_ack(command, port, ack_number, socket):
    ack_msg = Message.ack_msg(command, ack_number)
    socket.sendto(ack_msg, (LOCAL_HOST, port))
    print(f"Sending ACK: {ack_number}")
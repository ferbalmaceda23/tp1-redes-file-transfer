from lib.constants import SELECTIVE_REPEAT

class SelectiveRepeatProtocol():
    def __init__(self, socket):
        self.socket = socket
        self.seq_num = 0
        self.ack_num = 1
        self.name = SELECTIVE_REPEAT
       # window_size = 


    def receive(self, decoded_msg, port, file):
        pass
    
    def send(self, msg, port, file):
        pass

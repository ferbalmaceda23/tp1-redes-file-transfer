class StopAndWaitProtocol():
    def __init__(self, socket):
        self.socket = socket
        self.seq_num = 0
        self.ack_num = 0

    def send(self, command, data):
        
        pass

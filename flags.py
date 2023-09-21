# Flags used in the protocol
# [HI, CLOSE, ACK, CORRUPTED_PACKAGE]
# [1 0 0 0]
# [1 0 1 0]
class Flag:
    def __init__(self, name, id):
        self.name = name
        self.encoded = id
    
    def get_bytes(self):
        return self.encoded.to_bytes(1, byteorder='big')

HI = Flag("HI", 8)
HI_ACK = Flag("HI_ACK", 10)
CLOSE = Flag("CLOSE", 4)
ACK = Flag("ACK", 2)
CORRUPTED_PACKAGE = Flag("CORRUPTED_PACKAGE", 1)
NO_FLAGS = Flag("NO_FLAGS", 0)
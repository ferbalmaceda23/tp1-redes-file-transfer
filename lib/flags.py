# Flags used in the protocol
# [HI, CLOSE, ACK, CORRUPTED_PACKAGE]
# [1 0 0 0]
# [1 0 1 0]
class Flag:
    def __init__(self, id):
        self.encoded = id
    
    def __str__(self):
        flags_dict = {
            8: "HI",
            10: "HI_ACK",
            4: "CLOSE",
            2: "ACK",
            1: "CORRUPTED_PACKAGE",
            0: "NO_FLAGS"
        }
        return flags_dict.get(self.encoded, "UNKNOWN FLAG")
    
    def get_bytes(self):
        return self.encoded.to_bytes(1, byteorder='big')

HI = Flag(8)
HI_ACK = Flag(10)
CLOSE = Flag(4)
ACK = Flag(2)
CORRUPTED_PACKAGE = Flag(1)
NO_FLAGS = Flag(0)
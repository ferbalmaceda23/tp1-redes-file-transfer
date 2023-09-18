from enum import Enum
from flags import Flag

class Command(Enum):
    DOWNLOAD = 1
    UPLOAD = 2

    def get_bytes(self):
        return self.value.to_bytes(1, byteorder='big', signed=False)

"""
command: [DOWNLOAD, UPLOAD]
flags: [HI, CLOSE, ACK, CORRUPTED_PACKAGE]
file_length: [int]
file_path: [str]
file_name: [str]
id: [int]
data: [bytes]
"""

def add_padding(data: bytes, n: int):
    k = n - len(data)
    if k < 0:
        raise ValueError
    return data + b"\0" * k

class Message:
    def __init__(self, command: Command, flags: Flag, file_length: int, file_name: str, data: bytes):
        self.command = command
        self.flags = flags
        self.file_length = file_length
        self.file_name = file_name
        self.data = data
    
    @classmethod
    def decode(cls, bytes_arr: bytes):
        # Assuming 'command' is a single byte
        command = bytes_arr[0]
        print("Command:", command)

        # Assuming 'flags' is 1 byte
        flags = bytes_arr[1]

        print("Flags:", flags)

        # Assuming 'file_length' is a 32-bit integer (4 bytes)
        file_length = int.from_bytes(bytes_arr[2:6], byteorder="big")
        print("File Length:", file_length)

        # Assuming 'file_name' is a UTF-8 encoded string (up to 400 bytes)
        file_name_bytes = bytes_arr[6:406]
        file_name = file_name_bytes.decode().strip("\0")
        print("File Name:", file_name)

        # Assuming 'data' is the remaining bytes after the previous fields
        data = bytes_arr[406: 406 + file_length]
        print("Data Length:", len(data))

        return {
            "command": command,
            "flags": flags,
            "file_length": file_length,
            "file_name": file_name,
            "data": data
        }

    # @classmethod
    # def decode(cls, encoded_message: bytes):
    #     # Decode command from the first byte
    #     command = "DOWNLOAD" if encoded_message[0] == 0 else "UPLOAD"

    #     # Decode flags from the second byte
    #     flags_byte = encoded_message[1]
    #     flags = []
    #     if flags_byte & (1 << 0):
    #         flags.append("HI")
    #     if flags_byte & (1 << 1):
    #         flags.append("CLOSE")
    #     if flags_byte & (1 << 2):
    #         flags.append("ACK")
    #     if flags_byte & (1 << 3):
    #         flags.append("CORRUPTED_PACKAGE")

    #     # Decode file_length as a 32-bit integer from bytes 2 to 5
    #     file_length = int.from_bytes(encoded_message[2:6], byteorder='big')

    #     # Decode file_name as UTF-8 string from bytes 6 to 405 (assuming max length)
    #     file_name = encoded_message[6:406].decode('utf-8').rstrip('\x00')

    #     # Remaining bytes are the data
    #     data = encoded_message[406:]

    #     return cls(command, flags, file_length, file_name, data)
    
    def encode(self):
        bytes_arr = b""
        bytes_arr += self.command.get_bytes()
        bytes_arr += self.flags.get_bytes()
        bytes_arr += self.file_length.to_bytes(4, signed=False, byteorder='big')

        if self.file_name is not None:
            bytes_arr += add_padding(self.file_name.encode(), 400)
        
        # fill with 0 
        # relleno_len = 1024 - len(bytes_arr)
        # relleno = b'0' * relleno_len
        # bytes_arr += relleno
        # append data from positoin 1024 to 2048
        bytes_arr  += add_padding(self.data, 2048 - 406)

        return  bytes_arr


    # def encode(self):
    #     # Encode the command as a single byte (e.g., 0 for DOWNLOAD, 1 for UPLOAD)
    #     command_byte = bytes([0 if self.command == "DOWNLOAD" else 1])

    #     # Encode the flags as a single byte where each bit represents a flag
    #     flags_byte = 0
    #     for flag in self.flags:
    #         if flag == "HI":
    #             flags_byte |= 1 << 0
    #         elif flag == "CLOSE":
    #             flags_byte |= 1 << 1
    #         elif flag == "ACK":
    #             flags_byte |= 1 << 2
    #         elif flag == "CORRUPTED_PACKAGE":
    #             flags_byte |= 1 << 3
    #     flags_byte = bytes([flags_byte])

    #     # Encode file_length as a 32-bit integer (4 bytes)
    #     file_length_bytes = self.file_length.to_bytes(4, byteorder='big')

    #     # Encode file_name as UTF-8 bytes
    #     file_name_bytes = self.file_name.encode('utf-8')

    #     # Combine all the encoded fields
    #     encoded_message = command_byte + flags_byte + file_length_bytes + file_name_bytes + self.data

    #     return encoded_message
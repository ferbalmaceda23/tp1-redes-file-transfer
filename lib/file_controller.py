import logging
from lib.constants import DATA_SIZE

class FileController():
    def __init__(self, file_name):
        self.file_name = file_name

    def read(self):
        try: 
            file = open(self.file_name, 'rb')
            data = file.read(DATA_SIZE)
            return data
        except:
            logging.error('Error reading file')
            raise Exception('Error reading file')

    def write_file(self, text):
        with open(self.file_name, 'w') as file:
            file.write(text)
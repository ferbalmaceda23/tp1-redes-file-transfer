import logging
import os
from lib.constants import DATA_SIZE
from lib.exceptions import FileReadingError

class FileController():
    @classmethod
    def from_file_name(self, file_name):
        file_controller = FileController()
        file_controller.file_name  = file_name
        file_controller.file = open(file_name, 'wb')
        return file_controller
    
    @classmethod
    def from_args(self, args):
        file_controller = FileController()
        file_controller.src = args.src
        file_controller.file_name = args.name
        file_controller.file = open(file_controller.src, 'rb')
        return file_controller

    def read(self):
        try:
            data = self.file.read(DATA_SIZE)
            return data
        except Exception as e:
            logging.error(f'Error reading file: {e}')
            raise FileReadingError

    def write_file(self, text):
        self.file.write(text)
    
    def get_file_size(self):
        return os.path.getsize(self.src)
import logging

formatter = logging.Formatter('[%(asctime)s] [%(levelname)s] - %(message)s')

stdout_handler = logging.StreamHandler()
stdout_handler.setFormatter(formatter)

logging.basicConfig(level=logging.DEBUG, handlers=[stdout_handler])

def get_logger():
    logger = logging.getLogger('SERVER')
    return logger

LOG = get_logger()
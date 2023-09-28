import logging

# Para despues
RED = '\033[91m'
WHITE = '\033[0m'
GREEN = '\033[92m'
BLUE = '\033[94m'

error_formatter = logging.Formatter(f"%(asctime)s - {RED} [ %(levelname)s ]\
            {WHITE} - %(message)s (%(filename)s:%(lineno)d)")
info_formatter = logging.Formatter(f"%(asctime)s - {BLUE} [ %(levelname)s ]\
            {WHITE} - %(message)s (%(filename)s:%(lineno)d)")
debug_formatter = logging.Formatter(f"%(asctime)s - {GREEN} [ %(levelname)s ]\
            {WHITE} - %(message)s (%(filename)s:%(lineno)d)")


formatter = logging.Formatter('[%(asctime)s] [%(levelname)s] - %(message)s')

stdout_handler = logging.StreamHandler()
stdout_handler.setFormatter(formatter)


def prepare_logging(args):
    def level_verbosity():
        if args.verbose:
            return logging.DEBUG
        elif args.quiet:
            return logging.ERROR
        else:
            return logging.INFO

    
    logging.basicConfig(level=level_verbosity(), handlers=[stdout_handler])
    error_stdout_handler = logging.StreamHandler()
    error_stdout_handler.setFormatter(error_formatter)

    info_stdout_handler = logging.StreamHandler()
    info_stdout_handler.setFormatter(info_formatter)

    debug_stdout_handler = logging.StreamHandler()
    debug_stdout_handler.setFormatter(debug_formatter)

    logger = logging.getLogger('SERVER')
    logger.addHandler(error_stdout_handler) 
    logger.addHandler(info_stdout_handler)  
    logger.addHandler(debug_stdout_handler) 


def log_received_msg(msg, port):  
        logging.info(
            f"Client {port}: received {len(msg.data)}" +
            f" bytes, seq_number: {msg.seq_number}")

def log_sent_msg(msg, seq_num):
    logging.debug(
        f"Sent {msg} msg with seq_number {seq_num}")
BUFFER_SIZE = 2048
HEADER_SIZE = 414
DATA_SIZE = BUFFER_SIZE - HEADER_SIZE

TIMEOUT = 0.01
MAX_TIMEOUT_RETRIES = 5
MAX_ACK_RESEND_TRIES = 10

LOCAL_HOST = "127.0.0.1"
LOCAL_PORT = 8080

STOP_AND_WAIT = "sw"
SELECTIVE_REPEAT = "sr"

WRITE_MODE = "wb"
READ_MODE = "rb"
EMPTY_FILE = 0
EMPTY_DATA = b""

DEFAULT_FOLDER = 'saved-files'

ERROR_EXISTING_FILE = "File already exists"

MAX_WINDOW_SIZE = 10

DOWNLOADS_DIR = "downloads"

class ServerConnectionError(Exception):
    pass


class ClientConnectionError(Exception):
    pass


class FileReadingError(Exception):
    pass


class DuplicatedACKError(Exception):
    pass

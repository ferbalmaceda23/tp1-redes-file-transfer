class ServerConnectionError(Exception):
    pass


class ClientConnectionError(Exception):
    pass


class FileOpenException(Exception):
    pass


class FileReadingError(Exception):
    pass


class DuplicatedACKError(Exception):
    pass


class WindowFullError(Exception):
    pass

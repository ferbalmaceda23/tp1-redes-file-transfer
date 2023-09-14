from argparse import ArgumentParser

class CommandLineArgument:
    def __init__(self, short_form, long_form, description):
        self.short_form = short_form
        self.long_form = long_form
        self.description = description

class UploadCommandOptions:
    def __init__(self):
        self.command_name = 'upload'
        self.help = CommandLineArgument('-h', '--help', 'Show this help message and exit')
        self.verbose = CommandLineArgument('-v', '--verbose', 'Increase output verbosity')
        self.quiet = CommandLineArgument('-q', '--quiet', 'Decrease output verbosity')
        self.host = CommandLineArgument('-H', '--host', 'Server IP address')
        self.port = CommandLineArgument('-p', '--port', 'Server port')
        self.src = CommandLineArgument('-s', '--src', 'Source file path')
        self.name = CommandLineArgument('-n', '--name', 'File name')

class DownloadCommandOptions:
    def __init__(self):
        self.command_name = 'download'
        self.help = CommandLineArgument('-h', '--help', 'Show this help message and exit')
        self.verbose = CommandLineArgument('-v', '--verbose', 'Increase output verbosity')
        self.quiet = CommandLineArgument('-q', '--quiet', 'Decrease output verbosity')
        self.host = CommandLineArgument('-H', '--host', 'Server IP address')
        self.port = CommandLineArgument('-p', '--port', 'Server port')
        self.dst = CommandLineArgument('-d', '--dst', 'Destination file path')
        self.name = CommandLineArgument('-n', '--name', 'File name')


def initialiceCli():
    parser = ArgumentParser()

    # message_group = parser.add_mutually_exclusive_group(required=True)
    group = parser.add_mutually_exclusive_group(required=False)



    group.add_argument(
        "-v",
        "--verbose",
        help="increase output verbosity",
        action="store_true"
    )

    group.add_argument(
        "-q",
        "--quiet",
        help="decrease output verbosity",
        action="store_true"
    )

    parser.add_argument(
        "-H",
        "--host",
        help="server IP address",
        action="store",
        type=str,
        required=True
    )

    parser.add_argument(
        "-p",
        "--port",
        help="server port",
        action="store",
        type=int,
        required=True
    )

    args = parser.parse_args()
    print(args)
   
initialiceCli()
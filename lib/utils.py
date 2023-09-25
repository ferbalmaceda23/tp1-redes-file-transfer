from argparse import ArgumentParser
from lib.constants import SELECTIVE_REPEAT, STOP_AND_WAIT
from lib.selective_repeat import SelectiveRepeatProtocol
from lib.stop_and_wait import StopAndWaitProtocol

def select_protocol(protocol):
    if protocol == SELECTIVE_REPEAT:
        return SelectiveRepeatProtocol
    else:
        return StopAndWaitProtocol

def parse_args_upload():
    parser = ArgumentParser(
        prog="upload",
        description="This is a program to upload files to a server")

    add_args(parser)
    return validate_args(parser)


def parse_args_server():
    parser = ArgumentParser(
        prog="server",
        description="This is a program to upload or download files from a server")

    add_args(parser, src_required=False)

    return validate_args_server(parser)


def parse_args_download():
    parser = ArgumentParser(
        prog="download",
        description="This is a program to download files from a server")

    add_args(parser)
    return validate_args(parser)

def add_args(parser, src_required=True):
    group_verbosity = parser.add_mutually_exclusive_group(required=False)

    group_verbosity.add_argument(
        "-v",
        "--verbose",
        help="increase output verbosity",
        action="store_true"
    )

    group_verbosity.add_argument(
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
        type=str
    )

    parser.add_argument(
        "-p",
        "--port",
        help="server port",
        action="store",
        type=int
    )

    parser.add_argument(
        "-s",
        "--src",
        help="source file path",
        action="store",
        required=src_required,
        type=str
    )

    parser.add_argument(
        "-n",
        "--name",
        help="file name",
        action="store",
        type=str
    )

    parser.add_argument(
        "-pr",
        "--protocol",
        help="stop_and_wait or selective_repeat",
        action="store",
        type=str
    )


def validate_args(parser):
    args = parser.parse_args()

    if args.verbose:
        print("verbosity turned on")
    if args.quiet:
        print("quiet turned on")
    if args.host is None:
        args.host = "localhost"
    if args.port is None:
        args.port = 8080
    if args.name is None:
        args.name = args.src.split("/")[-1]
    if args.protocol is None:
        args.protocol = STOP_AND_WAIT
    
    return args


def validate_args_server(parser):
    args = parser.parse_args()

    if args.verbose:
        print("verbosity turned on")
    if args.quiet:
        print("quiet turned on")
    if args.host is None:
        args.host = "localhost"
    if args.port is None:
        args.port = 8080
    if args.protocol is None:
        args.protocol = STOP_AND_WAIT
    
    return args

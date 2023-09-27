import logging

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
    logging.getLogger('SERVER')

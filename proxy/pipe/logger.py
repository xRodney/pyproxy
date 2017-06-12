import logging


def create_logger():
    logger = logging.getLogger('proxy')
    logger.setLevel(logging.INFO)

    consoleHandler = logging.StreamHandler()
    consoleHandler.setLevel(logging.DEBUG)

    formatter = logging.Formatter(
        '%(asctime)s - %(threadName)s - %(message)s')
    consoleHandler.setFormatter(formatter)

    logger.addHandler(consoleHandler)

    return logger


logger = create_logger()

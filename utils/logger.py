import logging
import os

def load_summary_from_text(summ_dir):
    oracle_summ = dict()
    system_summ = dict()
    for root, dirs, files in os.walk(summ_dir):
        for file in files:
            infile = open(os.path.join(root, file), 'r')
            for line in infile:
                if file.endswith('oracle'):
                    oracle_summ[file] = line
                elif file.endswith('system'):
                    system_summ[file] = line
    return oracle_summ, system_summ

def getLogger(log_name='', log_file='file.log'):
    """
    Get logger
    """
    # logging.getLogger() is a singleton
    logger = logging.getLogger(log_name)
    formatter = logging.Formatter(logging.BASIC_FORMAT)

    if not len(logger.handlers):
        # add stream handler
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)
        logger.addHandler(stream_handler)

        # add file handler
        file_handler_info = logging.FileHandler(log_file, mode='w')
        file_handler_info.setFormatter(formatter)
        file_handler_info.setLevel(logging.DEBUG)
        logger.addHandler(file_handler_info)

        logger.setLevel(logging.DEBUG)

    return logger
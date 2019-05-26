import datetime
import logging
import os

levels = {
    'DEBUG': logging.DEBUG,
    'CRITICAL': logging.CRITICAL,
    'INFO': logging.INFO,
    'WARNING': logging.WARNING
}


def __get_formater():
    return logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')


def __file_handler(file_name, formatter, name='root'):
    if not os.path.exists('logs/'):
        os.mkdir('./logs/')

    handler = logging.FileHandler('logs/' + name + '.' + str(datetime.date.today()) + '.' + file_name)
    handler.setFormatter(formatter)
    return handler


def logger(name: str, file_name: str, log_level='DEBUG') -> logging.Logger:
    """
    Logger object for using (just call %objname%.debug(<str>) or warn and etc.)
    :param name: <str> name of log obj (it will be in log for identify)
    :param file_name: <str> name of log file (better to have an .log extension)
    :param log_level: <str> DEBUG\WARNING\INFO\CRITICAL type of record in log
    :return: <logging.Loger> specified logger object
    """
    if not os.path.exists('logs/'):
        os.mkdir('./logs/')

    logger = logging.getLogger(name)
    logger.setLevel(levels.get(log_level))

    formatter = __get_formater()

    handler = __file_handler(file_name, formatter, name)

    logger.addHandler(handler)

    return logger

'''
this file is used to override oslo log by pitrix logger.
A default logger is provided to run test 
'''
import logging
g_logger = None


def getLogger(name=None):
    global g_logger
    if g_logger:
        return g_logger
    else:
        return getDefaultLogger(name)


def setLogger(logger):
    global g_logger
    g_logger = logger


def getDefaultLogger(name):

    logger = logging.getLogger(name)
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    logger.addHandler(ch)
    logger.setLevel(logging.DEBUG)
    return logger
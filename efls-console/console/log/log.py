# -*- coding: utf8 -*-

import logging
import warnings
import sys

from console.constant import SERVICE_LOG_LEVEL, SERVICE_DEFAULT_LOG_LEVEL


class Logger(object):
    """
    This class is used to control the log integration to Flask application
    """
    logger = None

    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        if SERVICE_LOG_LEVEL not in app.config:
            warnings.warn(f'{SERVICE_LOG_LEVEL} is not set, defaulting {SERVICE_LOG_LEVEL} to '
                          f'{SERVICE_DEFAULT_LOG_LEVEL}')
        logger = logging.getLogger(__name__)
        logger.setLevel(level=app.config[SERVICE_LOG_LEVEL])
        formatter = logging.Formatter(fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                                      datefmt='%Y/%m/%d %H:%M:%S')
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setFormatter(formatter)
        logger.addHandler(stream_handler)
        self.logger = logger

    def debug(self, msg, *args, **kwargs):
        self.logger.debug(msg, *args, **kwargs)

    def info(self, msg, *args, **kwargs):
        self.logger.info(msg, *args, **kwargs)

    def warning(self, msg, *args, **kwargs):
        self.logger.warning(msg, *args, **kwargs)

    def error(self, msg, *args, **kwargs):
        self.logger.error(msg, *args, **kwargs, exc_info=True)

    def critical(self, msg, *args, **kwargs):
        self.logger.critical(msg, *args, **kwargs, exc_info=True)

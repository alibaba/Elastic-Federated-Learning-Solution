# -*- coding: utf8 -*-

"""
this module will be loaded in app init
forbid importing runtime modules
"""

__all__ = ['app_config']

from config.config import config as app_config

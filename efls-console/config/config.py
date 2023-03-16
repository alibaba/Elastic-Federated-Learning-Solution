# -*- coding: utf8 -*-

import os
import configparser
import logging

from console.constant import SERVICE_ENV, SERVICE_DEFAULT_ENV, SERVICE_DEFAULT_CONFIG, SERVICE_DEFAULT_ENCODING, \
    SERVICE_HOST, SERVICE_CONFIG_MODULE, SERVICE_PORT, SERVICE_DEBUG, SERVICE_DEFAULT_HOST, SERVICE_DEFAULT_PORT, \
    SERVICE_DEFAULT_DEBUG, DB_CONFIG_MODULE, DB_SQLALCHEMY_URI, DB_DEFAULT_SQLALCHEMY_URI, SERVICE_BASE_URL, \
    SERVICE_DEFAULT_BASE_URL, SERVICE_LOG_LEVEL, SERVICE_DEFAULT_LOG_LEVEL, SERVICE_LOG_LEVEL_MAP, SERVICE_SECRET_KEY, \
    SERVICE_DOMAIN, SERVICE_DEFAULT_DOMAIN, \
    DB_DEFAULT_SQLALCHEMY_TRACK_MODIFICATIONS, DB_DEFAULT_SQLALCHEMY_ECHO, DB_SQLALCHEMY_TRACK_MODIFICATIONS, \
    DB_SQLALCHEMY_ECHO, \
    MINIO_CONFIG_MODULE, MINIO_ENDPOINT, MINIO_ACCESS_KEY, MINIO_SECRET_KEY

config_dir = os.path.abspath(os.path.dirname(__file__))


def get_customized_ini_name(env: str) -> str:
    """
    get customized service config ini file name
    :return:
    """
    return f'{env}.ini'


class _Config:
    _instance = None

    def __getitem__(self, item):
        return getattr(self, item)

    def __setitem__(self, key, value):
        setattr(self, key, value)

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        cf = configparser.RawConfigParser(allow_no_value=True)
        local_env = os.getenv(SERVICE_ENV, SERVICE_DEFAULT_ENV).lower()
        default_ini_path = os.path.join(config_dir, SERVICE_DEFAULT_CONFIG)
        customized_ini_path = os.path.join(config_dir, get_customized_ini_name(local_env))
        cf.read([default_ini_path, customized_ini_path], SERVICE_DEFAULT_ENCODING)

        debug = str(os.environ.get('debug', 0))
        static = os.environ.get("STATIC", None)
        db_host_k8s_env = 'MYSQL_SERVICE_HOST' if static == 'host' else 'MYSQLPEER_SERVICE_HOST'
        db_port_k8s_env = 'MYSQL_SERVICE_PORT' if static == 'host' else 'MYSQLPEER_SERVICE_PORT'
        minio_host_k8s_env = 'MINIO_SERVICE_SERVICE_HOST'
        minio_port_k8s_env = 'MINIO_SERVICE_SERVICE_PORT'

        # service config
        self[SERVICE_HOST] = cf.get(SERVICE_CONFIG_MODULE, SERVICE_HOST, fallback=None) or SERVICE_DEFAULT_HOST
        self[SERVICE_PORT] = cf.getint(SERVICE_CONFIG_MODULE, SERVICE_PORT, fallback=None) or SERVICE_DEFAULT_PORT
        self[SERVICE_ENV] = local_env
        logging.error(f'current env is {self[SERVICE_ENV]}')
        self[SERVICE_DEBUG] = cf.getboolean(SERVICE_CONFIG_MODULE, SERVICE_DEBUG, fallback=None) \
                              or SERVICE_DEFAULT_DEBUG
        log_level = cf.get(SERVICE_CONFIG_MODULE, SERVICE_LOG_LEVEL, fallback=None) or SERVICE_DEFAULT_LOG_LEVEL
        self[SERVICE_LOG_LEVEL] = SERVICE_LOG_LEVEL_MAP.get(log_level.lower(), logging.NOTSET)
        self[SERVICE_SECRET_KEY] = SERVICE_LOG_LEVEL_MAP.get(SERVICE_CONFIG_MODULE, SERVICE_SECRET_KEY)
        service_url = os.environ.get("BASE-URL", None)
        self[SERVICE_BASE_URL] = service_url if service_url else \
            cf.get(SERVICE_CONFIG_MODULE, SERVICE_BASE_URL, fallback=None)
        logging.error(f'service_url is {self[SERVICE_BASE_URL]}')
        service_domain = os.environ.get("DOMAIN", None)
        self['SERVER_NAME'] = service_domain if service_domain else \
            cf.get(SERVICE_CONFIG_MODULE, SERVICE_DOMAIN, fallback=None)
        logging.error(f'service domain is {self["SERVER_NAME"]}')

        # database config
        db_host = os.environ.get(db_host_k8s_env, None)
        db_port = os.environ.get(db_port_k8s_env, None)
        db_uri = None
        if debug == '0' and db_host and db_port:
            db_uri = f'mysql+pymysql://root:Ali-fl@{db_host}:{db_port}/alifl?charset=utf8mb4'
        self[DB_SQLALCHEMY_URI] = db_uri if db_uri else cf.get(DB_CONFIG_MODULE, DB_SQLALCHEMY_URI, fallback=None)
        logging.error(f'db_host is {db_host}, db_port is {db_port} db_uri is {self[DB_SQLALCHEMY_URI]}')
        self[DB_SQLALCHEMY_TRACK_MODIFICATIONS] = cf.getboolean(DB_CONFIG_MODULE, DB_SQLALCHEMY_TRACK_MODIFICATIONS) \
                                                  or DB_DEFAULT_SQLALCHEMY_TRACK_MODIFICATIONS
        self[DB_SQLALCHEMY_ECHO] = cf.getboolean(DB_CONFIG_MODULE, DB_SQLALCHEMY_ECHO, fallback=None) \
                                   or DB_DEFAULT_SQLALCHEMY_ECHO

        # minio config
        minio_host = os.environ.get(minio_host_k8s_env, None)
        minio_port = os.environ.get(minio_port_k8s_env, None)
        minio_endpoint = None
        if debug == '0' and minio_host and minio_port:
            minio_endpoint = f'{minio_host}:{minio_port}'
        self[MINIO_ENDPOINT] = minio_endpoint if minio_endpoint else cf.get(MINIO_CONFIG_MODULE, MINIO_ENDPOINT)
        logging.error(f'minio_host is {minio_host}, minio_port is {minio_port}, '
                      f'minio_endpoint is {self[MINIO_ENDPOINT]}')
        self[MINIO_ACCESS_KEY] = cf.get(MINIO_CONFIG_MODULE, MINIO_ACCESS_KEY)
        self[MINIO_SECRET_KEY] = cf.get(MINIO_CONFIG_MODULE, MINIO_SECRET_KEY)


config = _Config()

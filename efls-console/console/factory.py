# -*- coding: utf8 -*-

from flask_sqlalchemy import SQLAlchemy
from console.log import Logger
from console.minio import MinioClient

"""
make instances for global use, which will be initiated in app setup
"""

__all__ = ['db', 'logger']

# Database instance
db = SQLAlchemy()

# Log instance
logger = Logger()

# Minio instance
minio_client = MinioClient()

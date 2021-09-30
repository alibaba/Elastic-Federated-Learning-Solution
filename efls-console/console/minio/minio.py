# -*- coding: utf8 -*-

import warnings
import io

from typing import List, Dict, Union, Tuple

from minio import Minio, error as minio_error, datatypes
from urllib3.response import HTTPResponse

from console.constant import MINIO_ENDPOINT, MINIO_ACCESS_KEY, MINIO_SECRET_KEY, DEFAULT_BUCKET_NAME
from console.exceptions import Internal, InvalidArgument


class MinioClient(object):
    """
    This class is used to control minio operations in flask application
    uri structure:
    <Schema>://<ENDPOINT>/<bucket_name>/<object_name>
    """
    client = None
    endpoint = None

    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        if MINIO_ENDPOINT not in app.config or MINIO_ACCESS_KEY not in app.config or MINIO_SECRET_KEY not in app.config:
            warnings.warn('minio necessary configs missing')
            raise RuntimeError
        self.endpoint = app.config[MINIO_ENDPOINT]
        self.client = Minio(app.config[MINIO_ENDPOINT], app.config[MINIO_ACCESS_KEY], app.config[MINIO_SECRET_KEY],
                            secure=False)
        self.create_bucket(DEFAULT_BUCKET_NAME)

    def get_uri_attribute(self, uri: str) -> Union[Tuple[str, str], Tuple[None, None]]:
        uri_component = uri.split('/')
        # ['http:', '', '0.0.0.0:9000', 'alifl', 'test']
        if len(uri_component) < 5:
            return None, None
        bucket_name = uri_component[3]
        object_name = '/'.join(uri_component[4:])

        return bucket_name, object_name

    def make_uri(self, bucket_name: str, object_name: str) -> str:
        return f'http://{self.endpoint}/{bucket_name}/{object_name}'

    def exist_bucket(self, bucket_name: str):
        try:
            return self.client.bucket_exists(bucket_name=bucket_name)
        except minio_error.InvalidResponseError:
            raise Internal(message='minio error in check bucket')
        except minio_error.S3Error as s3e:
            raise Internal(message=f'{s3e.message}')

    def create_bucket(self, bucket_name: str):
        if self.exist_bucket(bucket_name):
            return False
        try:
            self.client.make_bucket(bucket_name=bucket_name)
            return True
        except minio_error.InvalidResponseError:
            raise Internal(message='minio error in create bucket')
        except minio_error.S3Error as s3e:
            raise Internal(message=f'{s3e.message}')

    def get_bucket_list(self) -> List[Dict]:
        try:
            buckets = self.client.list_buckets()
        except minio_error.InvalidResponseError:
            raise Internal(message='minio error in list bucket')
        except minio_error.S3Error as s3e:
            raise Internal(message=f'{s3e.message}')
        bucket_list = []
        for bucket in buckets:
            bucket_list.append(dict(bucket_name=bucket.name, gmt_create=bucket.creation_date))
        return bucket_list

    def get_object(self, bucket_name: str, name: str) -> Union[HTTPResponse, None]:
        try:
            minio_response = self.client.get_object(bucket_name, name)
            return minio_response
        except minio_error.InvalidResponseError:
            raise Internal(message=f'minio error in get object {name} in bucket {bucket_name}')
        except minio_error.S3Error:
            return None

    def stat_object(self, bucket_name: str, name: str) -> datatypes.Object:
        try:
            return self.client.stat_object(bucket_name, name)
        except minio_error.InvalidResponseError:
            raise Internal(message=f'minio error in stat object {name} in bucket {bucket_name}')
        except minio_error.S3Error as s3e:
            raise InvalidArgument(message=f'{s3e.message}')

    def put_object(self, bucket_name: str, name: str, data: io.RawIOBase, length: int) -> str:
        try:
            etag = self.client.put_object(bucket_name, name, data, length)
            return self.make_uri(etag.bucket_name, etag.object_name)
        except minio_error.InvalidResponseError:
            raise Internal(
                message=f'minio error in put object {name} in bucket {bucket_name} with data length {length}')
        except minio_error.S3Error as s3e:
            raise Internal(message=f'{s3e.message}')

    def remove_object(self, bucket_name: str, name: str):
        try:
            return self.client.remove_object(bucket_name, name)
        except minio_error.InvalidResponseError:
            raise Internal(message=f'minio error in remove object {name} in bucket {bucket_name}')
        except minio_error.S3Error as s3e:
            raise Internal(message=f'{s3e.message}')

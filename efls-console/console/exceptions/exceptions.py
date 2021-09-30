# -*- coding: utf8 -*-

from console.exceptions.http_status_code_enum import HttpStatusCodeEnum
from console.exceptions.response_code_enum import ResponseCodeEnum


class ApiBaseException(Exception):
    """
    base exception, defining exception data structure
    """
    http_code = None
    rsp_code = None
    message = None

    def __init__(self, http_code: HttpStatusCodeEnum = None, rsp_code: ResponseCodeEnum = None,
                 message: str = None):
        super().__init__()
        if http_code:
            self.http_code = http_code
        if rsp_code:
            self.rsp_code = rsp_code
        if message:
            self.message = message


class NotFound(ApiBaseException):
    http_code = HttpStatusCodeEnum.NOT_FOUND
    rsp_code = ResponseCodeEnum.NOT_FOUND
    message = (
        'Requested entity was not found.'
    )


class AlreadyExist(ApiBaseException):
    http_code = HttpStatusCodeEnum.CONFLICT
    rsp_code = ResponseCodeEnum.ALREADY_EXISTS
    message = (
        'The entity already exists.'
    )


class Internal(ApiBaseException):
    http_code = HttpStatusCodeEnum.INTERNAL_SERVER_ERROR
    rsp_code = ResponseCodeEnum.INTERNAL
    message = (
        'Internal errors.'
    )


class InvalidArgument(ApiBaseException):
    http_code = HttpStatusCodeEnum.BAD_REQUEST
    rsp_code = ResponseCodeEnum.INVALID_ARGUMENT
    message = (
        'Arguments are problematic.'
    )


class PermissionDenied(ApiBaseException):
    http_code = HttpStatusCodeEnum.FORBIDDEN
    rsp_code = ResponseCodeEnum.PERMISSION_DENIED
    message = (
        'Permission denied.'
    )

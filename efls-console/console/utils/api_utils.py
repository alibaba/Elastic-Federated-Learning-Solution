# -*- coding: utf8 -*-

import json

from flask import request, jsonify, Response

from console.exceptions import HttpStatusCodeEnum, ResponseCodeEnum, InvalidArgument


def api_request() -> dict:
    method = request.method

    if method in ['POST', 'PUT']:
        data = request.get_json()
    elif method in ['GET', 'DELETE']:
        data = request.args
    else:
        data = {}

    return data


def api_response(data: dict, message: str = None, http_code: HttpStatusCodeEnum = HttpStatusCodeEnum.OK.value,
                 rsp_code: ResponseCodeEnum = ResponseCodeEnum.OK.value) -> Response:
    return jsonify(data=data, message=message, http_code=http_code, rsp_code=rsp_code)


def api_params_check(params: dict, required: set, forbidden: set = None, json_check: set = None):
    if not all(key in params for key in required):
        raise InvalidArgument(message=f'incorrect params, {required} are required')
    if forbidden and any(key in params for key in forbidden):
        raise InvalidArgument(message=f'incorrect params, {forbidden} are forbade')
    if json_check:
        for json_candidate in json_check:
            try:
                json.dumps(params.get(json_candidate))
            except json.JSONDecodeError or TypeError:
                raise InvalidArgument(message=f'incorrect param format, {json_candidate} are expected to be json')

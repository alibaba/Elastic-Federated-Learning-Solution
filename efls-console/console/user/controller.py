# -*- coding: utf8 -*-

from flask import Blueprint

from console.utils import api_request, api_response, api_params_check
from console.factory import logger
from console.user.service import UserService, verify_token
from console.user.user_enum import UserRoleEnum
from console.constant import TOKEN

blueprint = Blueprint('user', __name__)


@blueprint.route('', methods=['POST'])
def sign_up():
    request_data = api_request()
    required = {'name', 'password'}
    api_params_check(request_data, required)

    user = UserService().sign_up(request_data['name'], request_data['password'],
                                 request_data.get('role', UserRoleEnum.DEFAULT.value))

    return api_response(dict(user.to_dict(excluded=['password', 'token', 'token_valid'])))


@blueprint.route('', methods=['GET'])
@verify_token()
def get_user(user):
    return api_response(user.to_dict(excluded=['password', 'token', 'token_valid']))


@blueprint.route('/<_id>', methods=['PUT'])
def update_user(_id):
    pass


@blueprint.route('/<_id>', methods=['DELETE'])
def delete_user(_id):
    pass


@blueprint.route('/session', methods=['POST'])
def sign_in():
    request_data = api_request()
    required = {'name', 'password'}
    api_params_check(request_data, required)

    user_service = UserService(name=request_data['name'])
    token = user_service.sign_in(request_data['password'])
    user = user_service.user
    response = api_response(dict(token=token, id=user.id, name=user.name, role=user.role))
    response.set_cookie(TOKEN, token, httponly=True)

    return response


@blueprint.route('/session', methods=['DELETE'])
@verify_token()
def sign_off(user):
    if user:
        UserService(user=user).sign_off()

    response = api_response(dict(result=True))
    response.delete_cookie(TOKEN)

    return response

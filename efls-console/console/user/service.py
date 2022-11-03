# -*- coding: utf8 -*-

import time

from functools import wraps

from itsdangerous import TimedJSONWebSignatureSerializer as TJWSS, SignatureExpired
from flask import current_app, request

from console.models import user_repo, User
from console.exceptions import NotFound, AlreadyExist, InvalidArgument, ResponseCodeEnum
from console.factory import logger
from console.constant import TOKEN_USER_ID, SERVICE_SECRET_KEY, MAX_TOKEN_TIME_S, TOKEN
from console.utils.api_utils import api_response
from console.user.user_enum import UserRoleEnum


def create_token(payload: dict):
    now = int(time.time())
    payload.update(dict(gmt_create=now))
    tjwss = TJWSS(current_app.config[SERVICE_SECRET_KEY], MAX_TOKEN_TIME_S)
    return tjwss.dumps(payload).decode()


def verify_token(role: UserRoleEnum = UserRoleEnum.DEFAULT):
    def decorate(func):
        @wraps(func)
        def decode(*args, **kwargs):
            try:
                token = request.cookies.get(TOKEN)
                if not token:
                    return api_response(data=dict(), message='token not found in cookie',
                                        rsp_code=ResponseCodeEnum.PERMISSION_DENIED.value)
                tjwss = TJWSS(current_app.config[SERVICE_SECRET_KEY], MAX_TOKEN_TIME_S)
                data = tjwss.loads(token)
                if 'user_id' not in data:
                    return api_response(data=dict(), message='invalid token format',
                                        rsp_code=ResponseCodeEnum.PERMISSION_DENIED.value)
                try:
                    user = UserService(uid=data.get(TOKEN_USER_ID)).user
                except NotFound:
                    return api_response(data=dict(), message='user not found',
                                        rsp_code=ResponseCodeEnum.PERMISSION_DENIED.value)
                except:
                    return api_response(data=dict(), message='db connection failed',
                                        rsp_code=ResponseCodeEnum.PERMISSION_DENIED.value)
                # sign out check
                if not user.token_valid:
                    return api_response(data=dict(), message='token expired',
                                        rsp_code=ResponseCodeEnum.PERMISSION_DENIED.value)
                if role == UserRoleEnum.ADMIN and user.role > UserRoleEnum.ADMIN.value:
                    return api_response(data=dict(), message=f'user auth denied, {role.name} is required',
                                        rsp_code=ResponseCodeEnum.PERMISSION_DENIED.value)
                if role == UserRoleEnum.ROOT and user.role > UserRoleEnum.ROOT.value:
                    return api_response(data=dict(), message=f'user auth denied, {role.name} is required',
                                        rsp_code=ResponseCodeEnum.PERMISSION_DENIED.value)
            except SignatureExpired:
                return api_response(data=dict(), message='token expired',
                                    rsp_code=ResponseCodeEnum.PERMISSION_DENIED.value)
            except Exception as ex:
                logger.error(msg='jwt decode error')
                return api_response(data=dict(), message='invalid token',
                                    rsp_code=ResponseCodeEnum.PERMISSION_DENIED.value)

            return func(*args, **kwargs, user=user)

        return decode

    return decorate


class UserService:
    user_repo = user_repo

    def __init__(self, uid: str = None, name: str = None, user: User = None):
        if uid:
            self.user = self.user_repo.get(uid)
            if self.user is None:
                raise NotFound(message='user object init failed')
        elif name:
            self.user = self.user_repo.filter(name=name)
            if self.user is None:
                raise NotFound(message='user object init failed')
        elif user:
            self.user = user
            if self.user is None:
                raise NotFound(message='user object init failed')

    def sign_up(self, name: str, password: str, role: int) -> User:
        if self.user_repo.filter(name=name) is not None:
            raise AlreadyExist(message='user does already exist')

        self.user = User(name=name, password=password, role=role)
        self.user_repo.insert_or_update(self.user)

        return self.user

    def sign_in(self, password: str) -> str:
        check_pw = self.user.validate_password(password)
        if not check_pw:
            raise InvalidArgument(message='incorrect password')

        now = time.time()
        token = create_token({TOKEN_USER_ID: self.user.id})
        self.user.gmt_login = now
        self.user.token = token
        self.user.token_valid = True
        self.user_repo.insert_or_update(self.user)

        return token

    def sign_off(self):
        self.user.token = None
        self.user.token_valid = False
        self.user_repo.insert_or_update(self.user)

    def update(self, request_data: dict):
        update_attr = {}
        user_id = self.user.id
        if request_data.get('password'):
            origin_password = request_data.get('origin_password')
            if not origin_password:
                raise InvalidArgument(message='origin password missing')
            check_pw = self.user.validate_password(origin_password)
            if not check_pw:
                raise InvalidArgument(message='incorrect password')
            self.user.password = User.set_password(request_data.get('password'))
            update_attr['password'] = self.user.password
        if request_data.get('info'):
            update_attr['info'] = request_data.get('info')
        if request_data.get('role'):
            update_attr['role'] = request_data.get('role')

        if update_attr:
            self.user_repo.update_autocommit(
                query_attr=dict(id=user_id),
                update_attr=update_attr,
                error_msg='fail to update user'
            )
        user = self.user_repo.query(filter=[User.id == user_id], query_first=True)

        return user.to_dict(excluded=['password', 'token', 'token_valid'])

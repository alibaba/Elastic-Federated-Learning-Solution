# -*- coding: utf8 -*-

import requests
from typing import Dict, Union

from console.constant import CONNECT_MAX_TRY
from console.factory import logger
from console.exceptions import InvalidArgument


class PeerConnectService:

    def __init__(self, peer_url: str):
        self.peer_url = peer_url
        if not self.peer_url:
            raise InvalidArgument(message='peer url is not available')

    def _get_url(self, uri: str):
        return f'{self.peer_url}{uri}'

    def send_get(self, uri: str, params: dict = None) -> Union[Dict, None]:
        url = self._get_url(uri)
        max_try = CONNECT_MAX_TRY
        while max_try > 0:
            try:
                rsp = requests.get(url, params=params).json()
                logger.debug(msg=f'url is {url}, rsp is {rsp}')
                if rsp.get('http_code') == 200 and rsp.get('rsp_code') == 0:
                    return rsp.get('data')
                else:
                    return rsp
            except Exception:
                max_try -= 1
        return None

    def send_post(self, uri: str, data: dict) -> Union[Dict, None]:
        url = self._get_url(uri)
        max_try = CONNECT_MAX_TRY
        while max_try > 0:
            try:
                rsp = requests.post(url, json=data).json()
                logger.debug(msg=f'url is {url}, rsp is {rsp}')
                if rsp.get('http_code') == 200 and rsp.get('rsp_code') == 0:
                    return rsp.get('data')
                else:
                    return rsp
            except Exception:
                max_try -= 1
        return None

    def send_put(self, uri: str, data: dict) -> Union[Dict, None]:
        url = self._get_url(uri)
        max_try = CONNECT_MAX_TRY
        while max_try > 0:
            try:
                rsp = requests.put(url, json=data).json()
                logger.debug(msg=f'url is {url}, rsp is {rsp}')
                if rsp.get('http_code') == 200 and rsp.get('rsp_code') == 0:
                    return rsp.get('data')
                else:
                    return rsp
            except Exception:
                max_try -= 1
        return None

# -*- coding: utf8 -*-

from typing import Union

from console.models import TaskInter
from console.exceptions import Internal
from console.connect.peer_connect import PeerConnectService
from console.constant import PEER_TASK_URI


class SyncTaskService:
    def __init__(self, task_inter: TaskInter, peer_url: str):
        self.task_inter = task_inter
        if not self.task_inter:
            raise Internal(message='task inter invalid in sync task service')
        self.peer_connect_service = PeerConnectService(peer_url)

    def create_peer_task(self, token: str, version: str, task_root: bool) -> Union[str, None]:
        if not self.task_inter:
            raise Internal(message='task invalid in sync task service')
        data = dict(token=token, version=version, task_root=task_root)
        peer_task_rsp = self.peer_connect_service.send_post(f'{PEER_TASK_URI}/{self.task_inter.id}', data)
        if peer_task_rsp and 'task_inter_id' in peer_task_rsp and peer_task_rsp['task_inter_id']:
            return peer_task_rsp.get('task_inter_id')
        return None

    def get_peer_task(self) -> Union[dict, None]:
        if not self.task_inter:
            raise Internal(message='task invalid in sync task service')
        peer_task_rsp = self.peer_connect_service.send_get(f'{PEER_TASK_URI}/{self.task_inter.id}')
        if peer_task_rsp and 'task_meta' in peer_task_rsp:
            return peer_task_rsp.get('task_meta')
        return None

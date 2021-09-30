# -*- coding: utf8 -*-

from typing import Union

from console.models import TaskInstance
from console.exceptions import Internal
from console.connect.peer_connect import PeerConnectService
from console.constant import PEER_INSTANCE_URI


class SyncTaskInstanceService:
    def __init__(self, task_instance: TaskInstance, peer_url: str):
        self.task_instance = task_instance
        if not self.task_instance:
            raise Internal(message='task_instance invalid in sync task_instance service')
        self.peer_connect_service = PeerConnectService(peer_url)

    def create_task_peer_instance(self) -> Union[str, None]:
        data = dict(task_peer_id=self.task_instance.task_peer_id)
        task_peer_instance_rsp = self.peer_connect_service.send_post(f'{PEER_INSTANCE_URI}/{self.task_instance.id}',
                                                                     data)
        if task_peer_instance_rsp and 'task_instance_id' in task_peer_instance_rsp:
            return task_peer_instance_rsp.get('task_instance_id')
        return None

    def update_task_peer_instance(self, status: int) -> Union[dict, None]:
        data = dict(status=status)
        task_peer_instance_rsp = self.peer_connect_service.send_put(f'{PEER_INSTANCE_URI}/{self.task_instance.id}', data)
        if task_peer_instance_rsp and 'status' in task_peer_instance_rsp:
            return task_peer_instance_rsp.get('status')
        return None

    def get_task_peer_instance(self) -> Union[dict, None]:
        task_peer_instance_rsp = self.peer_connect_service.send_get(f'{PEER_INSTANCE_URI}/{self.task_instance.id}')
        if task_peer_instance_rsp and 'id' in task_peer_instance_rsp:
            return task_peer_instance_rsp
        return None

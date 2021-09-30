# -*- coding: utf8 -*-

from typing import Union

from console.factory import logger
from console.models import Project
from console.exceptions import Internal
from console.connect.peer_connect import PeerConnectService
from console.constant import PEER_PROJECT_URI


class SyncProjectService:
    def __init__(self, project: Project):
        self.project = project
        if not self.project:
            raise Internal(message='project invalid in sync project service')
        self.peer_connect_service = PeerConnectService(project.peer_url)

    def create_peer_project(self, self_url) -> Union[str, None]:
        data = dict(peer_id=self.project.id, peer_url=self_url, peer_config=self.project.config)
        peer_project_rsp = self.peer_connect_service.send_post(PEER_PROJECT_URI, data)
        if peer_project_rsp and 'project_id' in peer_project_rsp:
            return peer_project_rsp.get('project_id')
        return None

    def update_peer_project(self) -> Union[str, None]:
        data = dict(peer_config=self.project.config)
        peer_project_rsp = self.peer_connect_service.send_put(f'{PEER_PROJECT_URI}/{self.project.id}', data)
        if peer_project_rsp and 'project_id' in peer_project_rsp:
            return peer_project_rsp.get('project_id')
        return None

    def get_peer_project(self) -> Union[str, None]:
        peer_project_rsp = self.peer_connect_service.send_get(f'{PEER_PROJECT_URI}/{self.project.id}')
        if peer_project_rsp and 'project_id' in peer_project_rsp:
            return peer_project_rsp.get('project_id')
        return None

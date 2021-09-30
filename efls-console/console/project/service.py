# -*- coding: utf8 -*-

import json

from typing import List, Tuple

from flask import current_app

from console.models import project_repo, Project
from console.exceptions import NotFound, AlreadyExist, PermissionDenied, Internal
from console.factory import logger
from console.project.project_enum import ProjectStatusEnum
from console.constant import PROJECT_DEFAULT_USER, SERVICE_BASE_URL
from console.connect import SyncProjectService
from console.user import UserService, UserRoleEnum


class ProjectService:
    project_repo = project_repo

    def __init__(self, pid: str = None, name: str = None, peer_id: str = None):
        if pid:
            self.project = self.project_repo.get(pid)
            self._init_peer()
        elif name:
            self.project = self.project_repo.filter(name=name)
            self._init_peer()
        elif peer_id:
            self.project = self.project_repo.filter(peer_id=peer_id)
            self._init_peer()

    def _init_peer(self):
        if self.project is None:
            raise NotFound(message='project object init failed')
        self.sync_peer_service = SyncProjectService(self.project)

    def create_project(self, owner_id: str, name: str, peer_url: str, config: str, comment: str) -> Project:
        if self.project_repo.filter(name=name) is not None:
            raise AlreadyExist(message='project does already exist')
        self_url = current_app.config[SERVICE_BASE_URL]
        if not self_url:
            raise Internal(message='service base url not set')

        self.project = Project(owner_id=owner_id, name=name, peer_url=peer_url, comment=comment, config=config,
                               status=ProjectStatusEnum.DRAFT.value)
        self.project_repo.insert_or_update(self.project)
        self.sync_peer_service = SyncProjectService(self.project)
        peer_project_id = self.sync_peer_service.create_peer_project(self_url)
        if peer_project_id:
            self.project.peer_id = peer_project_id
            self.project.status = ProjectStatusEnum.READY.value
            self.project_repo.insert_or_update(self.project)

        return self.project

    def update_project(self, request_data: dict) -> Project:
        if self.project is None or self.sync_peer_service is None:
            raise NotFound(message='project object init failed')

        need_update = False
        need_sync = bool(request_data.get('need_sync', False))
        if 'owner_id' in request_data and request_data['owner_id']:
            user_service = UserService(uid=request_data['owner_id'])
            if user_service.user.role != UserRoleEnum.ADMIN.value:
                raise PermissionDenied(message='user is not allowed to be project owner')
            self.project.owner_id = request_data['owner_id']
            need_update = True
        if 'name' in request_data and request_data['name']:
            self.project.name = request_data['name']
            need_update = True
        if 'comment' in request_data:
            self.project.comment = request_data['comment']
            need_update = True
        if 'config' in request_data:
            config = json.loads(self.project.config) if self.project.config else {}
            config.update(request_data['config'])
            self.project.config = json.dumps(config)
            need_update = True
            need_sync = True

        if need_update:
            self.project_repo.insert_or_update(self.project)
        if need_sync:
            if self.project.status == ProjectStatusEnum.DRAFT.value:
                peer_project_id = self.sync_peer_service.create_peer_project()
                if peer_project_id:
                    self.project.status = ProjectStatusEnum.READY.value
                    self.project_repo.insert_or_update(self.project)
            elif self.project.status == ProjectStatusEnum.READY.value:
                peer_project_id = self.sync_peer_service.update_peer_project()

        return self.project

    def create_peer_project(self, peer_id: str, peer_url: str, peer_config: str) -> str:
        if self.project_repo.filter(peer_id=peer_id) is not None:
            raise AlreadyExist(message='project does already paired in create peer project')

        self.project = Project(owner_id=PROJECT_DEFAULT_USER, status=ProjectStatusEnum.READY.value, peer_id=peer_id,
                               peer_url=peer_url, peer_config=peer_config)
        self.project_repo.insert_or_update(self.project)

        return self.project.id

    def update_peer_project(self, peer_id: str, peer_config: str) -> str:
        self.project = self.project_repo.filter(peer_id=peer_id)
        if self.project is None:
            raise NotFound(message='project not found in update peer project')

        if peer_config:
            peer_config = json.loads(peer_config)
            origin_peer_config = json.loads(self.project.peer_config) if self.project.peer_config else {}
            origin_peer_config.update(peer_config)
            self.project.peer_config = json.dumps(origin_peer_config)
            self.project_repo.insert_or_update(self.project)

        return self.project.id

    def get_project_list(self, page_num, page_size) -> Tuple[List[Project], int]:
        return self.project_repo.get_all_with_pagination(page_num=page_num, page_size=page_size)

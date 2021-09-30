# -*- coding: utf8 -*-

import json

from typing import List

from console.models import TaskIntra, task_intra_repo
from console.exceptions import NotFound, AlreadyExist
from console.user import UserService
from console.project import ProjectService
from console.utils import get_time_version


class TaskIntraService:
    task_intra_repo = task_intra_repo

    def __init__(self, tid: str = None, project_id: str = None, name: str = None, version: str = None):
        if tid:
            self.task_intra = self.task_intra_repo.get(tid)
        elif project_id and name and version:
            self.task_intra = self.task_intra_repo.filter(project_id=project_id, name=name, version=version)

    def create_task(self, project_id: str, name: str, owner_id: str, type: int, task_root: bool, token: str = None,
                    comment: str = None, config: str = None, meta: str = None):
        UserService(uid=owner_id)
        version = get_time_version()
        ProjectService(pid=project_id)
        task_intra_check = self.task_intra_repo.filter(project_id=project_id, name=name, task_root=True)
        if task_root:
            if task_intra_check:
                raise AlreadyExist(message=f'task intra {name} in project {project_id} already exist')
        else:
            if not task_intra_check:
                raise NotFound(message=f'task intra root {name} in project {project_id} not found')
            token = task_intra_check.token

        task_intra = TaskIntra(project_id=project_id, name=name, version=version, owner_id=owner_id, type=type,
                               token=token, task_root=task_root, comment=comment, config=config, meta=meta)
        self.task_intra = task_intra
        self.task_intra_repo.insert_or_update(self.task_intra)

        return self.task_intra

    def check_task_name(self, task_name: str) -> bool:
        return self.task_intra_repo.filter(name=task_name) is not None

    def update_task(self, request_data: dict) -> TaskIntra:
        if self.task_intra is None:
            raise NotFound(message='task intra object init failed')

        need_update = False
        if 'owner_id' in request_data and request_data['owner_id']:
            UserService(uid=request_data['owner_id'])
            self.task_intra.owner_id = request_data['owner_id']
            need_update = True
        if 'token' in request_data:
            if self.task_intra_repo.filter(token=request_data['token']):
                raise AlreadyExist(message='token is already in use')
            self.task_intra.token = request_data['token']
            need_update = True
        if 'comment' in request_data:
            self.task_intra.comment = request_data['comment']
            need_update = True
        if 'config' in request_data:
            config = json.loads(self.task_intra.config) if self.task_intra.config else {}
            config.update(request_data['config'])
            self.task_intra.config = json.dumps(config)
            need_update = True
        if 'meta' in request_data:
            meta = json.loads(self.task_intra.meta) if self.task_intra.meta else {}
            meta.update(request_data['meta'])
            self.task_intra.meta = json.dumps(meta)
            need_update = True

        if need_update:
            self.task_intra_repo.insert_or_update(self.task_intra)

        return self.task_intra

    def get_task_list(self, request_data: dict) -> List[TaskIntra]:
        return self.task_intra_repo.get_all(**request_data)

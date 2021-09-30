# -*- coding: utf8 -*-

from typing import Union

from sqlalchemy.exc import SQLAlchemyError

from console.models import TaskInter, task_inter_repo, task_intra_repo, TaskIntra
from console.exceptions import AlreadyExist, PermissionDenied, NotFound
from console.task.task_enum import TaskInterStatusEnum
from console.connect import SyncTaskService
from console.factory import db
from console.task.task_intra_service import TaskIntraService
from console.project import ProjectService


class TaskInterService:
    task_inter_repo = task_inter_repo
    task_intra_repo = task_intra_repo

    def __init__(self, tid: str = None, task_intra_id: str = None, task_peer_id: str = None):
        if tid:
            self.task_inter = self.task_inter_repo.get(tid)
        elif task_intra_id:
            self.task_inter = self.task_inter_repo.filter(task_intra_id=task_intra_id)
        elif task_peer_id:
            self.task_inter = self.task_inter_repo.filter(task_peer_id=task_peer_id)

    def _get_peer_url(self):
        if not self.task_inter:
            return None
        task_intra = TaskIntraService(tid=self.task_inter.task_intra_id).task_intra
        project = ProjectService(pid=task_intra.project_id).project
        return project.peer_url

    def create_task(self, task_intra_id: str, token: str, version: str, task_root: bool) -> TaskInter:
        db_task_inter = self.task_inter_repo.filter(task_intra_id=task_intra_id)
        if db_task_inter:
            if db_task_inter.status != TaskInterStatusEnum.DRAFT.value:
                raise AlreadyExist(message='task does already exist in create inter task')
            self.task_inter = db_task_inter
        else:
            task_inter = TaskInter(task_intra_id=task_intra_id, status=TaskInterStatusEnum.DRAFT.value)
            self.task_inter = task_inter
            self.task_inter_repo.insert_or_update(self.task_inter)

        peer_url = self._get_peer_url()
        self.sync_peer_service = SyncTaskService(self.task_inter, peer_url)
        task_peer_id = self.sync_peer_service.create_peer_task(token, version, task_root)
        if task_peer_id:
            self.task_inter.task_peer_id = task_peer_id
            self.task_inter.status = TaskInterStatusEnum.READY.value
            self.task_inter_repo.insert_or_update(self.task_inter)

        return self.task_inter

    def update_task(self):
        pass

    def create_peer_task(self, task_peer_id: str, token: str, version: str, task_root: bool) -> Union[str, None]:
        task_intra_root = self.task_intra_repo.filter(token=token, task_root=True)
        if not task_intra_root:
            raise PermissionDenied(message='task token is not authorized')

        if task_root:
            task_intra = task_intra_root
            task_intra_root.version = version
            self.task_intra_repo.insert_or_update(task_intra_root)
        else:
            latest_task_intra = self.task_intra_repo.get_all(token=token)[-1]
            task_intra = TaskIntra(project_id=task_intra_root.project_id, name=task_intra_root.name,
                                   version=version, owner_id=task_intra_root.owner_id, type=task_intra_root.type,
                                   token=token, task_root=False, comment=latest_task_intra.comment,
                                   config=latest_task_intra.config, meta=latest_task_intra.meta)
            self.task_intra_repo.insert_or_update(task_intra)

        task_inter = self.task_inter_repo.filter(task_intra_id=task_intra.id)
        if task_inter is None:
            task_inter = TaskInter(task_intra_id=task_intra.id, task_peer_id=task_peer_id,
                                   status=TaskInterStatusEnum.READY.value)
            self.task_inter_repo.insert_or_update(task_inter)
        else:
            task_inter.task_peer_id = task_peer_id
            task_inter.status = TaskInterStatusEnum.READY.value
            self.task_inter_repo.insert_or_update(task_inter)

        return task_inter.id

    def get_peer_task(self) -> dict:
        if not self.task_inter:
            raise NotFound(message='task infer not found in get peer task')

        peer_url = self._get_peer_url()
        self.sync_peer_service = SyncTaskService(self.task_inter, peer_url)

        return self.sync_peer_service.get_peer_task()

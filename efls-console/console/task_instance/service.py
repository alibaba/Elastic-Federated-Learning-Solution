# -*- coding: utf8 -*-

import time
import json

from typing import List, Tuple
from datetime import datetime

from console.models import task_instance_repo, TaskInstance, task_inter_repo, TaskInter, TaskInstanceRepository
from console.exceptions import NotFound, AlreadyExist, PermissionDenied
from console.factory import logger
from console.task_instance.task_instance_enum import TaskInstanceStatusEnum
from console.connect import SyncTaskInstanceService
from console.task import TaskIntraService
from console.project import ProjectService


class TaskInstanceService:
    task_instance_repo = TaskInstanceRepository()
    task_inter_repo = task_inter_repo

    def __init__(self, task_instance_id: str = None, task_instance_peer_id: str = None):
        if task_instance_id:
            self.task_instance = self.task_instance_repo.get(task_instance_id)
        elif task_instance_peer_id:
            self.task_instance = self.task_instance_repo.filter(instance_peer_id=task_instance_peer_id)

    def _get_peer_url(self):
        if not self.task_instance:
            return None
        task_intra = TaskIntraService(tid=self.task_instance.task_intra_id).task_intra
        project = ProjectService(pid=task_intra.project_id).project
        logger.info(msg=f'sync task instance peer url is {project.peer_url}')
        return project.peer_url

    def create_task_instance(self, task_inter_id: str):
        task_inter = self.task_inter_repo.get(task_inter_id)
        if not task_inter:
            raise NotFound(message='task inter id not found')

        self.task_instance = TaskInstance(task_intra_id=task_inter.task_intra_id, task_inter_id=task_inter_id,
                                          gmt_start=datetime.fromtimestamp(time.time()),
                                          task_peer_id=task_inter.task_peer_id,
                                          status=TaskInstanceStatusEnum.DRAFT.value)
        self.task_instance_repo.insert_or_update(self.task_instance)
        self.task_instance_repo.commit()
        peer_url = self._get_peer_url()
        self.sync_peer_service = SyncTaskInstanceService(self.task_instance, peer_url)
        task_peer_instance_id = self.sync_peer_service.create_task_peer_instance()
        if task_peer_instance_id:
            self.task_instance.instance_peer_id = task_peer_instance_id
            self.task_instance.status = TaskInstanceStatusEnum.READY.value
            self.task_instance_repo.insert_or_update(self.task_instance)
            self.task_instance_repo.commit()

        return self.task_instance

    def update_task_instance(self, message: dict = None, error: dict = None, gmt_start: float = None,
                             gmt_error: float = None, status: int = None, comment: str = None, need_sync: bool = None,
                             check: bool = False):
        if self.task_instance is None:
            raise NotFound(message='task_instance object init failed')

        need_update = False
        if message is not None:
            origin_message = json.loads(self.task_instance.message) if self.task_instance.message else {}
            origin_message.update(message)
            self.task_instance.message = json.dumps(origin_message)
            need_update = True
        if error is not None:
            origin_error = json.loads(self.task_instance.error) if self.task_instance.error else {}
            origin_error.update(error)
            self.task_instance.error = json.dumps(origin_error)
            need_update = True
        if gmt_start is not None:
            self.task_instance.gmt_start = gmt_start
            need_update = True
        if gmt_error is not None:
            self.task_instance.gmt_error = gmt_error
            need_update = True
        if status is not None and status in TaskInstanceStatusEnum._value2member_map_:
            if check is True:
                cur_instance = self.task_instance_repo.get(self.task_instance.id)
                if cur_instance.gmt_create == cur_instance.gmt_modified:
                    self.task_instance.status = status
                    need_update = True
            else:
                self.task_instance.status = status
                need_update = True
        if comment is not None:
            self.task_instance.comment = comment
            need_update = True

        if need_update:
            self.task_instance_repo.insert_or_update(self.task_instance)
            self.task_instance_repo.commit()
        if need_sync is True:
            if self.task_instance.status == TaskInstanceStatusEnum.DRAFT.value:
                peer_url = self._get_peer_url()
                self.sync_peer_service = SyncTaskInstanceService(self.task_instance, peer_url)
                peer_instance_id = self.sync_peer_service.create_task_peer_instance()
                if peer_instance_id:
                    self.task_instance.instance_peer_id = peer_instance_id
                    self.task_instance.status = TaskInstanceStatusEnum.READY.value
                    self.task_instance_repo.insert_or_update(self.task_instance)
                    self.task_instance_repo.commit()

        return self.task_instance

    def create_task_peer_instance(self, task_peer_id: str, instance_peer_id: str):
        if self.task_instance_repo.filter(instance_peer_id=instance_peer_id) is not None:
            raise AlreadyExist(message='task_instance does already paired in create peer task_instance')
        task_inter = self.task_inter_repo.get(task_peer_id)
        if not task_inter:
            raise NotFound(message='task peer id not found')

        self.task_instance = TaskInstance(task_intra_id=task_inter.task_intra_id, task_inter_id=task_inter.id,
                                          gmt_start=datetime.fromtimestamp(time.time()),
                                          task_peer_id=task_peer_id, instance_peer_id=instance_peer_id,
                                          status=TaskInstanceStatusEnum.READY.value)
        self.task_instance_repo.insert_or_update(self.task_instance)
        self.task_instance_repo.commit()

        return self.task_instance

    def update_task_peer_instance(self, status: int):
        if not self.task_instance:
            raise NotFound(message='task_instance not found in get peer task_instance')

        peer_url = self._get_peer_url()
        self.sync_peer_service = SyncTaskInstanceService(self.task_instance, peer_url)

        return self.sync_peer_service.update_task_peer_instance(status)

    def get_task_peer_instance(self):
        if not self.task_instance:
            raise NotFound(message='task_instance not found in get peer task_instance')

        peer_url = self._get_peer_url()
        self.sync_peer_service = SyncTaskInstanceService(self.task_instance, peer_url)

        return self.sync_peer_service.get_task_peer_instance()

    def get_task_instance_list(self, task_inter_id: str, page_num: int, page_size: int) \
            -> Tuple[List[TaskInstance], int]:
        return self.task_instance_repo.get_all_with_pagination(task_inter_id=task_inter_id, page_num=page_num,
                                                               page_size=page_size)

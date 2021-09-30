# -*- coding: utf8 -*-

import json

from console.models import Resource, resource_repo
from console.exceptions import NotFound, AlreadyExist, PermissionDenied
from console.factory import logger


class ResourceService:
    resource_repo = resource_repo

    def __init__(self, rid: str = None, task_intra_id: str = None, name: str = None):
        if rid:
            self.resource = self.resource_repo.get(rid)
        elif task_intra_id and name:
            self.resource = self.resource_repo.filter(task_intra_id=task_intra_id, name=name)

    def create_resource(self, owner_id: str, task_intra_id: str, name: str, uri: str, comment: str, config: str):
        if self.resource_repo.filter(task_intra_id=task_intra_id, name=name) is not None:
            raise AlreadyExist(message='resource does already exist')

        self.resource = Resource(owner_id=owner_id, task_intra_id=task_intra_id, name=name, uri=uri, comment=comment,
                                 config=config)
        self.resource_repo.insert_or_update(self.resource)

        return self.resource

    def update_resource(self, request_data: dict) -> Resource:
        if self.resource is None:
            raise NotFound(message='resource object init failed')

        need_update = False
        if 'comment' in request_data:
            self.resource.comment = request_data['comment']
            need_update = True
        if 'config' in request_data:
            config = json.loads(self.resource.config) if self.resource.config else {}
            config.update(request_data['config'])
            self.resource.config = json.dumps(config)
            need_update = True

        if need_update:
            self.resource_repo.insert_or_update(self.resource)

        return self.resource

    def delete_resource(self):
        if self.resource is None:
            return

        self.resource_repo.delete(self.resource)

    def get_resource_list(self, task_intra_id: str):
        return self.resource_repo.get_all(task_intra_id=task_intra_id)

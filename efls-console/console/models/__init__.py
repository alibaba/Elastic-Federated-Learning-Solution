# -*- coding: utf8 -*-

__all__ = ['User', 'user_repo',
           'Project', 'ProjectRepository', 'ProjectUserRel', 'ProjectUserRepository', 'project_repo',
           'TaskIntra', 'task_intra_repo', 'TaskInter', 'task_inter_repo',
           'Resource', 'resource_repo',
           'TaskInstance', 'task_instance_repo']

from console.models.user import User, UserRepository
from console.models.project import Project, ProjectRepository
from console.models.project_user_rel import ProjectUserRel, ProjectUserRepository
from console.models.task_intra import TaskIntra, TaskIntraRepository
from console.models.task_inter import TaskInter, TaskInterRepository
from console.models.resource import Resource, ResourceRepository
from console.models.task_instance import TaskInstance, TaskInstanceRepository

user_repo = UserRepository()
project_repo = ProjectRepository()
project_user_repo = ProjectUserRepository()
task_intra_repo = TaskIntraRepository()
task_inter_repo = TaskInterRepository()
resource_repo = ResourceRepository()
task_instance_repo = TaskInstanceRepository()

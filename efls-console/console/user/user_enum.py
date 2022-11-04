# -*- coding: utf8 -*-

from enum import Enum


class UserRoleEnum(Enum):
    ROOT = 0  # system root
    ADMIN = 1  # system admin
    DEFAULT = 2  # common user


class UserPermissionEnum(Enum):
    TASK_CREATION = 'task_creation'
    TASK_RUN = 'task_run'

# -*- coding: utf8 -*-

from enum import Enum


class TaskInstanceStatusEnum(Enum):
    DRAFT = 0  # draft, local state
    READY = 1  # ready, connect successfully
    ARCHIVE = 2  # close, not serve any more
    RUNNING = 3
    FAILED = 4
    TERMINATED = 5


class TaskInstanceOperationEnum(Enum):
    START = 0
    STOP = 1

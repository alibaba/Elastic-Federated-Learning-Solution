# -*- coding: utf8 -*-

from enum import Enum


class TaskTypeEnum(Enum):
    SAMPLE = 0
    TRAIN = 1


class TaskInterStatusEnum(Enum):
    DRAFT = 0  # draft, local state
    READY = 1  # ready, connect successfully
    ARCHIVE = 2  # close, not serve any more

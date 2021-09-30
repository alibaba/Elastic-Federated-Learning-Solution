# -*- coding: utf8 -*-

from enum import Enum


class ProjectStatusEnum(Enum):
    DRAFT = 0  # draft, local state
    READY = 1  # ready, connect successfully
    ARCHIVE = 2  # close, not serve any more

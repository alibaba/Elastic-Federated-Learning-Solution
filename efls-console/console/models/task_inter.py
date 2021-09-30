# -*- coding: utf8 -*-

from console.factory import db
from console.models.base import BaseObject, BaseRepository


class TaskInter(BaseObject, db.Model):
    __tablename__ = 'task_inter'

    id = db.Column(db.VARCHAR(64), primary_key=True, autoincrement=False)
    gmt_create = db.Column(db.DateTime)
    gmt_modified = db.Column(db.DateTime)
    # intra info
    task_intra_id = db.Column(db.VARCHAR(64), index=True, unique=True, nullable=False)
    task_peer_id = db.Column(db.VARCHAR(64), index=True, unique=True)
    status = db.Column(db.SmallInteger, index=True)
    comment = db.Column(db.VARCHAR(256))

    __table_args__ = (db.Index('uk_task_intra_id', task_intra_id, unique=True),
                      db.Index('idx_task_inter_id', task_peer_id),
                      db.Index('idx_status', status))

    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class TaskInterRepository(BaseRepository):
    def __init__(self):
        super().__init__(db, TaskInter)

# -*- coding: utf8 -*-

from console.factory import db
from console.models.base import BaseObject, BaseRepository


class TaskInstance(BaseObject, db.Model):
    __tablename__ = 'task_instance'

    id = db.Column(db.VARCHAR(64), primary_key=True, autoincrement=False)
    gmt_create = db.Column(db.DateTime)
    gmt_modified = db.Column(db.DateTime)

    task_intra_id = db.Column(db.VARCHAR(64), index=True, nullable=False)
    task_inter_id = db.Column(db.VARCHAR(64), index=True, nullable=False)
    task_peer_id = db.Column(db.VARCHAR(64), index=True, nullable=False)
    instance_peer_id = db.Column(db.VARCHAR(64), index=True)
    gmt_start = db.Column(db.DateTime)
    gmt_error = db.Column(db.DateTime)
    status = db.Column(db.SmallInteger, index=True)
    comment = db.Column(db.VARCHAR(256))
    message = db.Column(db.JSON)
    error = db.Column(db.JSON)

    __table_args__ = (db.Index('idx_task_intra_id', task_intra_id), db.Index('idx_task_inter_id', task_inter_id),
                      db.Index('idx_task_peer_id', task_peer_id), db.Index('idx_instance_peer_id', instance_peer_id),
                      db.Index('idx_status', status))

    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class TaskInstanceRepository(BaseRepository):
    def __init__(self):
        super().__init__(db, TaskInstance)

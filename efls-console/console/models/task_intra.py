# -*- coding: utf8 -*-

from console.factory import db
from console.models.base import BaseObject, BaseRepository


class TaskIntra(BaseObject, db.Model):
    __tablename__ = 'task_intra'

    id = db.Column(db.VARCHAR(64), primary_key=True, autoincrement=False)
    gmt_create = db.Column(db.DateTime)
    gmt_modified = db.Column(db.DateTime)
    # intra info
    project_id = db.Column(db.VARCHAR(64), index=True, nullable=False)
    name = db.Column(db.VARCHAR(256), index=True, nullable=False)
    version = db.Column(db.VARCHAR(32), nullable=False)
    owner_id = db.Column(db.VARCHAR(64), index=True, nullable=False)
    type = db.Column(db.SmallInteger, index=True, nullable=False)
    token = db.Column(db.VARCHAR(256), index=True)
    task_root = db.Column(db.BOOLEAN, nullable=False)
    comment = db.Column(db.VARCHAR(256))
    config = db.Column(db.JSON)
    # inter info
    meta = db.Column(db.JSON)

    __table_args__ = (db.Index('idx_project_id', project_id), db.Index('idx_name', name),
                      db.Index('idx_owner_id', owner_id), db.Index('idx_type', type), db.Index('idx_token', token),
                      db.Index('uk_project_id_name_version', project_id, name, version, unique=True))

    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class TaskIntraRepository(BaseRepository):
    def __init__(self):
        super().__init__(db, TaskIntra)

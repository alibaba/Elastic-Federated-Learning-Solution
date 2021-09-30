# -*- coding: utf8 -*-

from console.factory import db
from console.models.base import BaseObject, BaseRepository


class Resource(BaseObject, db.Model):
    __tablename__ = 'resource'

    id = db.Column(db.VARCHAR(64), primary_key=True, autoincrement=False)
    gmt_create = db.Column(db.DateTime)
    gmt_modified = db.Column(db.DateTime)

    owner_id = db.Column(db.VARCHAR(64), index=True, nullable=False)
    task_intra_id = db.Column(db.VARCHAR(64), index=True, nullable=False)
    name = db.Column(db.VARCHAR(256), index=True)
    uri = db.Column(db.VARCHAR(512))
    comment = db.Column(db.VARCHAR(256))
    config = db.Column(db.JSON)

    __table_args__ = (db.Index('idx_owner_id', owner_id), db.Index('idx_task_intra_id', task_intra_id),
                      db.Index('idx_name', name))

    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class ResourceRepository(BaseRepository):
    def __init__(self):
        super().__init__(db, Resource)

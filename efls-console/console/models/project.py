# -*- coding: utf8 -*-

from console.factory import db
from console.models.base import BaseObject, BaseRepository


class Project(BaseObject, db.Model):
    __tablename__ = 'project'

    id = db.Column(db.VARCHAR(64), primary_key=True, autoincrement=False)
    gmt_create = db.Column(db.DateTime)
    gmt_modified = db.Column(db.DateTime)
    # intra info
    owner_id = db.Column(db.VARCHAR(64), index=True, nullable=False)
    name = db.Column(db.VARCHAR(256), unique=True, index=True)
    comment = db.Column(db.VARCHAR(256))
    config = db.Column(db.JSON)
    status = db.Column(db.SmallInteger, index=True)
    peer_url = db.Column(db.VARCHAR(256), nullable=False)
    # inter info
    peer_id = db.Column(db.VARCHAR(64), unique=True, index=True)
    peer_config = db.Column(db.JSON)

    __table_args__ = (db.Index('idx_owner_id', owner_id), db.Index('uk_name', name, unique=True),
                      db.Index('idx_status', status), db.Index('idx_peer_id', peer_id))

    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class ProjectRepository(BaseRepository):
    def __init__(self):
        super().__init__(db, Project)

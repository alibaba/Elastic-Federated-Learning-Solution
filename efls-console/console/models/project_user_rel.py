# -*- coding: utf8 -*-

from console.factory import db
from console.models.base import BaseObject, BaseRepository


class ProjectUserRel(BaseObject, db.Model):
    __tablename__ = 'project_user_rel'

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    gmt_create = db.Column(db.DateTime)
    gmt_modified = db.Column(db.DateTime)

    project_id = db.Column(db.VARCHAR(64), nullable=False)
    user_id = db.Column(db.VARCHAR(64), nullable=False)

    __table_args__ = (db.Index('idx_project_id', project_id, unique=True), db.Index('idx_user_id', user_id))

    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class ProjectUserRepository(BaseRepository):
    def __init__(self):
        super().__init__(db, ProjectUserRel)

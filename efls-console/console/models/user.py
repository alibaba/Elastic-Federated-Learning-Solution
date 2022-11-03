# -*- coding: utf8 -*-

from werkzeug.security import generate_password_hash, check_password_hash

from console.factory import db
from console.models.base import BaseObject, BaseRepository


class User(BaseObject, db.Model):
    __tablename__ = 'user'

    id = db.Column(db.VARCHAR(64), primary_key=True, autoincrement=False)
    gmt_create = db.Column(db.DateTime)
    gmt_modified = db.Column(db.DateTime)

    gmt_login = db.Column(db.DateTime)
    name = db.Column(db.VARCHAR(128), unique=True, index=True, nullable=False)
    password = db.Column(db.VARCHAR(128), nullable=False)
    role = db.Column(db.SmallInteger, nullable=False)
    token = db.Column(db.VARCHAR(256))
    token_valid = db.Column(db.BOOLEAN)
    comment = db.Column(db.VARCHAR(256))
    info = db.Column(db.JSON)

    __table_args__ = (db.Index('uk_name', name, unique=True), db.Index('idx_role', role))

    def __init__(self, password, **kwargs):
        super().__init__(**kwargs)
        self.password = self.set_password(password)

    @staticmethod
    def set_password(password):
        return generate_password_hash(password)

    def validate_password(self, password):
        return check_password_hash(self.password, password)

    @staticmethod
    def check_password(hash_, password):
        return check_password_hash(hash_, password)


class UserRepository(BaseRepository):
    def __init__(self):
        super().__init__(db, User)

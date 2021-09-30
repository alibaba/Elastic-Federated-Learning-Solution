# -*- coding: utf8 -*-

from flask import Blueprint

from console.factory import db
from console.utils import api_response

blueprint = Blueprint('db', __name__)


@blueprint.route('', methods=['POST'])
def init_db():
    db.drop_all()
    db.create_all()
    return api_response(dict(result=True))

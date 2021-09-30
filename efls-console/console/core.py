# -*- coding: utf8 -*-

import traceback
import os
import json
import logging

from flask import Flask, _request_ctx_stack, Response, render_template
from flask_cors import CORS
from sqlalchemy.exc import SQLAlchemyError

from config import app_config
from console.factory import db, logger, minio_client
from console.constant import SERVICE_ENV, SERVICE_DEFAULT_ENV
from console.exceptions import ApiBaseException

from console.utils import api_response

static_path = '' if os.environ.get("STATIC", None) is None else '/' + str(os.environ.get("STATIC"))


def create_app():
    file_path = os.path.join(os.path.dirname(__file__), os.path.pardir)
    template_folder = os.path.abspath(file_path + '/templates')
    static_folder = os.path.abspath(file_path + '/static')
    app = Flask(__name__, template_folder=template_folder, static_url_path=static_path, static_folder=static_folder)

    with app.app_context():
        CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)
        setup_config(app)
        logging.error(f'config set up finished')
        setup_db(app)
        logging.error(f'db set up finished')
        setup_logger(app)
        logging.error(f'logger set up finished')
        setup_minio(app)
        logging.error(f'minio set up finished')

        setup_health_api(app)
        setup_blueprints(app)

        @app.route('/')
        def home():
            return render_template('/index.html')

        @app.route(f'{static_path if static_path != "" else "/prefix"}')
        def host():
            return render_template('/index.html')

        @app.route('/env')
        def get_env():
            return os.getenv(SERVICE_ENV, SERVICE_DEFAULT_ENV)

        @app.errorhandler(ApiBaseException)
        def handle_api_exceptions(error):
            logger.error(msg=error.message)
            data = json.dumps(dict(message=error.message, rsp_code=error.rsp_code.value))

            return Response(data, status=error.http_code.value, mimetype='application/json')
            # return api_response(data=data, message=error.message, http_code=error.http_code.value,
            #                     rsp_code=error.rsp_code.value)

        @app.teardown_request
        def commit_to_db(exc):
            if exc and not isinstance(exc, ApiBaseException):
                db.session.rollback()
                _request_ctx_stack.top.http_status_code = 500
            else:
                try:
                    db.session.commit()
                except SQLAlchemyError:
                    _request_ctx_stack.top.http_status_code = 500
                    db.session.rollback()

    return app


def setup_config(app):
    app.config.from_object(app_config)


def setup_db(app):
    db.app = app
    db.init_app(app)


def setup_logger(app):
    logger.app = app
    logger.init_app(app)


def setup_minio(app):
    minio_client.app = app
    minio_client.init_app(app)


def setup_health_api(app):
    @app.route('/health')
    def check_health():
        return 'OK'

    @app.route('/health/db')
    def check_db_health():
        sql = """SELECT 1"""
        try:
            db.session.execute(sql)
            logger.debug(f'db is {db}')
            return 'OK'
        except SQLAlchemyError as e:
            traceback.print_exc()
            return repr(e)

    @app.route('/health/logger')
    def check_logger():
        logger.debug('debug')
        logger.info('info')
        logger.warning('warning')
        try:
            10 / 0
        except Exception:
            logger.error('error')
            logger.critical('critical')
        return 'OK'

    @app.route('/health/minio')
    def check_minio():
        bucket_list = minio_client.get_bucket_list()
        return api_response(dict(bucket_list=bucket_list))


def setup_blueprints(app):
    from console.database import blueprint as database
    from console.user import blueprint as user
    from console.project import blueprint as project
    from console.task import blueprint as task
    from console.task_instance import blueprint as task_instance
    from console.resource import blueprint as resource

    blueprints = [
        {'handler': database, 'url_prefix': '/db'},
        {'handler': user, 'url_prefix': '/user'},
        {'handler': project, 'url_prefix': '/project'},
        {'handler': task, 'url_prefix': '/task'},
        {'handler': task_instance, 'url_prefix': '/task_instance'},
        {'handler': resource, 'url_prefix': '/resource'},
    ]

    for bp in blueprints:
        url_prefix = bp['url_prefix'] if static_path == '' else static_path + bp['url_prefix']
        app.register_blueprint(bp['handler'], url_prefix=url_prefix)

# -*- coding: utf8 -*-

from contextlib import contextmanager
from functools import wraps

from console.factory import logger


@contextmanager
def auto_session(repo, error_msg: str, auto_commit: bool):
    try:
        yield repo.db.session
        if auto_commit:
            repo.db.session.commit()
    except Exception as e:
        repo.db.session.rollback()
        error_msg = f'{error_msg} {str(e)}'
        logger.error(msg=error_msg)
        raise e
    finally:
        if repo.db.session:
            repo.db.session.close()


def repo_auto_session(auto_commit):
    """
    用于 repo 的 db session 封装
    :return:
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            repo = args[0]
            error_msg = kwargs.get('error_msg')
            with auto_session(repo, error_msg, auto_commit):
                return func(*args, **kwargs)

        return wrapper

    return decorator

# -*- coding: utf8 -*-

import time
import uuid

from typing import Optional, List, Any, Tuple, Iterable
from enum import Enum
from datetime import datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import defer

from console.constant import DATA_CREATE, DATA_TIME_KEYS, DB_MAX_TRY, DATA_MODIFIED, DB_PAGE_NUM, DB_PAGE_SIZE
from console.factory import logger
from console.exceptions import Internal
from console.utils import repo_auto_session


class BaseObject:
    """
    base model
    """

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)
        setattr(self, DATA_CREATE, time.time())

    def __setattr__(self, key, value):
        if key in DATA_TIME_KEYS:
            value = datetime.fromtimestamp(value)
        super().__setattr__(key, value)

    def __repr__(self):
        return str(self.__dict__)

    def to_dict(self, added: dict = None, excluded: Optional[list] = None) -> dict:
        """
        object to dict, allowing added and exclusive keys
        :param added: added keys
        :param excluded: exclusive keys
        :return:
        """
        excluded = excluded or []

        output = {}
        if added:
            output.update(added)
        items = self.__table__.columns
        for column in items:
            key = column.name
            if key in excluded:
                continue
            value = getattr(self, key)
            if isinstance(value, Enum):
                value = value.value
            if value and key in DATA_TIME_KEYS:
                value = datetime.timestamp(value)
            output[key] = value

        return output

    @classmethod
    def dict_list(cls, obj_list: list, excluded: Optional[list] = None) -> List[dict]:
        """
        object list to dict list
        :param obj_list:
        :param excluded:
        :return:
        """
        return [obj.to_dict(excluded) for obj in obj_list if isinstance(obj, cls)]


class BaseRepository:
    """
    base repository, offering basic CRUD methods
    """

    def __init__(self, db, model_class):
        self.db = db
        self.model = model_class

    def add(self, element):
        """
        add one element to transaction
        :param element:
        :return:
        """
        self.db.session.add(element)

    def commit(self):
        """
        submit transaction
        :return:
        """
        self.db.session.commit()

    @repo_auto_session(auto_commit=True)
    def add_autocommit(self, element, error_msg: str = 'db fail to add', auto_time=True):
        if auto_time and hasattr(element, DATA_MODIFIED):
            element.gmt_modified = time.time()
        return self.db.session.add(element)

    def add(self, element, error_msg: str = 'db fail to add', auto_time=True):
        if auto_time and hasattr(element, DATA_MODIFIED):
            element.gmt_modified = time.time()
        return self.db.session.add(element)

    @repo_auto_session(auto_commit=True)
    def delete_autocommit(self, element: object, error_msg: str = 'db fail to delete'):
        return self.db.session.delete(element)

    def delete(self, element: object, error_msg: str = 'db fail to delete'):
        return self.db.session.delete(element)

    @repo_auto_session(auto_commit=True)
    def update_autocommit(self, query_attr, update_attr, error_msg: str = 'db fail to update', auto_time=True):
        if auto_time:
            update_attr.update(gmt_modified=datetime.now())

        return self.db.session.query(self.model).filter_by(**query_attr).update(update_attr)

    def update(self, query_attr, update_attr, error_msg: str = 'db fail to update', auto_time=True):
        if auto_time:
            update_attr.update(gmt_modified=datetime.now())

        return self.db.session.query(self.model).filter_by(**query_attr).update(update_attr)

    def execute(self, sql_str: str, error_msg: str = 'db fail to exec'):
        return self.db.session.execute(sql_str)

    @repo_auto_session(auto_commit=False)
    def query(self, params=None, error_msg: str = 'db fail to query', **where_conds):
        if (not where_conds or not set(where_conds.keys()).
                issubset({'filter', 'group_by', 'order_by', 'limit', 'offset', 'query_first'})):
            raise Internal(message='query where conditions error')
        if params is None:
            # 查询 model 全量字段
            session_query = self.db.session.query(self.model)
        else:
            if not isinstance(params, Iterable):
                params = [params]
            session_query = self.db.session.query(*params)
        filter_conds = where_conds.pop('filter', None)
        group_conds = where_conds.pop('group_by', None)
        order_conds = where_conds.pop('order_by', None)
        limit = where_conds.pop('limit', None)
        offset = where_conds.pop('offset', None)
        query_first = where_conds.pop('query_first', False)

        if filter_conds is not None:
            session_query = session_query.filter(*filter_conds)
        if group_conds is not None:
            session_query = session_query.group_by(*group_conds)
        if order_conds is not None:
            session_query = session_query.order_by(*order_conds)
        if limit is not None:
            session_query = session_query.limit(limit)
        if offset is not None:
            session_query = session_query.offset(offset)
        if query_first:
            return session_query.first()

        return session_query.all()

    def query_without_auto_session(self, params=None, error_msg: str = 'db fail to query', **where_conds):
        if (not where_conds or not set(where_conds.keys()).
                issubset({'filter', 'group_by', 'order_by', 'limit', 'offset', 'query_first'})):
            raise Internal(message='query where conditions error')
        if params is None:
            # 查询 model 全量字段
            session_query = self.db.session.query(self.model)
        else:
            if not isinstance(params, Iterable):
                params = [params]
            session_query = self.db.session.query(*params)
        filter_conds = where_conds.pop('filter', None)
        group_conds = where_conds.pop('group_by', None)
        order_conds = where_conds.pop('order_by', None)
        limit = where_conds.pop('limit', None)
        offset = where_conds.pop('offset', None)
        query_first = where_conds.pop('query_first', False)

        if filter_conds is not None:
            session_query = session_query.filter(*filter_conds)
        if group_conds is not None:
            session_query = session_query.group_by(*group_conds)
        if order_conds is not None:
            session_query = session_query.order_by(*order_conds)
        if limit is not None:
            session_query = session_query.limit(limit)
        if offset is not None:
            session_query = session_query.offset(offset)
        if query_first:
            return session_query.first()

        return session_query.all()

    def get(self, _id):
        """
        get element by id
        :param _id:
        :return:
        """
        return self.db.session.query(self.model).filter_by(id=_id).first()

    def filter(self, **attr):
        """
        filter element by attr, get earliest one order by gmt_create
        :param attr:
        :return:
        """
        return self.db.session.query(self.model).filter_by(**attr).order_by(self.model.gmt_create).first()

    def get_all(self, order: Optional[str] = None, defer_attr: Optional[List[str]] = None, **attr) -> List[Any]:
        """
        get all elements by attr order by order
        :param order:
        :param defer_attr:
        :param attr:
        :return:
        """
        order = order or DATA_CREATE
        defer_attr = defer_attr or []

        return self.db.session.query(self.model).options(*[defer(item) for item in defer_attr]).filter_by(**attr) \
            .order_by(getattr(self.model, order)).all()

    def get_all_with_pagination(self, params=None, order: Optional[str] = None, **attr) -> Tuple[List[Any], int]:
        """
        get all elements with pagination
        :param params:
        :param order:
        :param attr:
        :return:
        """
        order = order or DATA_CREATE
        page_num = attr.pop(DB_PAGE_NUM)
        page_size = attr.pop(DB_PAGE_SIZE)
        if params is None:
            session_query = self.db.session.query(self.model)
        else:
            if not isinstance(params, Iterable):
                params = [params]
            session_query = self.db.session.query(*params)
        pagination = session_query.filter_by(**attr).order_by(getattr(self.model, order)) \
            .paginate(page_num, page_size, False)

        return pagination.items, pagination.total

    def get_in(self, id_list):
        """
        get elements for ids in id_list
        :param id_list:
        :return:
        """
        return self.db.session.query(self.model).filter(self.model.id.in_(id_list)).all()

    def insert_or_update(self, element: object, count: int = 1):
        """
        insert or update element
        :param element:
        :param count:
        :return:
        """
        if count > DB_MAX_TRY:
            logger.error('fail to insert or update db')
            raise Internal(message='fail to insert or update db')
        if not element.id and not self.model.id.autoincrement:
            element.id = uuid.uuid4().hex
        now = time.time()
        if hasattr(element, DATA_MODIFIED):
            element.gmt_modified = now

        try:
            self.db.session.add(element)
            self.db.session.flush()
        except IntegrityError:
            element.id = None
            count += 1
            self.insert_or_update(element, count=count)
        except Exception:
            logger.error('fail to insert or update db')
            raise Internal(message='fail to insert or update db')

    def insert_or_update_batch(self, bulk: list, count: int = 1):
        """
        insert or update rows in batch
        :param bulk:
        :param count:
        :return:
        """
        if not bulk:
            return
        if count > DB_MAX_TRY:
            logger.error('fail to insert or update db')
            raise Internal(message='fail to insert or update db')
        check, auto_increment, id_list = bulk[0], True, []
        if not check.id and not self.model.id.autoincrement:
            auto_increment = False
            for i in range(len(bulk)):
                id_list.append(uuid.uuid4().hex)
        now = time.time()
        for index, element in enumerate(bulk):
            if not auto_increment:
                element.id = id_list[index]
            if hasattr(element, DATA_MODIFIED):
                element.gmt_modified = now

        try:
            self.db.session.bulk_save_objects(bulk)
            self.db.session.flush()
        except IntegrityError:
            self.db.session.rollback()
            for element in bulk:
                element.id = None
            count += 1
            self.insert_or_update_batch(bulk, count=count)

    def update_with_attr(self, query_attr, update_attr):
        """
        update rows with update_attr filter by query_attr
        :param query_attr:
        :param update_attr:
        :return:
        """
        now = time.time()
        update_attr.update(gmt_modified=now)
        self.db.session.query(self.model).filter_by(**query_attr).update(update_attr)
        self.db.session.commit()

    def update_with_id_list(self, id_list, **update_attr):
        """
        update rows with update_attr list for ids in id_list
        :param id_list:
        :param update_attr:
        :return:
        """
        now = time.time()
        update_attr.update(gmt_modified=now)
        self.db.session.query(self.model).filter_by(self.model.id.in_(id_list)) \
            .update(update_attr, synchronize_session=False)
        self.db.session.commit()

    def delete(self, element: object):
        """
        delete element
        :param element:
        :return:
        """
        self.db.session.delete(element)
        self.db.session.commit()

    def delete_with_id_list(self, id_list):
        """
        delete rows for ids in id_list
        :param id_list:
        :return:
        """
        self.db.session.query(self.model).filter_by(self.model.id.in_(id_list)).delete(synchronize_session=False)
        self.db.session.commit()

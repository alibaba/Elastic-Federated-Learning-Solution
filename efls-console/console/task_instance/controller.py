# -*- coding: utf8 -*-

import time
import threading

from flask import Blueprint, request

from console.utils import api_request, api_response, api_params_check
from console.exceptions import InvalidArgument, NotFound
from console.factory import logger
from console.task import TaskIntraService
from console.resource import ResourceService
from console.constant import DB_PAGE_NUM, DB_PAGE_SIZE, DB_PAGE_NUM_DEFAULT, DB_PAGE_SIZE_DEFAULT
from console.task_instance.service import TaskInstanceService
from console.task_instance.task_instance_enum import TaskInstanceStatusEnum, TaskInstanceOperationEnum
from console.user import verify_token

from task_interface import TaskInterface

blueprint = Blueprint('task_instance', __name__)


@blueprint.route('/<task_inter_id>', methods=['POST'])
@verify_token()
def create_and_run_instance(task_inter_id, user):
    task_instance = TaskInstanceService().create_task_instance(task_inter_id)
    if task_instance.status == TaskInstanceStatusEnum.READY.value:
        task_intra = TaskIntraService(tid=task_instance.task_intra_id).task_intra
        if task_intra:
            resource_object_list = ResourceService().get_resource_list(task_intra.id)
            resource_uri_list = []
            for resource_object in resource_object_list:
                resource_uri_list.append(resource_object.uri)
            task_instance_service = TaskInstanceService(task_instance_id=task_instance.id)
            logger.info(msg=f'call task run with task inter id {task_inter_id}')
            task_thread = threading.Thread(
                target=TaskInterface.task_run,
                args=(task_intra, task_instance, resource_uri_list, task_instance.id))
            task_thread.start()
            logger.info(msg=f'update task status after task run')
            task_instance = task_instance_service.update_task_instance(gmt_start=time.time(),
                                                                       status=TaskInstanceStatusEnum.RUNNING.value,
                                                                       check=True)

    return api_response(task_instance.to_dict())


@blueprint.route('/<task_instance_id>', methods=['PUT'])
@verify_token()
def update_instance(task_instance_id, user):
    request_data = api_request()
    comment = None
    need_sync = None
    if request_data.get('comment') is not None:
        comment = request_data['comment']
    if request_data.get('need_sync') is not None:
        need_sync = bool(request_data['need_sync'])
    task_instance_service = TaskInstanceService(task_instance_id=task_instance_id)
    task_instance = task_instance_service.update_task_instance(comment=comment, need_sync=need_sync)
    task_instance_peer = task_instance_service.get_task_peer_instance()

    return api_response(dict(task_instance.to_dict(added=dict(task_instance_peer=task_instance_peer))))


@blueprint.route('/<task_instance_id>', methods=['GET'])
@verify_token()
def get_instance(task_instance_id, user):
    task_instance_service = TaskInstanceService(task_instance_id=task_instance_id)
    task_instance = task_instance_service.task_instance
    task_instance_peer = task_instance_service.get_task_peer_instance()
    task_intra_name = TaskIntraService(tid=task_instance.task_intra_id).task_intra.name

    return api_response(dict(task_instance.to_dict(added=dict(task_instance_peer=task_instance_peer,
                                                              task_intra_name=task_intra_name))))


@blueprint.route('/peer/<task_instance_peer_id>', methods=['POST', 'GET', 'PUT'])
def create_peer_instance(task_instance_peer_id):
    """
    service api
    :param task_instance_peer_id:
    :return:
    """
    if request.method == 'POST':
        request_data = api_request()
        required = {'task_peer_id'}
        api_params_check(request_data, required)

        task_instance = TaskInstanceService().create_task_peer_instance(request_data['task_peer_id'],
                                                                        task_instance_peer_id)
        task_intra = TaskIntraService(tid=task_instance.task_intra_id).task_intra
        if task_intra:
            resource_object_list = ResourceService().get_resource_list(task_intra.id)
            resource_uri_list = []
            for resource_object in resource_object_list:
                resource_uri_list.append(resource_object.uri)
            task_instance_service = TaskInstanceService(task_instance_id=task_instance.id)
            task_thread = threading.Thread(
                target=TaskInterface.task_run,
                args=(task_intra, task_instance, resource_uri_list, task_instance.id))
            task_thread.start()
            task_instance = task_instance_service.update_task_instance(gmt_start=time.time(),
                                                                       status=TaskInstanceStatusEnum.RUNNING.value,
                                                                       check=True)

        return api_response(dict(task_instance_id=task_instance.id))
    if request.method == 'PUT':
        request_data = api_request()
        required = {'status'}
        api_params_check(request_data, required)
        task_instance_service = TaskInstanceService(task_instance_peer_id=task_instance_peer_id)
        task_instance = task_instance_service.task_instance
        if not task_instance:
            raise NotFound(
                message=f'task_instance peer id {task_instance_peer_id} was not found in update peer task_instance')
        status = int(request_data.get('status'))
        task_intra = TaskIntraService(tid=task_instance.task_intra_id).task_intra
        if not task_intra:
            raise NotFound(message=f'task intra was not found in update peer task_instance')
        resource_object_list = ResourceService().get_resource_list(task_intra.id)
        resource_uri_list = []
        for resource_object in resource_object_list:
            resource_uri_list.append(resource_object.uri)

        if status == TaskInstanceStatusEnum.RUNNING.value:
            if task_instance.status in (TaskInstanceStatusEnum.READY.value, TaskInstanceStatusEnum.TERMINATED.value):
                task_thread = threading.Thread(
                    target=TaskInterface.task_start,
                    args=(task_intra, task_instance, resource_uri_list, task_instance.id))
                task_thread.start()
                task_instance = task_instance_service.update_task_instance(gmt_start=time.time(),
                                                                           status=TaskInstanceStatusEnum.RUNNING.value)
        if status == TaskInstanceStatusEnum.TERMINATED.value:
            if task_instance.status == TaskInstanceStatusEnum.RUNNING.value:
                task_thread = threading.Thread(
                    target=TaskInterface.task_stop,
                    args=(task_intra, task_instance, resource_uri_list, task_instance.id))
                task_thread.start()
                task_instance = task_instance_service \
                    .update_task_instance(status=TaskInstanceStatusEnum.TERMINATED.value)

        return api_response(dict(status=task_instance.status))
    if request.method == 'GET':
        task_instance = TaskInstanceService(task_instance_peer_id=task_instance_peer_id).task_instance
        if not task_instance:
            raise NotFound(
                message=f'task_instance peer id {task_instance_peer_id} was not found in get peer task_instance')
        task_intra_name = TaskIntraService(tid=task_instance.task_intra_id).task_intra.name

        return api_response(task_instance.to_dict(added=dict(task_intra_name=task_intra_name)))


@blueprint.route('/list', methods=['GET'])
@verify_token()
def get_instance_list(user):
    request_data = api_request()
    required = {'task_inter_id'}
    api_params_check(request_data, required)
    page_num = request_data.get(DB_PAGE_NUM, DB_PAGE_NUM_DEFAULT)
    page_size = request_data.get(DB_PAGE_SIZE, DB_PAGE_SIZE_DEFAULT)
    task_instance_object_list, total = TaskInstanceService() \
        .get_task_instance_list(request_data['task_inter_id'], page_num=int(page_num), page_size=int(page_size))
    task_instance_dict_list = []
    for task_instance_object in task_instance_object_list:
        task_instance_dict_list.append(task_instance_object.to_dict())

    return api_response(dict(task_instance_list=task_instance_dict_list, total=total))


@blueprint.route('/status/<task_instance_id>', methods=['POST'])
@verify_token()
def update_status(task_instance_id, user):
    request_data = api_request()
    required = {'operation'}
    api_params_check(request_data, required)
    operation = int(request_data['operation'])
    if operation not in TaskInstanceOperationEnum._value2member_map_:
        raise InvalidArgument(message='invalid operation type')

    task_instance_service = TaskInstanceService(task_instance_id=task_instance_id)
    task_instance = task_instance_service.task_instance
    if not task_instance:
        raise NotFound(message='task_instance id not found')
    task_intra = TaskIntraService(tid=task_instance.task_intra_id).task_intra
    if not task_intra:
        raise NotFound(message='task intra not found')
    resource_object_list = ResourceService().get_resource_list(task_intra.id)
    resource_uri_list = []
    for resource_object in resource_object_list:
        resource_uri_list.append(resource_object.uri)
    if operation == TaskInstanceOperationEnum.START.value:
        if task_instance.status not in (TaskInstanceStatusEnum.READY.value, TaskInstanceStatusEnum.TERMINATED.value):
            raise InvalidArgument(message='invalid operation type')
        logger.info(msg=f'call task start with task instance id {task_instance_id}')
        task_thread = threading.Thread(
            target=TaskInterface.task_start,
            args=(task_intra, task_instance, resource_uri_list, task_instance_id))
        task_thread.start()
        task_instance = task_instance_service.update_task_instance(gmt_start=time.time(),
                                                                   status=TaskInstanceStatusEnum.RUNNING.value)
        task_instance_service.update_task_peer_instance(TaskInstanceStatusEnum.RUNNING.value)
    if operation == TaskInstanceOperationEnum.STOP.value:
        if task_instance.status != TaskInstanceStatusEnum.RUNNING.value:
            raise InvalidArgument(message='invalid operation type')
        task_thread = threading.Thread(
            target=TaskInterface.task_stop,
            args=(task_intra, task_instance, resource_uri_list, task_instance_id))
        task_thread.start()
        logger.info(msg=f'call task stop with task instance id {task_instance_id}')
        task_instance = task_instance_service.update_task_instance(status=TaskInstanceStatusEnum.TERMINATED.value)
        task_instance_service.update_task_peer_instance(TaskInstanceStatusEnum.TERMINATED.value)

    return api_response(dict(status=task_instance.status))

# -*- coding: utf8 -*-

import json

from flask import Blueprint, request

from console.utils import api_request, api_response, api_params_check
from console.exceptions import InvalidArgument, NotFound
from console.factory import logger
from console.task.task_intra_service import TaskIntraService
from console.task.task_inter_service import TaskInterService
from console.task.task_enum import TaskTypeEnum, TaskInterStatusEnum
from console.user import verify_token, UserService
from console.project import ProjectService

blueprint = Blueprint('task', __name__)


@blueprint.route('', methods=['POST'])
@verify_token()
def create_task_intra(user):
    request_data = api_request()
    required = {'project_id', 'name', 'type', 'task_root'}
    config = request_data.get('config')
    meta = request_data.get('meta')
    json_check = set()
    if config:
        json_check.add('config')
    if meta:
        json_check.add('meta')
    api_params_check(request_data, required, json_check=json_check)
    type = request_data.get('type')
    if type and type not in TaskTypeEnum._value2member_map_:
        raise InvalidArgument(message='invalid task type')

    config = json.dumps(config) if config else None
    meta = json.dumps(meta) if meta else None
    task_intra = TaskIntraService().create_task(request_data['project_id'], request_data['name'],
                                                user.id, request_data['type'],
                                                request_data['task_root'], request_data.get('token'),
                                                request_data.get('comment'), config, meta)

    return api_response(task_intra.to_dict())


@blueprint.route('/name/<task_name>', methods=['POST'])
@verify_token()
def check_task_name(task_name, user):
    name_exist = TaskIntraService().check_task_name(task_name)

    return api_response(dict(name_exist=name_exist))


@blueprint.route('/<task_intra_id>', methods=['PUT', 'GET', 'DELETE'])
@verify_token()
def update_or_get_task_intra(task_intra_id, user):
    if request.method == 'PUT':
        request_data = api_request()
        required = set()
        forbidden = {'project_id', 'name', 'version', 'type', 'task_root'}
        config = request_data.get('config')
        meta = request_data.get('meta')
        json_check = set()
        if config:
            json_check.add('config')
        if meta:
            json_check.add('meta')
        api_params_check(request_data, required, forbidden=forbidden, json_check=json_check)

        task_intra = TaskIntraService(tid=task_intra_id).update_task(request_data)

        return api_response(task_intra.to_dict())
    if request.method == 'GET':
        task_intra = TaskIntraService(tid=task_intra_id).task_intra
        task_inter = TaskInterService(task_intra_id=task_intra_id).task_inter
        status = task_inter.status if task_inter else TaskInterStatusEnum.DRAFT.value
        task_inter_id = task_inter.id if task_inter else None
        owner_name = UserService(uid=task_intra.owner_id).user.name
        project_name = ProjectService(pid=task_intra.project_id).project.name

        return api_response(task_intra.to_dict(added=dict(status=status, task_inter_id=task_inter_id,
                                                          owner_name=owner_name, project_name=project_name)))
    if request.method == 'DELETE':
        task_intra_service = TaskIntraService(tid=task_intra_id)
        if not task_intra_service.task_intra:
            raise InvalidArgument(message=f'task intra {task_intra_id} not valid')
        if task_intra_service.task_intra.task_root:
            raise InvalidArgument(message=f'task intra {task_intra_id} is root instance, cannot be deleted')
        task_intra_service.delete_task()

        return api_response(dict(result=True))


@blueprint.route('/inter/<task_id>', methods=['POST', 'GET'])
@verify_token()
def create_or_get_task_inter(task_id, user):
    if request.method == 'POST':
        task_intra_id = task_id
        task_intra = TaskIntraService(tid=task_intra_id).task_intra
        if not task_intra or not task_intra.token:
            raise InvalidArgument(message='task intra not valid, not exist or token missed')

        task_inter = TaskInterService().create_task(task_intra_id, task_intra.token, task_intra.version,
                                                    task_intra.task_root)

        return api_response(task_inter.to_dict())
    if request.method == 'GET':
        task_inter_id = task_id
        peer_task_rsp = TaskInterService(tid=task_inter_id).get_peer_task()

        return api_response(dict(peer_task_rsp=peer_task_rsp))


@blueprint.route('/peer/<task_peer_id>', methods=['POST', 'GET'])
def create_or_get_peer_task(task_peer_id):
    """
    service api
    :return:
    """
    if request.method == 'POST':
        request_data = api_request()
        required = {'token', 'version', 'task_root'}
        api_params_check(request_data, required)

        task_inter_id = TaskInterService().create_peer_task(task_peer_id, request_data['token'],
                                                            request_data['version'], request_data['task_root'])

        return api_response(dict(task_inter_id=task_inter_id))
    if request.method == 'GET':
        task_inter = TaskInterService(task_peer_id=task_peer_id).task_inter
        if not task_inter:
            raise NotFound(message=f'task peer id {task_peer_id} was not found in get peer task inter')
        task_intra = TaskIntraService(tid=task_inter.task_intra_id).task_intra
        if not task_intra:
            raise NotFound(message=f'task peer id {task_peer_id} was not found in get peer task intra')
        if task_intra.meta:
            task_meta = json.loads(task_intra.meta)
        else:
            task_meta = None

        return api_response(dict(task_meta=task_meta))


@blueprint.route('/list', methods=['GET'])
@verify_token()
def get_task_list(user):
    request_data = api_request()
    task_object_list = TaskIntraService().get_task_list(request_data)
    task_dict_list = []
    for task_object in task_object_list:
        status = TaskInterStatusEnum.DRAFT.value
        task_inter_id = None
        task_inter = TaskInterService(task_intra_id=task_object.id).task_inter
        if task_inter:
            status = task_inter.status
            task_inter_id = task_inter.id
        owner_name = UserService(uid=task_object.owner_id).user.name
        project_name = ProjectService(pid=task_object.project_id).project.name
        task_dict_list.append(task_object.to_dict(added=dict(status=status, task_inter_id=task_inter_id,
                                                             owner_name=owner_name, project_name=project_name)))

    return api_response(dict(task_list=task_dict_list, total=len(task_dict_list)))

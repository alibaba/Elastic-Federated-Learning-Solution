# -*- coding: utf8 -*-

import json

from flask import Blueprint, request

from console.utils import api_request, api_response, api_params_check
from console.factory import logger
from console.project.service import ProjectService
from console.constant import DB_PAGE_NUM, DB_PAGE_SIZE, DB_PAGE_NUM_DEFAULT, DB_PAGE_SIZE_DEFAULT, PROJECT_DEFAULT_USER
from console.user import UserRoleEnum, verify_token, UserService

blueprint = Blueprint('project', __name__)


@blueprint.route('', methods=['POST'])
@verify_token(UserRoleEnum.ADMIN)
def create_project(user):
    request_data = api_request()
    required = {'name', 'peer_url'}
    if request_data.get('config'):
        json_check = {'config'}
    else:
        json_check = None
    api_params_check(request_data, required, json_check=json_check)

    config = json.dumps(request_data.get('config')) if request_data.get('config') else None
    project = ProjectService().create_project(user.id, request_data['name'], request_data['peer_url'], config,
                                              request_data.get('comment'))

    return api_response(project.to_dict())


@blueprint.route('/<project_id>', methods=['PUT', 'GET'])
@verify_token()
def update_or_get_project(project_id, user):
    if request.method == 'PUT':
        request_data = api_request()
        required = set()
        forbidden = {'peer_id', 'peer_config', 'peer_url', 'status'}
        if request_data.get('config'):
            json_check = {'config'}
        else:
            json_check = None
        api_params_check(request_data, required, forbidden=forbidden, json_check=json_check)

        project = ProjectService(pid=project_id).update_project(request_data)

        return api_response(project.to_dict())
    if request.method == 'GET':
        project = ProjectService(pid=project_id).project

        return api_response(project.to_dict())


@blueprint.route('/peer', methods=['POST'])
def create_peer_project():
    """
    service api
    :return:
    """
    request_data = api_request()
    required = {'peer_id', 'peer_url'}
    if request_data.get('peer_config'):
        json_check = {'peer_config'}
    else:
        json_check = None
    api_params_check(request_data, required, json_check=json_check)

    project_id = ProjectService().create_peer_project(request_data['peer_id'], request_data['peer_url'],
                                                      request_data['peer_config'])

    return api_response(dict(project_id=project_id))


@blueprint.route('/peer/<peer_id>', methods=['PUT', 'GET'])
def update_or_get_peer_project(peer_id):
    """
    service api
    :param peer_id:
    :return:
    """
    if request.method == 'PUT':
        request_data = api_request()
        required = set()
        if request_data.get('peer_config'):
            json_check = {'peer_config'}
        else:
            json_check = None
        api_params_check(request_data, required, json_check=json_check)

        project_id = ProjectService(peer_id=peer_id).update_peer_project(peer_id, request_data['peer_config'])

        return api_response(dict(project_id=project_id))
    if request.method == 'GET':
        project = ProjectService(peer_id=peer_id).project

        return api_response(dict(project_id=project.id))


@blueprint.route('/list', methods=['GET'])
@verify_token()
def get_project_list(user):
    request_data = api_request()
    page_num = request_data.get(DB_PAGE_NUM, DB_PAGE_NUM_DEFAULT)
    page_size = request_data.get(DB_PAGE_SIZE, DB_PAGE_SIZE_DEFAULT)
    project_object_list, total = ProjectService().get_project_list(page_num=int(page_num), page_size=int(page_size))
    project_dict_list = []
    for project_object in project_object_list:
        if project_object.owner_id == str(PROJECT_DEFAULT_USER):
            owner_name = None
        else:
            owner_name = UserService(uid=project_object.owner_id).user.name
        project_dict_list.append(project_object.to_dict(added=dict(owner_name=owner_name)))

    return api_response(dict(project_list=project_dict_list, total=total))


@blueprint.route('/connect/<_id>', methods=['GET'])
@verify_token()
def get_project_connect(_id, user):
    project_id = ProjectService(pid=_id).sync_peer_service.get_peer_project()

    return api_response(dict(project_id=project_id))

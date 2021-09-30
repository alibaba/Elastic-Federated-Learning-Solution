# -*- coding: utf8 -*-

import json
import io

from flask import Blueprint, request, stream_with_context, Response
from urllib3.response import HTTPResponse

from console.user import verify_token
from console.utils import api_request, api_response, api_params_check
from console.exceptions import InvalidArgument, NotFound, AlreadyExist
from console.factory import logger, minio_client
from console.resource.service import ResourceService
from console.constant import DEFAULT_BUCKET_NAME
from console.task import TaskIntraService

blueprint = Blueprint('resource', __name__)


@blueprint.route('', methods=['POST'])
@verify_token()
def create_resource(user):
    request_data = api_request()
    required = {'task_intra_id', 'name', 'uri'}
    if request_data.get('config'):
        json_check = {'config'}
    else:
        json_check = None
    api_params_check(request_data, required, json_check=json_check)
    bucket_name, object_name = minio_client.get_uri_attribute(request_data['uri'])
    minio_object = minio_client.stat_object(bucket_name, object_name)
    if minio_object.size == 0:
        raise InvalidArgument(message='empty object error')
    if bucket_name is None or object_name is None:
        raise InvalidArgument(message='illegal uri')
    task_intra = TaskIntraService(tid=request_data['task_intra_id']).task_intra
    if not task_intra:
        raise InvalidArgument(message='task intra id not found')

    config = json.dumps(request_data.get('config')) if request_data.get('config') else None
    resource = ResourceService().create_resource(user.id, request_data['task_intra_id'], request_data['name'],
                                                 request_data['uri'], request_data.get('comment'), config)

    return api_response(resource.to_dict())


@blueprint.route('/<resource_id>', methods=['PUT', 'GET', 'DELETE'])
@verify_token()
def update_or_get_or_delete_resource(resource_id, user):
    if request.method == 'PUT':
        request_data = api_request()
        required = set()
        forbidden = {'owner_id', 'task_intra_id', 'name', 'uri'}
        if request_data.get('config'):
            json_check = {'config'}
        else:
            json_check = None
        api_params_check(request_data, required, forbidden=forbidden, json_check=json_check)

        resource = ResourceService(rid=resource_id).update_resource(request_data)

        return api_response(resource.to_dict())
    if request.method == 'GET':
        resource = ResourceService(rid=resource_id).resource

        return api_response(resource.to_dict())
    if request.method == 'DELETE':
        ResourceService(rid=resource_id).delete_resource()

        return api_response(dict(result=True))


@blueprint.route('/list/<task_intra_id>', methods=['GET'])
@verify_token()
def get_resource_list(task_intra_id, user):
    resource_object_list = ResourceService().get_resource_list(task_intra_id)
    total = len(resource_object_list)
    resource_dict_list = []
    for resource_object in resource_object_list:
        resource_dict_list.append(resource_object.to_dict())

    return api_response(dict(resource_list=resource_dict_list, total=total))


@blueprint.route('/object', methods=['POST'])
@verify_token()
def upload_object(user):
    file = request.files['data']
    if not file:
        raise InvalidArgument(message='data missing in request form')
    file_data = file.read()
    file_length = len(file_data)
    if file_length == 0:
        raise InvalidArgument(message='byte data is empty')
    file_data_stream = io.BytesIO(file_data)
    request_form = request.form
    if 'name' not in request_form:
        raise InvalidArgument(message='name missing in request form')
    object_response = minio_client.get_object(DEFAULT_BUCKET_NAME, request_form['name'])
    if object_response and len(object_response.data) != 0:
        raise AlreadyExist(message='name found in the default bucket')

    uri = minio_client.put_object(DEFAULT_BUCKET_NAME, request_form['name'], file_data_stream, file_length)

    return api_response(dict(uri=uri))


@blueprint.route('/object', methods=['GET'])
@verify_token()
def download_object(user):
    request_data = api_request()
    required = {'name'}
    api_params_check(request_data, required)

    minio_object = minio_client.stat_object(DEFAULT_BUCKET_NAME, request_data['name'])
    if minio_object.size == 0:
        raise InvalidArgument(message='empty object error')
    object_response = minio_client.get_object(DEFAULT_BUCKET_NAME, request_data['name'])
    file_data_stream = object_response.stream(minio_object.size)

    return Response(stream_with_context(file_data_stream),
                    headers={
                        'Content-Disposition': f'attachment; filename={request_data["name"]}'
                    })


@blueprint.route('/object', methods=['DELETE'])
@verify_token()
def remove_object(user):
    request_data = api_request()
    required = {'name'}
    api_params_check(request_data, required)

    minio_client.stat_object(DEFAULT_BUCKET_NAME, request_data['name'])
    minio_client.remove_object(DEFAULT_BUCKET_NAME, request_data['name'])

    return api_response(dict(result=True))

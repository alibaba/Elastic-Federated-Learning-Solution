from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import os
import json
import time
from enum import Enum

from task_interface.k8s_controller import K8sController

_EFLS_DATAJOIN_JOB_K8S_NAMESPACE = 'default'

def get_config(value, *args, **kwargs):
    default_value = kwargs.pop("default", None)
    for arg in args:
        if not isinstance(value, dict) or arg not in value:
            return default_value
        value = value[arg]
    return value

class DatajoinScheduler():

    class AppStatus(Enum):
        Success = 1
        Failed = 2
        Running = 3
        Pendding = 4

    def __init__(self, k8s_config_file, docker_secret):
        self._k8s_config_file = k8s_config_file
        self._controller = K8sController(kube_config=k8s_config_file)
        self._docker_secret = docker_secret

    def _check_job_config(self, job_config):
        if get_config(job_config, 'job_name') is None:
            raise ValueError('job_name must be set.')
        if get_config(job_config, 'input_path') is None:
            raise ValueError('input_path must be set.')
        if get_config(job_config, 'output_path') is None:
            raise ValueError('output_path must be set.')
        if get_config(job_config, 'docker_image') is None:
            raise ValueError('docker_image must be set.')

        if get_config(job_config, 'job_type') == 'feature-inc':
            if get_config(job_config, 'split_num') is None:
                raise ValueError('split_num must be set.')
            if get_config(job_config, 'worker_num') is None:
                raise ValueError('worker_num must be set.')
            if get_config(job_config, 'left_key') is None:
                raise ValueError('left_key must be set.')
            if get_config(job_config, 'right_key') is None:
                raise ValueError('right_key must be set.')
            if get_config(job_config, 'aux_table') is None:
                raise ValueError('aux_table must be set.')
        else:
            if get_config(job_config, 'bucket_num') is None:
                raise ValueError('bucket_num must be set.')
            if get_config(job_config, 'hash_col_name') is None:
                raise ValueError('hash_col_name must be set.')
            if get_config(job_config, 'sort_col_name') is None:
                raise ValueError('sort_col_name must be set.')
            if get_config(job_config, 'run_mode') is None:
                raise ValueError('run_mode must be set.')
            if get_config(job_config, 'batch_size') is None:
                raise ValueError('batch_size must be set.')
            if get_config(job_config, 'file_part_size') is None:
                raise ValueError('file_part_size must be set.')
            if get_config(job_config, 'is_server') is None:
                raise ValueError('is_server must be set.')
            if get_config(job_config, 'flink_claster') is None:
                raise ValueError('flink_claster must be set.')
            if get_config(job_config, 'wait_s') is None:
                raise ValueError('wait_s must be set.')

            if get_config(job_config, 'is_server') == 'false' or get_config(job_config, 'is_server') == 'False':
                if get_config(job_config, 'tls_path') is None:
                    raise ValueError('tls_path must be set.')
                if get_config(job_config, 'ingress_ip') is None:
                    raise ValueError('ingress_ip must be set.')
                if get_config(job_config, 'port') is None:
                    raise ValueError('port must be set.')
                if get_config(job_config, 'host') is None:
                    raise ValueError('host must be set.')

    def _get_job_name(self, job_config):
        job_name = job_config.get('job_name')
        job_suffix = ""
        if get_config(job_config, 'is_server') == 'true' or get_config(job_config, 'is_server') == 'True':
            job_suffix = "-server"
        elif get_config(job_config, 'is_server') == 'false' or get_config(job_config, 'is_server') == 'False':
            job_suffix = "-client"
        job_name = job_name + job_suffix
        return job_name

    def _generate_scheduler_datajoin_job_config(self, job_config):
        job_name = self._get_job_name(job_config)
        command = []
        if get_config(job_config, 'is_server') == 'true' or get_config(job_config, 'is_server') == 'True':
            command = ["/opt/flink/bin/flink", "run", "--target", "kubernetes-session",
                       "-Dkubernetes.cluster-id=" + job_config.get('flink_claster'),
                       "--python", "/xfl/xfl/data/main/run_data_join.py",
                       "-i", job_config.get('input_path'), "-o", job_config.get('output_path'),
                       "--job_name=" + job_config.get('job_name'), "--bucket_num=" + job_config.get('bucket_num'),
                       "--hash_col_name=" + job_config.get('hash_col_name'),
                       "--sort_col_name=" + job_config.get('sort_col_name'),
                       "--is_server=" + job_config.get('is_server'),
                       "--run_mode=" + job_config.get('run_mode'),
                       "--batch_size=" + job_config.get('batch_size'),
                       "--file_part_size=" + job_config.get('file_part_size'),
                       "--wait_s=" + job_config.get('wait_s'),
                       "--jars=file:///xfl/lib/efls-flink-connectors-1.0-SNAPSHOT.jar"]
        else :
            command =  ["/opt/flink/bin/flink", "run", "--target", "kubernetes-session",
                        "-Dkubernetes.cluster-id=" + job_config.get('flink_claster'),
                        "--python", "/xfl/xfl/data/main/run_data_join.py",
                        "-i", job_config.get('input_path'), "-o", job_config.get('output_path'),
                        "--job_name=" + job_config.get('job_name'), "--bucket_num=" + job_config.get('bucket_num'),
                        "--hash_col_name=" + job_config.get('hash_col_name'),
                        "--sort_col_name=" + job_config.get('sort_col_name'),
                        "--is_server=" + job_config.get('is_server'),
                        "--ingress_ip=" + job_config.get('ingress_ip'),
                        "--port=" + job_config.get('port'),
                        "--host=" + job_config.get('host'),
                        "--run_mode=" + job_config.get('run_mode'),
                        "--batch_size=" + job_config.get('batch_size'),
                        "--file_part_size=" + job_config.get('file_part_size'),
                        "--wait_s=" + job_config.get('wait_s'),
                        "--tls_path=" + job_config.get('tls_path'),
                        "--jars=file:///xfl/lib/efls-flink-connectors-1.0-SNAPSHOT.jar"]

        scheduler_job_config = {
            'apiVersion': 'batch/v1',
            'kind': 'Job',
            'metadata': {
                'labels': {
                    'app': job_name
                },
                'name': job_name
            },
            'spec': {
                'template': {
                    'metadata': {
                        'labels': {
                            'app': job_name
                        }
                    },
                    'spec': {
                        'imagePullSecrets': [
                            {
                                'name': self._docker_secret
                            }
                        ],
                        'restartPolicy': 'Never',
                        'containers': [
                            {
                                'command': command,
                                'image': job_config.get('docker_image'),
                                'name': "job-submit",
                                'imagePullPolicy': 'Always'
                            }
                        ]
                    }
                }
            }
        }
        return scheduler_job_config

    def _generate_scheduler_featureinc_job_config(self, job_config):
        job_name = self._get_job_name(job_config)
        command = ["python", "-m", "xfl.data.main.run_wq_local_join",
                   "--job_name=" + job_config.get('job_name'),
                   "--input_dir=" + job_config.get('input_path'),
                   "--output_dir=" + job_config.get('output_path'),
                   "--split_num=" + job_config.get('split_num')]
        left_key = job_config.get('left_key').split(",")
        right_key = job_config.get('right_key').split(",")
        aux_table = job_config.get('aux_table').split(",")
        if len(left_key) != len(right_key) or len(left_key) != len(aux_table):
            raise ValueError('left_key, right_key and aux_table are not equal in length')
        for i in range(len(left_key)):
            command.append("--left_key=" + left_key[i])
            command.append("--right_key=" + right_key[i])
            command.append("--aux_table=" + aux_table[i])
        scheduler_job_config = {
            'apiVersion': 'batch/v1',
            'kind': 'Job',
            'metadata': {
                'name': job_name
            },
            'spec': {
                'parallelism': int(job_config.get('worker_num')),
                'backoffLimit': 1,
                'template': {
                    'spec': {
                        'restartPolicy': 'Never',
                        'volumes': [
                            {
                                'name': 'nas-pv-storage',
                                'persistentVolumeClaim': {
                                    'claimName': 'nas-pvc'
                                }
                            }
                        ],
                        'imagePullSecrets': [
                            {
                                'name': self._docker_secret
                            }
                        ],
                        'containers': [
                            {
                                'command': command,
                                'image': job_config.get('docker_image'),
                                'name': "worker",
                                'volumeMounts': [
                                    {
                                        'mountPath': '/data',
                                        'name': 'nas-pv-storage'
                                    }
                                ]
                            }
                        ]
                    }
                }
            }
        }
        return scheduler_job_config

    def create_datajoin_job(self, job_config, namespace='default'):
        self._check_job_config(job_config)
        if get_config(job_config, 'job_type') == 'feature-inc':
            job_json = self._generate_scheduler_featureinc_job_config(job_config)
        else :
            job_json = self._generate_scheduler_datajoin_job_config(job_config)
        self._controller.create_job(job_json, namespace=namespace)

    def get_job_status(self, job_name, namespace='default'):
        return self._controller.get_job_status(job_name, namespace=namespace)

    def get_app_status(self, job_config, namespace='default'):
        job_name = self._get_job_name(job_config)
        job_status = self.get_job_status(job_name, namespace=namespace)
        if job_status == 'Success':
          return DatajoinScheduler.AppStatus.Success
        elif job_status == 'Pendding':
          return DatajoinScheduler.AppStatus.Pendding
        elif job_status == 'Running':
          return DatajoinScheduler.AppStatus.Running
        else:
          return DatajoinScheduler.AppStatus.Failed

    def delete_datajoin_job(self, job_config, namespace='default'):
        job_name = self._get_job_name(job_config)
        self._controller.delete_job(job_name, namespace=namespace)

    def get_job_log(self, job_config, namespace='default'):
        job_name = self._get_job_name(job_config)
        pod_names = self._controller.get_job_pod_names(job_name, namespace=namespace, get_all_pods=True)
        return self._controller.get_pod_log(pod_names[0], namespace=namespace)


_EFLS_DATAJOIN_SCHEDULER = None

def init_datajoin_scheduler(k8s_config, docker_secret):
    global _EFLS_DATAJOIN_SCHEDULER
    if _EFLS_DATAJOIN_SCHEDULER is None:
        _EFLS_DATAJOIN_SCHEDULER = DatajoinScheduler(k8s_config, docker_secret)

def create_datajoin_job(config):
    if _EFLS_DATAJOIN_SCHEDULER is None:
        raise ValueError('Datajoin scheduler has not been initialized, call init_data_join_scheduler first.')
    _EFLS_DATAJOIN_SCHEDULER.create_datajoin_job(config, _EFLS_DATAJOIN_JOB_K8S_NAMESPACE)

def kill_datajoin_job(config):
    if _EFLS_DATAJOIN_SCHEDULER is None:
        raise ValueError('Datajoin scheduler has not been initialized, call init_data_join_scheduler first.')
    _EFLS_DATAJOIN_SCHEDULER.delete_datajoin_job(config, _EFLS_DATAJOIN_JOB_K8S_NAMESPACE)

def get_job_status(job_name):
    if _EFLS_DATAJOIN_SCHEDULER is None:
        raise ValueError('Datajoin scheduler has not been initialized, call init_data_join_scheduler first.')
    return _EFLS_DATAJOIN_SCHEDULER.get_job_status(job_name, _EFLS_DATAJOIN_JOB_K8S_NAMESPACE)

def get_app_status(config):
    if _EFLS_DATAJOIN_SCHEDULER is None:
        raise ValueError('Datajoin scheduler has not been initialized, call init_data_join_scheduler first.')
    return _EFLS_DATAJOIN_SCHEDULER.get_app_status(config, _EFLS_DATAJOIN_JOB_K8S_NAMESPACE)

def get_job_log(config):
    if _EFLS_DATAJOIN_SCHEDULER is None:
        raise ValueError('Datajoin scheduler has not been initialized, call init_data_join_scheduler first.')
    return _EFLS_DATAJOIN_SCHEDULER.get_job_log(config, _EFLS_DATAJOIN_JOB_K8S_NAMESPACE)
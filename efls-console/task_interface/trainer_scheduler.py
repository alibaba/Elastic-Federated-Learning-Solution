from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import os
import json
import time
from enum import Enum

from task_interface.k8s_controller import K8sController

_EFLS_TRAIN_JOB_K8S_NAMESPACE = 'default'
_EFLS_START_TRAIN_JOB_COMMAND = '/bin/bash'
_EFLS_START_TRAIN_JOB_SCRIPT = '/efl/train/start_federal_train.sh'


def get_config(value, *args, **kwargs):
    default_value = kwargs.pop("default", None)
    for arg in args:
        if not isinstance(value, dict) or arg not in value:
            return default_value
        value = value[arg]
    return value


class TrainerScheduler():
    class AppStatus(Enum):
        Success = 1
        Failed = 2
        Running = 3
        Pendding = 4

    def __init__(self, k8s_config_file,
                 cert_file,
                 docker_secret,
                 ingress_cert_name,
                 wait_sleep_time=10):
        self._k8s_config_file = k8s_config_file
        self._controller = K8sController(kube_config=k8s_config_file)
        self._wait_sleep_time = wait_sleep_time
        self._cert_file = cert_file
        self._ingress_cert_name = ingress_cert_name
        self._docker_secret = docker_secret

    def _check_job_config(self, job_config):
        worker_config = get_config(job_config, 'worker', default={})
        if int(get_config(worker_config, 'instance_num', default=1)) < 1:
            raise ValueError('Worker number must be more than 1.')
        if int(get_config(worker_config, 'core', default=1)) < 1:
            raise ValueError('Worker core must be more than 1.')
        if int(get_config(worker_config, 'memory', default=1)) < 1:
            raise ValueError('Worker memory must be more than 1.')
        ps_config = get_config(job_config, 'ps', default={})
        if int(get_config(ps_config, 'instance_num', default=1)) < 1:
            raise ValueError('PS number must be more than 1.')
        if int(get_config(ps_config, 'core', default=1)) < 1:
            raise ValueError('PS core must be more than 1.')
        if int(get_config(ps_config, 'memory', default=1)) < 1:
            raise ValueError('PS memory must be more than 1.')
        if get_config(job_config, 'appid') is None:
            raise ValueError('Appid must be set.')
        if get_config(job_config, 'code_dir') is None:
            raise ValueError('Code dir must be set.')
        if get_config(job_config, 'script') is None:
            raise ValueError('Script must be set.')
        if get_config(job_config, 'docker_image') is None:
            raise ValueError('Docker image must be set.')
        if get_config(job_config, 'job_type', 'federal') == 'federal':
            if get_config(job_config, 'federal_role') is None:
                raise ValueError('`federal_role` must be set one of [leader/follower] when run `job_type` is `federal`')

    def _generate_template_config(self, job_config, command, arguments):
        body = {'metadata': {'labels': {'app': 'test'},
                             'name': 'test'},
                'spec': {'replicas': 1}}
        body['spec']['template'] = {'metadata': {'labels': {'app': 'test'}},
                                    'spec': {'containers': []}}
        body['spec']['template']['spec']['containers'].append(
            {'args': arguments,
             'command': [command],
             'env': [],
             'image': get_config(job_config, 'docker_image', default=''),
             'name': 'test',
             'resources': {'requests': {'cpu': '1000m',
                                        'memory': '500Mi'},
                           'limites': {'cpu': '1000m',
                                       'memory': '500Mi'}},
             'ports': [{'containerPort': 50051}]})
        if not get_config(job_config, 'use_docker_secret') == 'false':
            body['spec']['template']['spec']['imagePullSecrets'] = [{'name': self._docker_secret}]
            body['spec']['template']['spec']['containers'][0]['imagePullPolicy'] = 'Always'
        if not get_config(job_config, 'volume_mount') == 'false':
            body['spec']['template']['spec']['volumes'] = [{'name': 'nas-pv-storage',
                                                            'persistentVolumeClaim': {'claimName': 'nas-pvc'}}]
            body['spec']['template']['spec']['containers'][0]['volumeMounts'] = [
                {'name': 'nas-pv-storage', 'mountPath': '/data'}]
        body['spec']['template']['spec']['containers'][0]['env'].append(
            {'name': 'CODE_DIR', 'value': get_config(job_config, 'code_dir', default='')})
        body['spec']['template']['spec']['containers'][0]['env'].append(
            {'name': 'JOB_SCRIPT', 'value': get_config(job_config, 'script')})
        train_config = json.dumps(get_config(job_config, 'train_config', default={}))
        body['spec']['template']['spec']['containers'][0]['env'].append(
            {'name': 'TRAIN_CONFIG', 'value': train_config})
        body['spec']['template']['spec']['containers'][0]['env'].append(
            {'name': 'MODEL_DIR', 'value': get_config(job_config, 'model_dir', default='/')})
        body['spec']['template']['spec']['containers'][0]['env'].append(
            {'name': 'APPID', 'value': get_config(job_config, 'appid', default='')})
        body['spec']['template']['spec']['containers'][0]['env'].append(
            {'name': 'PS_NUM', 'value': str(get_config(job_config, 'ps', 'instance_num', default=''))})
        body['spec']['template']['spec']['containers'][0]['env'].append(
            {'name': 'WORKER_NUM', 'value': str(get_config(job_config, 'worker', 'instance_num', default=''))})
        body['spec']['template']['spec']['containers'][0]['env'].append(
            {'name': 'FEDERAL_ROLE', 'value': get_config(job_config, 'federal_role', default='NULL')})
        body['spec']['template']['spec']['containers'][0]['env'].append(
            {'name': 'ZK_ADDR', 'value': get_config(job_config, 'zk_addr')})
        body['spec']['template']['spec']['containers'][0]['env'].append(
            {'name': 'EFL_PEER_CERTS_FILENAME', 'value': self._cert_file})
        body['spec']['template']['spec']['containers'][0]['env'].append(
            {'name': 'PEER_ADDR', 'value': get_config(job_config, 'peer_addr')})
        body['spec']['template']['spec']['containers'][0]['env'].append(
            {'name': 'TF_CPP_MIN_LOG_LEVEL', 'value': get_config(job_config, 'log_level', default='2')})
        return body

    def _generate_template_deploy_config(self, job_config, command, arguments):
        body = self._generate_template_config(job_config, command, arguments)
        body['apiVersion'] = 'apps/v1'
        body['kind'] = 'Deployment'
        body['spec']['selector'] = {'matchLables': {'app': 'test'}}
        return body

    def _generate_template_job_config(self, job_config, command, arguments):
        body = self._generate_template_config(job_config, command, arguments)
        body['apiVersion'] = 'batch/v1'
        body['kind'] = 'Job'
        return body

    def _generate_worker_job_config(self, appid, index, job_config,
                                    command, arguments):
        body = self._generate_template_job_config(job_config, command, arguments)
        job_name = self.worker_name(appid, index)
        core = int(get_config(job_config, 'worker', 'core')) * 1000
        core = str(core) + 'm'
        memory = str(get_config(job_config, 'worker', 'memory')) + 'Mi'
        body['metadata']['name'] = job_name
        body['metadata']['labels']['app'] = job_name
        body['spec']['template']['spec']['restartPolicy'] = 'Never'
        body['spec']['template']['spec']['containers'][0]['name'] = job_name
        body['spec']['template']['metadata']['labels']['app'] = job_name
        body['spec']['template']['spec']['containers'][0]['resources']['requests']['cpu'] = core
        body['spec']['template']['spec']['containers'][0]['resources']['limites']['cpu'] = core
        body['spec']['template']['spec']['containers'][0]['resources']['requests']['memory'] = memory
        body['spec']['template']['spec']['containers'][0]['resources']['limites']['memory'] = memory
        body['spec']['template']['spec']['containers'][0]['env'].append(
            {'name': 'TASK_NAME', 'value': 'worker'})
        body['spec']['template']['spec']['containers'][0]['env'].append(
            {'name': 'TASK_INDEX', 'value': str(index)})
        peer_appid = get_config(job_config, 'peer_appid')
        if not peer_appid:
            peer_appid = get_config(job_config, 'appid')
        body['spec']['template']['spec']['containers'][0]['env'].append(
            {'name': 'EFL_SSL_TARGET_NAME_OVERRIDE',
             'value': peer_appid + '-worker-' + str(index) + '.' + get_config(job_config,
                                                                              'target_hostname')})
        return body

    def _generate_ps_job_config(self, appid, index, job_config,
                                command, arguments):
        body = self._generate_template_job_config(job_config, command, arguments)
        job_name = self.ps_name(appid, index)
        core = int(get_config(job_config, 'ps', 'core')) * 1000
        core = str(core) + 'm'
        memory = str(get_config(job_config, 'ps', 'memory')) + 'Mi'
        body['metadata']['name'] = job_name
        body['metadata']['labels']['app'] = job_name
        body['spec']['template']['spec']['restartPolicy'] = 'Never'
        body['spec']['template']['spec']['containers'][0]['name'] = job_name
        body['spec']['template']['metadata']['labels']['app'] = job_name
        body['spec']['template']['spec']['containers'][0]['resources']['requests']['cpu'] = core
        body['spec']['template']['spec']['containers'][0]['resources']['limites']['cpu'] = core
        body['spec']['template']['spec']['containers'][0]['resources']['requests']['memory'] = memory
        body['spec']['template']['spec']['containers'][0]['resources']['limites']['memory'] = memory
        body['spec']['template']['spec']['containers'][0]['env'].append(
            {'name': 'TASK_NAME', 'value': 'ps'})
        body['spec']['template']['spec']['containers'][0]['env'].append(
            {'name': 'TASK_INDEX', 'value': str(index)})
        return body

    def _generate_scheduler_job_config(self, appid, job_config,
                                       command, arguments):
        body = self._generate_template_job_config(job_config, command, arguments)
        job_name = self.scheduler_name(appid, 0)
        core = '1000m'
        memory = '500Mi'
        body['metadata']['name'] = job_name
        body['metadata']['labels']['app'] = job_name
        body['spec']['template']['spec']['restartPolicy'] = 'Never'
        body['spec']['template']['spec']['containers'][0]['name'] = job_name
        body['spec']['template']['metadata']['labels']['app'] = job_name
        body['spec']['template']['spec']['containers'][0]['resources']['requests']['cpu'] = core
        body['spec']['template']['spec']['containers'][0]['resources']['limites']['cpu'] = core
        body['spec']['template']['spec']['containers'][0]['resources']['requests']['memory'] = memory
        body['spec']['template']['spec']['containers'][0]['resources']['limites']['memory'] = memory
        body['spec']['template']['spec']['containers'][0]['env'].append(
            {'name': 'TASK_NAME', 'value': 'scheduler'})
        body['spec']['template']['spec']['containers'][0]['env'].append(
            {'name': 'TASK_INDEX', 'value': '0'})
        return body

    def _create_cluster_job(self, appid, worker_num, ps_num,
                            job_config, command, arguments,
                            namespace='default'):
        for i in range(worker_num):
            job_json = self._generate_worker_job_config(appid, i, job_config,
                                                        command, arguments)
            self._controller.create_job(job_json, namespace=namespace)
        for i in range(ps_num):
            job_json = self._generate_ps_job_config(appid, i, job_config,
                                                    command, arguments)
            self._controller.create_job(job_json, namespace=namespace)
        job_json = self._generate_scheduler_job_config(appid, job_config,
                                                       command, arguments)
        self._controller.create_job(job_json, namespace=namespace)

    def _generate_worker_service_config(self, appid, index):
        metadata = {'name': self.service_name(appid, index)}
        spec = {'type': 'ClusterIP',
                'ports': [{'port': 80,
                           'protocal': 'TCP',
                           'targetPort': 50051}],
                'selector': {'app': self.worker_name(appid, index)}}
        return metadata, spec

    def _create_cluster_service(self, appid, worker_num, namespace='default'):
        for i in range(worker_num):
            metadata, spec = self._generate_worker_service_config(appid, i)
            self._controller.create_service(metadata, spec, namespace=namespace)

    def _generate_ingress_config(self, appid, worker_num):
        metadata = {'name': self.ingress_name(appid),
                    'annotations': {
                        'kubernetes.io/ingress.class': "nginx",
                        'nginx.ingress.kubernetes.io/ssl-redirect': "true",
                        'nginx.ingress.kubernetes.io/backend-protocol': "GRPC"
                    }
                    }
        spec = {'rules': [], 'tls': [{'secretName': self._ingress_cert_name, 'hosts': []}]}
        for i in range(worker_num):
            rule = {'host': '{}.alifl.alibaba-inc.com'.format(self.worker_name(appid, i)),
                    'http': {'paths': [{'path': '/',
                                        'pathType': 'Prefix',
                                        'backend': {'serviceName': '{}'.format(self.service_name(appid, i)),
                                                    'servicePort': 80}}]}}
            spec['rules'].append(rule)
        spec['tls'][0]['hosts'].append('{}.alifl.alibaba-inc.com'.format(self.worker_name(appid, i)))
        return metadata, spec

    def _create_cluster_ingress(self, appid, worker_num, namespace='default'):
        metadata, spec = self._generate_ingress_config(appid, worker_num)
        self._controller.create_ingress(metadata, spec, namespace=namespace)

    def worker_name(self, appid, index):
        return '{}-worker-{}'.format(appid, index)

    def ps_name(self, appid, index):
        return '{}-ps-{}'.format(appid, index)

    def scheduler_name(self, appid, index):
        return '{}-scheduler-{}'.format(appid, index)

    def service_name(self, appid, index):
        return '{}-service-{}'.format(appid, index)

    def ingress_name(self, appid):
        return '{}-ingress'.format(appid)

    def _wait_for_cluster_ready(self, appid, worker_num, ps_num, namespace='default'):
        for job_num, name_fn in zip([worker_num, ps_num, 1], [self.worker_name, self.ps_name, self.scheduler_name]):
            for i in range(job_num):
                job_name = name_fn(appid, i)
                while not self._controller.job_ready(job_name, namespace=namespace):
                    print('Job is pending, waiting for {} ready...'.format(job_name))
                    time.sleep(self._wait_sleep_time)

    def get_job_status(self, job_name, namespace='default'):
        return self._controller.get_job_status(job_name, namespace=namespace)

    def get_app_status(self, job_config, namespace='default'):
        appid = get_config(job_config, 'appid')
        worker_num = get_config(job_config, 'worker', 'instance_num', default=1)
        job_name = self.worker_name(appid, 0)
        if self.get_job_status(job_name, namespace=namespace) == 'Success':
            return TrainerScheduler.AppStatus.Success
        for i in range(worker_num):
            job_status = self.get_job_status(job_name, namespace=namespace)
            if job_status == 'Pendding':
                return TrainerScheduler.AppStatus.Pendding
            elif job_status == 'Running':
                continue
            else:
                return TrainerScheduler.AppStatus.Failed
        return TrainerScheduler.AppStatus.Running

    def create_train_job(self, job_config,
                         command, arguments,
                         namespace='default'):
        self._check_job_config(job_config)
        appid = get_config(job_config, 'appid')
        worker_num = get_config(job_config, 'worker', 'instance_num', default=1)
        ps_num = get_config(job_config, 'ps', 'instance_num', default=1)
        self._create_cluster_job(appid, worker_num, ps_num,
                                 job_config, command, arguments,
                                 namespace)
        self._create_cluster_service(appid, worker_num, namespace)
        self._create_cluster_ingress(appid, worker_num, namespace)

    def delete_train_job(self, job_config, namespace='default'):
        self._check_job_config(job_config)
        appid = get_config(job_config, 'appid')
        worker_num = get_config(job_config, 'worker', 'instance_num', default=1)
        ps_num = get_config(job_config, 'ps', 'instance_num', default=1)
        for deploy_num, name_fn in zip([worker_num, ps_num, 1], [self.worker_name, self.ps_name, self.scheduler_name]):
            for i in range(deploy_num):
                job_name = name_fn(appid, i)
                self._controller.delete_job(job_name, namespace=namespace)
        for i in range(worker_num):
            service_name = self.service_name(appid, i)
            self._controller.delete_service(service_name, namespace=namespace)
        ingress_name = self.ingress_name(appid)
        self._controller.delete_ingress(ingress_name, namespace=namespace)


_EFLS_TRAINER_SCHEDULER = None


def init_trainer_scheduler(k8s_config, cert_file_path, docker_secret, ingress_cert_name):
    global _EFLS_TRAINER_SCHEDULER
    if _EFLS_TRAINER_SCHEDULER is None:
        _EFLS_TRAINER_SCHEDULER = TrainerScheduler(
            k8s_config,
            cert_file_path,
            docker_secret,
            ingress_cert_name)


def create_train_job(config,
                     command=None,
                     arguments=None):
    if command is None:
        command = _EFLS_START_TRAIN_JOB_COMMAND
    if arguments is None:
        arguments = [_EFLS_START_TRAIN_JOB_SCRIPT]
    if not isinstance(arguments, (list, tuple)):
        arguments = [arguments]
    if _EFLS_TRAINER_SCHEDULER is None:
        raise ValueError('Trainer scheduler has not been initialized, call init_trainer_scheduler first.')
    _EFLS_TRAINER_SCHEDULER.create_train_job(config,
                                             command,
                                             arguments,
                                             _EFLS_TRAIN_JOB_K8S_NAMESPACE)


def kill_train_job(config):
    if _EFLS_TRAINER_SCHEDULER is None:
        raise ValueError('Trainer scheduler has not been initialized, call init_trainer_scheduler first.')
    _EFLS_TRAINER_SCHEDULER.delete_train_job(config,
                                             _EFLS_TRAIN_JOB_K8S_NAMESPACE)


def get_job_status(job_name):
    if _EFLS_TRAINER_SCHEDULER is None:
        raise ValueError('Trainer scheduler has not been initialized, call init_trainer_scheduler first.')
    return _EFLS_TRAINER_SCHEDULER.get_job_status(job_name, _EFLS_TRAIN_JOB_K8S_NAMESPACE)


def get_app_status(config):
    if _EFLS_TRAINER_SCHEDULER is None:
        raise ValueError('Trainer scheduler has not been initialized, call init_trainer_scheduler first.')
    return _EFLS_TRAINER_SCHEDULER.get_app_status(config, _EFLS_TRAIN_JOB_K8S_NAMESPACE)

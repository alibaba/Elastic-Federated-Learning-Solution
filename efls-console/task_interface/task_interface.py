# -*- coding: utf8 -*-

import time
import os
import re
import json

from console.models import TaskIntra, TaskInstance
from console.task import TaskTypeEnum
from console.task_instance.task_instance_enum import TaskInstanceStatusEnum
from console.factory import logger
from console.task_instance.service import TaskInstanceService
from task_interface import trainer_scheduler
from task_interface import data_join_scheduler


class TaskInterface:
    def __init__(self, task: TaskIntra, task_instance: TaskInstance, resource_uri_list: list):
        self.task = task
        self.instance = task_instance
        self.resource_uri_list = resource_uri_list

    @staticmethod
    def get_task_log(log_dir):
        stdout_dict = {}
        stderr_dict = {}
        job_roles = os.listdir(log_dir)
        for role in job_roles:
            with open(os.path.join(log_dir, role, "stdout"), 'r') as f:
                msg = f.read()
            stdout_dict[role] = msg
            with open(os.path.join(log_dir, role, "stderr"), 'r') as f:
                msg = f.read()
            stderr_dict[role] = msg
        return stdout_dict, stderr_dict

    @staticmethod
    def get_job_loglink(job_log):
        try:
            flink_urls = re.findall('https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+:[\d]+', job_log)
            job_ids = re.findall('JobID [\da-zA-Z]+', job_log)
            job_ids = job_ids[0].split(' ')
            jobs_url = "{}/#/job/{}/overview".format(flink_urls[0], job_ids[1])
        except Exception as e:
            logger.info(msg=f"Got exception when get job log link, error: {e}")
            logger.info(msg=f"job log:{job_log}")
            call_back(status=TaskInstanceStatusEnum.FAILED.value)
        return jobs_url

    @staticmethod
    def task_run(task: TaskIntra, instance: TaskInstance, resource_uri_list: list, task_instance_id: str):
        """
        message in call_back is used to store logview and similar stdout info
        error in call_back is used to store error and similar stderr info
        gmt_start in call_back is used to record task start time
        gmt_error in call_back is used to record task error time
        status in call_back is used to record task current status, use values in InstanceStatusEnum
        :param resource_uri_list:
        :param instance:
        :param task:
        :param call_back:
        :return:
        """
        task_instance_service = TaskInstanceService(task_instance_id=task_instance_id)
        call_back = task_instance_service.update_task_instance
        if task.type == TaskTypeEnum.SAMPLE.value:
            task_config = task.config
            if isinstance(task_config, str):
                task_config = json.loads(task_config)
            logger.info(
                msg=f'sample type task run, task intra: {task.to_dict()}, instance: {instance.to_dict()}, '
                    f'resource_uri_list: {resource_uri_list}, task_instance_id: {task_instance_id}')
            data_join_scheduler.init_datajoin_scheduler(
                task_config.get('k8s_config'), task_config.get('docker_secret'))
            data_join_scheduler.create_datajoin_job(task_config)

            time.sleep(20)

            while True:
                try:
                    if data_join_scheduler.get_app_status(task_config) == \
                        data_join_scheduler.DatajoinScheduler.AppStatus.Running:
                        if task_config.get('job_type') != 'feature-inc':
                            job_log = data_join_scheduler.get_job_log(task_config)
                            job_log_link = TaskInterface.get_job_loglink(job_log)
                            message = {'job_log_link': job_log_link}
                            call_back(message=message, error=message)
                        call_back(status=TaskInstanceStatusEnum.RUNNING.value)
                        time.sleep(20)
                    elif data_join_scheduler.get_app_status(task_config) == \
                        data_join_scheduler.DatajoinScheduler.AppStatus.Failed:
                        if task_config.get('job_type') != 'feature-inc':
                            job_log = data_join_scheduler.get_job_log(task_config)
                            job_log_link = TaskInterface.get_job_loglink(job_log)
                            message = {'job_log_link': job_log_link}
                            call_back(message=message, error=message)
                        call_back(status=TaskInstanceStatusEnum.FAILED.value)
                        data_join_scheduler.kill_datajoin_job(task_config)
                        break
                    elif data_join_scheduler.get_app_status(task_config) == \
                        data_join_scheduler.DatajoinScheduler.AppStatus.Success:
                        if task_config.get('job_type') != 'feature-inc':
                            job_log = data_join_scheduler.get_job_log(task_config)
                            job_log_link = TaskInterface.get_job_loglink(job_log)
                            message = {'job_log_link': job_log_link}
                            call_back(message=message, error=message)
                        call_back(status=TaskInstanceStatusEnum.TERMINATED.value)
                        data_join_scheduler.kill_datajoin_job(task_config)
                        break
                except KeyboardInterrupt:
                    call_back(status=TaskInstanceStatusEnum.FAILED.value)
                    data_join_scheduler.kill_datajoin_job(task_config)
                    break
                except Exception as e:
                    call_back(status=TaskInstanceStatusEnum.FAILED.value)
                    data_join_scheduler.kill_datajoin_job(task_config)
                    break
        elif task.type == TaskTypeEnum.TRAIN.value:
            try:
                task_config = task.config
                if isinstance(task_config, str):
                    task_config = json.loads(task_config)
                logger.info(
                    msg=f'train type task run, task intra: {task.to_dict()}, instance: {instance.to_dict()}, '
                        f'resource_uri_list: {resource_uri_list}, task_instance_id: {task_instance_id}')
                trainer_scheduler.init_trainer_scheduler(
                    task_config.get('k8s_config'), task_config.get('cert_file_path'),
                    task_config.get('docker_secret'), task_config.get('ingress_cert_name'))
                if task_config.get('debug_test'):
                    trainer_scheduler.create_train_job(task_config, '/bin/bash', '/efl/train/print_env.sh')
                else:
                    trainer_scheduler.create_train_job(task_config)
    
                appid = task_config.get('appid')
                log_dir = os.path.join("/data/efl-logs/", appid)
                time.sleep(20)
            except Exception as e:
                logger.info(msg=f"Got exception when schedule job, error: {e}")
                call_back(status=TaskInstanceStatusEnum.FAILED.value)
            while True:
                try:
                    if trainer_scheduler.get_app_status(task_config) == \
                            trainer_scheduler.TrainerScheduler.AppStatus.Running:
                        call_back(status=TaskInstanceStatusEnum.RUNNING.value)
                        if task_config.get('debug_test'):
                            msg = f"This is a mock log, please check whether pod env equals to config. Env: kubectl logs -f xxx."
                            message = {'worker-0': msg, 'ps-0': msg, 'scheduler-0': msg}
                            call_back(message=message, error=message)
                        else:
                            stdout_dict, stderr_dict = TaskInterface.get_task_log(log_dir)
                            call_back(message=stdout_dict, error=stderr_dict)
                        time.sleep(20)
                    elif trainer_scheduler.get_app_status(task_config) == \
                            trainer_scheduler.TrainerScheduler.AppStatus.Failed:
                        call_back(status=TaskInstanceStatusEnum.FAILED.value)
                        if task_config.get('debug_test'):
                            msg = f"This is a mock log, please check whether pod env equals to config. Env: kubectl logs -f xxx."
                            message = {'worker-0': msg, 'ps-0': msg, 'scheduler-0': msg}
                            call_back(message=message, error=message)
                        else:
                            stdout_dict, stderr_dict = TaskInterface.get_task_log(log_dir)
                            call_back(message=stdout_dict, error=stderr_dict)
                        trainer_scheduler.kill_train_job(task_config)
                        break
                    elif trainer_scheduler.get_app_status(task_config) == \
                            trainer_scheduler.TrainerScheduler.AppStatus.Success:
                        call_back(status=TaskInstanceStatusEnum.TERMINATED.value)
                        if task_config.get('debug_test'):
                            msg = f"This is a mock log, please check whether pod env equals to config. Env: kubectl logs -f xxx."
                            message = {'worker-0': msg, 'ps-0': msg, 'scheduler-0': msg}
                            call_back(message=message, error=message)
                        else:
                            stdout_dict, stderr_dict = TaskInterface.get_task_log(log_dir)
                            call_back(message=stdout_dict, error=stderr_dict)
                        trainer_scheduler.kill_train_job(task_config)
                        break
                except KeyboardInterrupt:
                    trainer_scheduler.kill_train_job(task_config)
                    call_back(status=TaskInstanceStatusEnum.FAILED.value)
                    break
                except Exception as e:
                    trainer_scheduler.kill_train_job(task_config)
                    call_back(status=TaskInstanceStatusEnum.FAILED.value)
                    break

    @staticmethod
    def task_start(task: TaskIntra, instance: TaskInstance, resource_uri_list: list, task_instance_id: str):
        task_instance_service = TaskInstanceService(task_instance_id=task_instance_id)
        call_back = task_instance_service.update_task_instance
        if task.type == TaskTypeEnum.SAMPLE.value:
            logger.info(
                msg=f'sample type task start, task intra: {task.to_dict()}, instance: {instance.to_dict()}, '
                    f'resource_uri_list: {resource_uri_list}, task_instance_id: {task_instance_id}')
            call_back(gmt_error=time.time())
            pass  # start sample task
        if task.type == TaskTypeEnum.TRAIN.value:
            logger.info(
                msg=f'train type task start, task intra: {task.to_dict()}, instance: {instance.to_dict()}, '
                    f'resource_uri_list: {resource_uri_list},  task_instance_id: {task_instance_id}')
            call_back(gmt_error=time.time())
            pass  # start training task

    @staticmethod
    def task_stop(task: TaskIntra, instance: TaskInstance, resource_uri_list: list, task_instance_id: str):
        task_instance_service = TaskInstanceService(task_instance_id=task_instance_id)
        call_back = task_instance_service.update_task_instance
        if task.type == TaskTypeEnum.SAMPLE.value:
            task_config = task.config
            if isinstance(task_config, str):
                task_config = json.loads(task_config)
            logger.info(
                msg=f'sample type task stop, task intra: {task.to_dict()}, instance: {instance.to_dict()}, '
                    f'resource_uri_list: {resource_uri_list}, task_instance_id: {task_instance_id}')
            data_join_scheduler.init_datajoin_scheduler(
                task_config.get('k8s_config'), task_config.get('docker_secret'))
            data_join_scheduler.kill_datajoin_job(task_config)
            call_back(status=TaskInstanceStatusEnum.TERMINATED.value)
        elif task.type == TaskTypeEnum.TRAIN.value:
            task_config = task.config
            if isinstance(task_config, str):
                task_config = json.loads(task_config)
            logger.info(
                msg=f'train type task stop, task intra: {task.to_dict()}, instance: {instance.to_dict()}, '
                    f'resource_uri_list: {resource_uri_list}, task_instance_id: {task_instance_id}')
            trainer_scheduler.init_trainer_scheduler(
                task_config.get('k8s_config'), task_config.get('cert_file_path'),
                task_config.get('docker_secret'), task_config.get('ingress_cert_name'))
            trainer_scheduler.kill_train_job(task_config)
            call_back(status=TaskInstanceStatusEnum.TERMINATED.value)

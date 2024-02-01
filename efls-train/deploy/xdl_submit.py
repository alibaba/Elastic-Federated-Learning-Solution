from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import sys
import os
import json
import argparse

# import xdl_deploy
import time
import non_federal_task_scheduler
import federal_task_scheduler
from task_controller import get_config

parser = argparse.ArgumentParser(description="xdl arguments")
parser.add_argument('-c', '--config')
parser.add_argument('--kill', default=False)
parser.add_argument('--addr', default=None)
parser.add_argument('--federal', default=True)

def record_logs(config, task_scheduler):
  task_scheduler.record_logs(config)

def create_job(config_file, task_scheduler):
  with open(config_file, 'r') as f:
    config = json.load(f)
  task_scheduler.create_train_job(config)
  appid = config.get('appid')
  print("================================================================================================")
  print("XDL Job is Running. Appid: {}".format(appid))
  print("You can dump logviews to local by")
  print("command: `python xdl_logview.py {} [task_name] [task_index]`".format(appid))
  print("example: `bash dump_logview.sh {} worker 0` to get worker0's logview".format(appid))
  print("You can kill job by command: `python xdl_submit.py --kill --config config_file`")
  print("================================================================================================")
  
  while True:
    try:
      if task_scheduler.get_app_status(config) == \
          task_scheduler.TrainerScheduler.AppStatus.Running:
        time.sleep(20)
      elif task_scheduler.get_app_status(config) == \
          task_scheduler.TrainerScheduler.AppStatus.Failed:
        print("XDL Job is Failed. Appid: {}, start to clean job".format(appid))
        # print(non_federal_task_scheduler.get_app_status(config))
        record_logs(config, task_scheduler)
        task_scheduler.kill_train_job(config)
        break
      elif task_scheduler.get_app_status(config) == \
          task_scheduler.TrainerScheduler.AppStatus.Success:
        print("XDL Job is Successed. Appid: {}, start to clean job.".format(appid))
        record_logs(config, task_scheduler)
        task_scheduler.kill_train_job(config)
        break
    except KeyboardInterrupt:
      print("Got KeyboardInterrupt. Appid: {}, start to clean job.".format(appid))
      record_logs(config, task_scheduler)
      task_scheduler.kill_train_job(config)
      break

def kill_job(config_file, task_scheduler):
  with open(config_file, 'r') as f:
    config = json.load(f)
  record_logs(config, task_scheduler)
  task_scheduler.kill_train_job(config)

if __name__ == "__main__":
  job_args, unknown = parser.parse_known_args()
  if job_args.addr is None:
    addr = '39.106.55.247:443'
  else:
    addr = job_args.addr
  config_file = job_args.config

  with open(config_file, 'r') as f:
    config = json.load(f)
  if job_args.federal:
    task_scheduler = federal_task_scheduler
  else:
    task_scheduler = non_federal_task_scheduler
  cert_file_path = get_config(config, "cert_file_path", default='./trainer.crt')
  if "docker_secret" in config:
    docker_secret = get_config(config, "docker_secret")
  else:
    docker_secret = "<YOUR_DOCKER_SECRET>"
  ingress_cert_name = get_config(config, "ingress_cert_name", default="efl-trainer")
  task_scheduler.init_trainer_scheduler("deploy/k8s_config.yaml", cert_file_path, docker_secret, ingress_cert_name)
  if job_args.kill:
    kill_job(config_file, task_scheduler)
  else:
    create_job(config_file, task_scheduler)

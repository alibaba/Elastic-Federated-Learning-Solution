# 快速开始

## 安装

参考  [部署手册](manifests/README.md)， 在云原生环境部署控制台

## 项目结构

* /alembic: 数据库版本管理目录
* /config: 配置目录，default_local 是 host 的一个案例, default_peer 是 peer 的一个案例，可以部署双边或者单测。 环境变量 `ENV` 设置使用的配置文件名，以加载对应的配置.
* /console: 联邦学习控制台源码目录
    * /connect: 连接模块
    * /constant: 常数模块
    * /database: 数据库模块
    * /exceptions: 项目标准化异常模块
    * /log: 项目标准化日志模块
    * /minio: 项目对象存储模块
    * /models: 数据库 ORM 模块
    * /project: 媒体方模块
    * /task: 任务模块
    * /task_instance: 任务实例模块
    * /user: 用户模块
    * /utils: 工具模块
* /front_end: 前端目录
* /manifests: kubernetes manifests
* /task_interface: 引擎和控制台的交互目录

## Dockerfile

参考镜像构建命令

```commandline
docker build --build-arg ENV_ARG=default_local --build-arg EXPOSE_ARG=5000 -t alifl/console/host:v1 .
docker build --build-arg ENV_ARG=default_peer --build-arg EXPOSE_ARG=5001 -t alifl/console/peer:v1 .
```

## 异构部署手册
### 1.二次开发 efls-console
#### 1.1 开发 task_interface
task_interface/task_interface.py  
开发 console 和数据求交/训练的接口，定义了 console 的启动、重启、停止、日志上报、状态控制功能

```python 
# -*- coding: utf8 -*-

import time

from console.models import TaskIntra, Instance
from console.models import TaskIntra, TaskInstance
from console.task import TaskTypeEnum
from console.instance.instance_enum import InstanceStatusEnum
from console.task_instance.task_instance_enum import TaskInstanceStatusEnum
from console.factory import logger


class TaskInterface:
    def __init__(self, task: TaskIntra, instance: Instance, resource_uri_list: list):
    def __init__(self, task: TaskIntra, task_instance: TaskInstance, resource_uri_list: list):
        self.task = task
        self.instance = instance
        self.instance = task_instance
        self.resource_uri_list = resource_uri_list

    def task_run(self, call_back):
        """
        message in call_back is used to store logview and similar stdout info
        error in call_back is used to store error and similar stderr info
        gmt_start in call_back is used to record task start time
        gmt_error in call_back is used to record task error time
        status in call_back is used to record task current status, use values in InstanceStatusEnum
        :param call_back:
        :return:
        """
        if self.task.type == TaskTypeEnum.SAMPLE.value:
            logger.info(
                msg=f'sample type task run, task intra: {self.task.to_dict()}, instance: {self.instance.to_dict()}, '
                    f'resource_uri_list: {self.resource_uri_list}')
            call_back(gmt_error=time.time())
            pass  # run sample task
            # call_back(message, error, gmt_start, gmt_error, status)
        if self.task.type == TaskTypeEnum.TRAIN.value:
            logger.info(
                msg=f'train type task run, task intra: {self.task.to_dict()}, instance: {self.instance.to_dict()}, '
                    f'resource_uri_list: {self.resource_uri_list}')
            call_back(gmt_error=time.time())
            pass  # run training task
            # call_back(message, error, gmt_start, gmt_error, status)

    def task_start(self, call_back):
        if self.task.type == TaskTypeEnum.SAMPLE.value:
            logger.info(
                msg=f'sample type task start, task intra: {self.task.to_dict()}, instance: {self.instance.to_dict()}, '
                    f'resource_uri_list: {self.resource_uri_list}')
            call_back(gmt_error=time.time())
            pass  # start sample task
        if self.task.type == TaskTypeEnum.TRAIN.value:
            logger.info(
                msg=f'train type task start, task intra: {self.task.to_dict()}, instance: {self.instance.to_dict()}, '
                    f'resource_uri_list: {self.resource_uri_list}')
            call_back(gmt_error=time.time())
            pass  # start training task

    def task_stop(self, call_back):
        if self.task.type == TaskTypeEnum.SAMPLE.value:
            logger.info(
                msg=f'sample type task stop, task intra: {self.task.to_dict()}, instance: {self.instance.to_dict()}')
            call_back(gmt_error=time.time())
            pass  # stop sample task
        if self.task.type == TaskTypeEnum.TRAIN.value:
            logger.info(
                msg=f'train type task stop, task intra: {self.task.to_dict()}, instance: {self.instance.to_dict()}')
            call_back(gmt_error=time.time())
            pass  # stop training task
```

#### 1.2 部署
依赖：mysql, minio
根据部署方式设置好对应的环境变量，启动 docker

```bash
# 下载 console 
git clone https://github.com/alibaba/Elastic-Federated-Learning-Solution.git
cd Elastic-Federated-Learning-Solution/efls-console/

# 制作 docker
sudo docker build --build-arg ENV_ARG=default_local --build-arg EXPOSE_ARG=5000 -t alifl/console/host:v1 . 
# 如果报错 Error: Failed to download metadata for repo 'appstream': Cannot prepare internal mirrorlist: No URLs in mirrorlist
# Dockerfile 加入
RUN cd /etc/yum.repos.d/
RUN sed -i 's/mirrorlist/#mirrorlist/g' /etc/yum.repos.d/CentOS-*
RUN sed -i 's|#baseurl=http://mirror.centos.org|baseurl=http://vault.centos.org|g' /etc/yum.repos.d/CentOS-*

# 获取 mysql-8 docker
sudo docker pull mysql:8.0.23

# 启动 mysql, minio
sudo docker run -p 3306:3306 --name mysql \
-v /usr/local/docker/mysql/mysql-files:/var/lib/mysql-files \
-v /usr/local/docker/mysql/conf:/etc/mysql \
-v /usr/local/docker/mysql/logs:/var/log/mysql \
-v /usr/local/docker/mysql/data:/var/lib/mysql \
-e MYSQL_ROOT_PASSWORD=Ali-fl \
-e MYSQL_DATABASE=alifl \
-d mysql:8.0.23
sudo docker run -p 9000:9000 --name minio \
-e "MINIO_ACCESS_KEY=alifl" \
-e "MINIO_SECRET_KEY=aliflminio" \
-v /mnt/data:/data \
-v /mnt/config:/root/.minio \
-d minio/minio server /data 

# 启动 console，配置容器可连通的 IP
sudo docker run -p 5000:5000 --name efls-console \
-e "ENV=default_local" \
-e "STATIC=host" \
-e "MYSQL_SERVICE_HOST=111.11.1.1" \
-e "MYSQL_SERVICE_PORT=3306" \
-e "MINIO_SERVICE_SERVICE_HOST=111.11.1.1" \
-e "MINIO_SERVICE_SERVICE_PORT=9000" \
-d alifl/console/host:v1 
```

### 2.基于 efls-console 协议开发 console
#### 2.1 project
create 
POST /project/peer
```json
{
    "peer_id": xx,
    "peer_url": xx,
    "peer_config": xx
}
```

update
PUT /project/peer/$project_id
```json
{
    "peer_config": xx
}
```

get
GET /project/peer/$project_id  

####  2.2 task
create
POST /task/peer/$task_inter_id  
```json
{
    "token": xx,
    "version": xx,
    "task_root": xx  # bool
}
```  

get
GET /task/peer/$task_inter_id  

####  2.3 instance
create 
POST /task_instance/peer/$task_instance_id
```json
{
    "task_peer_id": xx
}
```

update
PUT /task_instance/peer/$task_instance_id
```json
{
    "status": xx
}
```

get
GET /task_instance/peer/$task_instance_id

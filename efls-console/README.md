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

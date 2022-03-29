

# EFLS-console模块使用

## 使用方法
EFLS-console在部署时会生成host和peer两端，
`http://ingressIP/host，http://ingressIP/peer` ,如果ingress存在私网IP，可以用于部署完成后进行两者间进行样本求交与模型训练的测试

### 账号注册
填写用户名与密码，选择相应角色进行账号注册

### 项目创建
填写项目名（项目名与项目说明可任意填写）以及合作方的地址

### 任务创建
填写任务名以及相应参数([参数介绍](Parameter_introduction_CN.md))，创建任务，随后点击编辑，填写任务的token，己方任务与对方任务通过token进行配对，双方token填写完成后，一方点击配对即可配对成功

### 任务运行
配对成功后，任意一方点击运行即可调度双方的任务开始运行。

### 修改任务配置
如果任务配置需要修改，可以通过点击原任务的生成版本或者重建任务，进行配置修改

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



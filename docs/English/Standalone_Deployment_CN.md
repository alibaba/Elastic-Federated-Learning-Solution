# Standalone Deployment Guide

在单机模式部署中，用户可以构建镜像，通过docker文件夹挂载的方式，在本地进行样本数据求交与模型训练。
单机模式部署主要分为efls-data和efls-train两个模块

环境要求
- docker

## EFLS-data
### 镜像构建
```bash
cd ${EFLS}/efls-data
sudo docker build -t efls-data:v1 -f ./Dockerfile ./
```
### 镜像测试

构建镜像完成后，可以在镜像生成的容器内运行测试脚本测试本地数据求交的可行性。
本地测试将随机生成两份tfrecord数据，随后运行服务端与客户端。客户端采用grpc通信将向服务端传送数据，服务端返回求交的结果。

```bash
python /xfl/test/test_data_join.py
```
预期输出 "OK"

### 快速使用
用户可以自行生成样本求交数据或者修改容器内/efls-data/test/data_maker.py文件，生成数据。

我们提供了单机数据求交的运行脚本，位于容器内的/xfl/bin目录，相应参数可以参考[文档](Parameter_introduction_CN.md)

## EFLS-train

### 镜像构建

```bash
cd ${EFLS}
sudo docker build -f docker/Dockerfile.efls-train -t efls-train:v1 .
```

### 测试

构建镜像完成后，可以在镜像生成的容器内运行测试文件测试本地训练的可行性，测试文件在example目录下。
例如，进行mnist联邦训练，生成数据后，运行leader和follower两端进行训练。

```bash
docker run -it efls-train:v1 bash
cd /tmp/efl/python/efl/example/mnist
python generate_data.py
python leader.py --federal_role=leader &
python follower.py --federal_role=follower
```

### 快速使用
可以根据example进行修改，设计新的训练模型，也可以参考相应[文档](quick_start_efls_train_CN.md)


[English](README.md) | 简体中文

# Elastic-Federated-Learning-Solution
Elastic-Federated-Learning-Solution(简称EFLS)，是经过百亿规模工业级场景实战验证的跨互联网企业信息合作的联邦学习框架。EFLS有以下核心特性：云原生支持自定义特征工程——大规模高可用；首开水平聚合，层次聚合双模型——更强大更便捷。 EFLS会更加关注隐私保护和加密计算，并在此基础上建立APP孤岛的信息链接、构建机器学习模型，集成了隐私集合求交算法、差分隐私算法、大规模稀疏机器学习算法以及可视化流程控制台等，助力大家在搜推广的超大规模稀疏场景下进行联邦学习的合作应用与实践

## Installation

### Git Clone

EFLS依赖一些三方库，需要递归clone相应三方库。由于网络不稳定等原因，建议clone完成后，进一步检验三方库是否下载完成。

```bash
git clone https://github.com/alibaba/Elastic-Federated-Learning-Solution.git --recursive

#进一步检验三方库是否下载完成
cd ${EFLS}/efls-train/third_party/grpc
git submodule init && git submodule update --recursive
```

EFLS提供了两种部署方式，单机部署和云原生部署，用户可以根据自身需要进行选择。

### Stand-alone Deployment

部署环境要求: docker

EFLS提供了单机部署方式，用户可以利用docker在单机模式下快速部署与测试EFLS。具体参见
[Standalone Deployment Guide](./docs/English/Standalone_Deployment_CN.md).

### Cloud Native Deployment

部署环境要求: docker, kubectl

EFLS提供了云原生的部署方式，支持在公网上进行大规模分布式联邦学习。具体参见
[Cloud native Deployment Guide](./docs/English/Cloud_native_Deployment_CN.md).

## Documentation

### Parameter introduction
我们提供了样本求交部分与模型训练部分的参数介绍，参见[文档](./docs/English/Parameter_introduction_CN.md)

### API Documentation
我们提供了模型训练部分中[dataio](./docs/efls-train/data_api.md)、[Communicator](./docs/efls-train/comm_api.md)和[model](./docs/efls-train/model_api.md)对应的API文档。

### forward encryption Introduction
我们提供了模型训练部分中前向加密算法的介绍以及使用方法，参见[文档](./docs/efls-train/forward_encrypt.md)

### Differential Privacy Introduction
我们提供了模型训练部分中差分隐私的介绍以及使用方法，参见[文档](./docs/efls-train/differential_privacy.md)

## Algorithm Documentation
我们提出基于水平聚合的特征融合方法和基于层次聚合的特征融合方法，参见[文档](./docs/efls-algo/algos.md)

用户可以根据自己的需求设计训练算法，进行联邦学习训练。
English | [简体中文](README_CN.md)

# Elastic-Federated-Learning-Solution

Elastic-Federated-Learning-Solution(EFLS) is a federal learning framework for cross Internet enterprise information cooperation, which has been verified in 10 billion scale industrial scenarios. 
 EFLS has the following core features: large-scale, highly available cloud native architecture; more powerful and convenient horizontal aggregation and hierarchical aggregation algorithm models.

EFLS pay more attention on privacy protection and encrypted computing. On this basis, EFLS establish the information link of APP island, build the machine learning model, and integrate the privacy collection intersection algorithm, differential privacy algorithm, large-scale sparse machine learning algorithm and visual process console, so as to help everyone carry out the cooperative application and practice of federated learning in the super large-scale sparse scenario in the field of search、recommendation and advertising algorithm.

## Installation

### Git Clone

EFLS needs to recursively clone the corresponding third-party libraries. Due to network instability and other reasons, it is recommended that when clone is complete, further check if the third-party library is downloaded.

```bash
git clone https://github.com/alibaba/Elastic-Federated-Learning-Solution.git --recursive

#Further check if the third-party library is downloaded
cd ${EFLS}
git submodule init && git submodule update --recursive
cd ${EFLS}/efls-train/third_party/grpc
git submodule init && git submodule update --recursive
```

EFLS provides two deployment modes, stand-alone deployment and cloud native deployment. Users can choose according to their own needs.


### Stand-alone Deployment

Environment requirements: docker

EFLS provides stand-alone deployment mode. Users can quickly deploy and test EFLS in stand-alone mode by using docker. Please refer to 
[Standalone Deployment Guide](./docs/English/Standalone_Deployment.md) for more information.

### Cloud Native Deployment

Environment requirements: docker, kubectl

EFLS provides cloud native deployment and supports large-scale distributed federated learning on the public network. Please refer to 
[Cloud native Deployment Guide](./docs/English/Cloud_native_Deployment.md) for more information.

## Documentation

### Parameter introduction
We provide an introduction to the parameters of the EFLS-data and EFLS-train part. Please refer to [documentation](./docs/English/Parameter_introduction_CN.md)

### API Documentation
We provide documentation for [dataio](./docs/efls-train/data_api.md), [communicator](./docs/efls-train/comm_api.md) and [model](./docs/efls-train/model_api.md) in EFLS-train section.

### Forward Encryption Introduction
We provide the introduction and usage of forward encryption algorithm in EFLS-train section. Please refer to [documentation](./docs/efls-train/forward_encrypt.md)

### Differential Privacy Introduction
We provide the introduction and usage of differential privacy algorithm in EFLS-train section. Please refer to [documentation](./docs/efls-train/differential_privacy.md)

## Algorithm Documentation
We propose a feature fusion method based on horizontal aggregation and a feature fusion method based on hierarchical aggregation. Please refer to [documentation](./docs/efls-algo/algos.md)

Users can design training algorithms according to their own needs for federated learning training.
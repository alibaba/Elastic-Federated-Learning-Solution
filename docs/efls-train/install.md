# 源码安装
## 安装依赖
EFLS训练部分目前仅支持Python3和TensorFlow 1.15

- 更新软件源缓存，并安装编译依赖
```bash
apt-get update && apt-get install golang cmake git libmpc-dev libgmp3-dev -y
```

- 安装tensorflow以及python相关依赖
```bash
pip install tensorflow==1.15.5 gmpy2 tensorflow_privacy==0.3.0
```
## 编译安装
```bash
cd ${EFLS}/efls-train
mkdir build && cd build
cmake ../
make
pip install efl*.whl
```
# Dockerfile构建
```bash
cd ${EFLS}
sudo docker build -f docker/Dockerfile.efls-train -t efls-train:v1 .
```
# 集群部署

- 生成ingress grpc通信的密钥对，并为k8s集群创建secret密钥（gen_crt.sh 默认域名`alifl.alibaba-inc.com`）
```bash
cd ${EFLS}/efls-train
bash tools/cert/gen_crt.sh
```

- 生成pull docker的登陆密钥，用于k8s集群免密拉取镜像（使用私有镜像仓库时使用）
```bash
kubectl create secret docker-secret regcred \
  --docker-server=<你的镜像仓库名> \
  --docker-username=<你的用户名> \
  --docker-password=<你的密码> \
  --docker-email=<你的邮箱地址>
```

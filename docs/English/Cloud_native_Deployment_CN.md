# Cloud native Deployment Guide
云原生部署依赖于公有云环境，可以根据自身需求选择相应的云服务商。

环境要求: docker,[kubectl](https://kubernetes.io/docs/tasks/tools/)

## 云环境部署
部署手册中采用nas作为文件存储的示例。根据选择的云服务商文档，部署kubernetes集群(Kubernetes >= 1.9)，同时需要部署以下组件:
- nginx-ingress (提供负载均衡)
- nas pv,nas pvc (用于数据挂载)
- zookeeper (模型训练部分的微服务引擎MSE，将在webconsole中使用)

创建nas文件系统后可以参考/efls_data/deploy/quickstart/nas.yaml部署nas的pv和pvc。

随后将kubernetes集群的 .kube/config 文件复制到本地。使用`kubectl auth can-i <list|create|edit|delete> pods`命令验证kubctl集群连通性和权限。

## EFLS-data部署

EFLS-data 分为服务端与客户端。客户端将通过gRPC通信将求交的key发送给服务端，服务端返回每个key是否求交成功。
服务端将生成gRPC通信的密钥对，并将相应公钥提供给客户端。客户端通过服务端提供的公钥与服务端建立grpc连接。

### 密钥配置

#### 服务端
生成ingress gRPC通信的密钥对（密钥对默认储存在efls_data/deploy/quickstart下，注意构建镜像时将私钥tls.key保存在其他位置），并将相应公钥tls.crt提供给客户端，随后进行构建镜像。域名可以根据自身需求进行更改，但需要注意使用虚假的域名进行grpc请求时可能被云服务商拦截。
```bash
cd ${EFLS}/efls_data 
DOMAIN_NAME="www.alibaba.com"
openssl req -x509 -sha256 -nodes -days 365 -newkey rsa:2048 -keyout ./deploy/quickstart/tls.key -out ./deploy/quickstart/tls.crt -subj "/CN=${DOMAIN_NAME}/O=${DOMAIN_NAME}"
kubectl create secret tls tls-secret --key ./deploy/quickstart/tls.key --cert ./deploy/quickstart/tls.crt
```

#### 客户端
接收服务端提供的公钥，默认存储在efls_data/deploy/quickstart下，随后进行镜像构建。（也可以选择将公钥放置在nas挂载的文件夹中，此时需要在运行时修改tls.crt对应位置）

### 镜像构建

根据需要以及k8s ECS资源设置efls_data/deploy/quickstart/flink_pod_template.yaml的参数

```bash
sudo docker build -t efls-data:v1 -f ./Dockerfile ./
```

### flink集群部署
EFLS-data 基于flink on k8s 实现分布式样本数据求交
```bash
#使用如下命令设置Flink-k8s的所需RBAC
kubectl create clusterrolebinding flink-role-binding-default --clusterrole=edit --serviceaccount=default:default
```

输入输出使用云上存储，需要依赖k8s的[PV功能](https://kubernetes.io/docs/concepts/storage/persistent-volumes/) 。前置步骤：

1. 按实际情况建立k8s上PV和PVC资源。（如上文中建立的nas与nas-pvc）
2. 使用pod-template启动flink集群，-Dkubernetes.pod-template-file=/path_to/flink_pod_template.yaml。flink_pod_template.yaml默认在镜像中/xfl/deploy/quickstart下。

启动flink集群命令参考：
```bash
sudo docker run -v ${HOME}/.kube/:/root/.kube ${YOUR_DOCKER_NAME} /opt/flink/bin/kubernetes-session.sh -Dkubernetes.cluster-id=my-first-flink-cluster -Dkubernetes.container.image=${YOUR_DOCKER_NAME} -Dkubernetes.pod-template-file=/xfl/deploy/quickstart/flink_pod_template.yaml
```

### flink集群测试
```bash
#运行测试任务，终端输出word count结果即为flink部署成功
CMD="docker run -v ${HOME}/.kube/:/root/.kube ${YOUR_DOCKER_NAME} /opt/flink/bin/flink run --target kubernetes-session -Dkubernetes.cluster-id=my-first-flink-cluster"
$CMD /opt/flink/examples/batch/WordCount.jar
```

随后，根据需要以及k8s ECS资源设置flink集群的jobmanager.memory.process.size、taskmanager.memory.process.size等参数，参照命令`kubectl edit configmap flink-config-my-first-flink-cluster`，修改configmap后需要重新生成flink集群pod使其生效，参照命令`kubectl delete pods XXXXXX`

### ingress部署
我们提供了flink任务运行时的进行请求转发的nginx-ingress，以及用于测试网络连通性的grpc_test，ingress中域名需与上文保持一致。

```bash
cd ${EFLS}/efls_data
kubectl apply -f ./deploy/quickstart/grpc_server.yaml
kubectl apply -f ./deploy/quickstart/efls_ingress.yaml
```

可以通过以下命令，在公网环境测试grpc的连通性, 注意, network文件夹下需要有tls.crt文件用于grpc认证。

```bash
python ./deploy/network/grpc_ingress_test.py -i ip -p port -n www.ailibaba.com
```

### 注意事项
在云环境中暴露公网IP不安全，可能被黑客利用进行挖矿等攻击，建议对flink web设置访问控制。

### 样本求交测试

### 快速使用
参考相应[文档](quick_start_efls_data_CN.md)


## EFLS-train部署

### 镜像构建

```bash
cd ${EFLS}
sudo docker build -f docker/Dockerfile.efls-train -t efls-train:v1 .
```

### 镜像测试

构建镜像完成后，可以在镜像生成的容器内运行测试文件测试本地训练的可行性，测试文件在example目录下。

例如，进行mnist联邦训练，生成数据后，运行leader和follower两端进行训练。

```bash
docker run -it efls-train:v1 bash
cd /tmp/efl/python/efl/example/mnist
python generate_data.py
python leader.py --federal_role=leader &
python follower.py --federal_role=follower
```

### grpc密钥生成
生成ingress gRPC通信的密钥对，并为k8s集群创建secret密钥（gen_crt.sh 默认域名alifl.alibaba-inc.com）。模型训练时需要将各自的tls.crt提供给对方，用于grpc通信时验证。
```bash
cd ${EFLS}/efls-train 
bash tools/cert/gen_crt.sh
```

### 快速使用
参考相应[文档](quick_start_efls_train_CN.md)

## EFLS-console部署

### 镜像构建
在efls-console目录下构建镜像，需要修改镜像名为对应镜像名，随后将镜像提交到远程仓库中
```bash
cd ${EFLS}/efls-console
sudo docker build --build-arg ENV_ARG=aliyun_host --build-arg STATIC_ARG=host --build-arg EXPOSE_ARG=5000 -t XXXXXX/host:XXX .
sudo docker build --build-arg ENV_ARG=aliyun_peer --build-arg STATIC_ARG=peer --build-arg EXPOSE_ARG=5001 -t XXXXXX/peer:XXX .

docker push XXXXXX/host:XXX
docker push XXXXXX/peer:XXX
```

### 部署流程
1. 修改对应参数后，部署 host 和 peer 服务，先部署 host，其中包含了双方共用的 minio 服务拉起。  
   注意修改 `console-host.yaml` 中 l83 中的 nodeName（云服务中k8s集群的节点名称），l203 中的服务 url（注意使用公网可以访问的地址，可以采用 Ingress 的公网地址）；  
   注意修改 `console-peer.yaml` 中 l95 中的服务 url（注意使用公网可以访问的地址，可以采用 Ingress 的公网地址）；  
   注意修改 两个yaml文件中镜像名，与远程仓库的镜像名相对应；
   
2. ingress部署，运行 `kubectl apply -f /efls-console/manifests/alifl-console-host-ing.yaml`生成相应ingress

3. 数据库初始化

命令行中填入双边的公网访问地址，初始化数据库
```bash
curl --request POST 'http://xxx/host/db'
curl --request POST 'http://xxx/peer/db'
```

### 快速使用
参考相应[文档](quick_start_efls_console_CN.md)

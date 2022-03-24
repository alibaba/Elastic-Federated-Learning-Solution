# Cloud native Deployment Guide
Cloud native deployment depends on the public cloud environment. You can select the corresponding cloud service provider according to your own needs.

Environment: docker, [kubectl](https://kubernetes.io/docs/tasks/tools/)

## Cloud environment deployment

NAS is used as an example of file storage file storage in the deployment manual. 
According to the selected cloud service provider document, deploy the kubernetes(Kubernetes >= 1.9) cluster with the following components:
- nginx-ingress (to provide load balance)
- nas pv,nas pvc (For data mounting)
- zookeeper (used in EFLS-train in webconsole)

After creating the nas file system, you can refer to /efls_data/deploy/quickstart/nas.yaml to deploy nas pv and nas pvc.

Then copy .kube/config to local. Use the command `kubectl auth can-i <list|create|edit|delete> pods` to verify kubctl cluster connectivity and permissions.

## EFLS-data deployment

EFLS data is divided into server and client. The client will send the data key to the server through grpc communication, and the server will return whether each key is in the intersection.

The server will generate the key pair of grpc communication and provide the corresponding public key tls.crt to the client. The client establishes grpc connection with the server through the public key tls.crt.

### Key generation

#### server

Generate the key pair for ingress grpc communication (the key pair is stored in efls_data/deploy/quickstart by default), and provide the corresponding public key tls.crt to the client, and then build the image. Domain names can be changed according to your own needs, but it should be noted that grpc requests using fake domain names may be intercepted by cloud service providers.

```bash
cd ${EFLS}/efls_data
DOMAIN_NAME="www.alibaba.com"
openssl req -x509 -sha256 -nodes -days 365 -newkey rsa:2048 -keyout ./deploy/quickstart/tls.key -out ./deploy/quickstart/tls.crt -subj "/CN=${DOMAIN_NAME}/O=${DOMAIN_NAME}"
kubectl create secret tls tls-secret --key ./deploy/quickstart/tls.key --cert ./deploy/quickstart/tls.crt
```

#### client
The public key provided by the receiving server is stored in efls_data/deploy/quickstart by default, and then build the image. (you can also choose to place the public key in the NAS mounted folder. At this time, you need to modify the corresponding location of tls.crt at runtime)

#### docker image build
Set parameters of ${EFLS}/deploy/quickstart/flink_pod_template.yaml as needed and k8s ECS resources

```bash
sudo docker build -t efls-data:v1 -f ./Dockerfile ./
```

### flink cluster deployment

```bash
#set the desired RBAC for flink-k8s
kubectl create clusterrolebinding flink-role-binding-default --clusterrole=edit --serviceaccount=default:default
```

It is depended on [persistent-volumes](https://kubernetes.io/docs/concepts/storage/persistent-volumes/) of k8s to use cloud storage for input and output.Requirements：

1. pv and pvc resources（As mentioned above nas and nas-pvc）
2. Start the Flink cluster using pod template, -Dkubernetes.pod-template-file=/path_to/flink_pod_template.yaml.
The default path for flink_pod_template.yaml in container is /xfl/deploy/quickstart.

Start Flink cluster command reference：

```bash
sudo docker run -v ${HOME}/.kube/:/root/.kube ${YOUR_DOCKER_NAME} /opt/flink/bin/kubernetes-session.sh -Dkubernetes.cluster-id=my-first-flink-cluster -Dkubernetes.container.image=${YOUR_DOCKER_NAME} -Dkubernetes.pod-template-file=/xfl/deploy/quickstart/flink_pod_template.yaml
```

### Flink cluster test

```bash
#Run the test task, and the word count result output by the terminal indicates that the flick deployment is successful
CMD="docker run -v ${HOME}/.kube/:/root/.kube ${YOUR_DOCKER_NAME} /opt/flink/bin/flink run --target kubernetes-session -Dkubernetes.cluster-id=my-first-flink-cluster"
$CMD /opt/flink/examples/batch/WordCount.jar
```

Then, you may need to modify the parameters jobmanager.memory.process.size and taskmanager.memory.process.size of the Flink cluster. Refer to the command
`kubectl edit configmap flink-config-my-first-flink-cluster`
After modifying the configmap, you need to regenerate the flink cluster pod to make it effective. Refer to the command `kubectl delete pods XXXXXX`

### ingress deployment

We provide nginx ingress for grpc request forwarding , and grpc_test for testing network connectivity. The domain name in ingress should be consistent with the above.

```bash
cd ${EFLS}/efls_data
kubectl apply -f ./deploy/quickstart/grpc_server.yaml
kubectl apply -f ./deploy/quickstart/efls_ingress.yaml
```

You can test the connectivity of grpc in the public network environment through the following commands.

Note that tls.crt is required under the network folder for grpc authentication.

```bash
python ./deploy/network/grpc_ingress_test.py -i ip -p port -n www.ailibaba.com
```

### Attention

It is unsafe to expose public IP in cloud environment and may be attacked by hackers.
It is recommended to set access control for flink web.

### quick_start

Please refer to [documentation](quick_start_efls_data_CN.md)


## EFLS-train deployment

### docker image build

```bash
cd ${EFLS}
sudo docker build -f docker/Dockerfile.efls-train -t efls-train:v1 .
```

### docker image test

After constructing the image, you can run the test file in the container generated by the image to test the feasibility of local training. The test file is in the /example directory.

```bash
docker run -it efls-train:v1 bash
cd /tmp/efl/python/efl/example/mnist
python generate_data.py
python leader.py --federal_role=leader &
python follower.py --federal_role=follower
```

### Key generation

Generate the key pair of ingress grpc communication and create a secret for k8s cluster (the default domain name is alifl.alibaba-inc.com). Before model training, each tls.crt needs to be provided to the other party for verification during grpc communication.

```bash
cd ${EFLS}/efls-train 
bash tools/cert/gen_crt.sh
```

### quick_start

Please refer to [documentation](quick_start_efls_train_CN.md)

## EFLS-console deployment

### docker image build

```bash
cd ${EFLS}/efls-console
sudo docker build --build-arg ENV_ARG=aliyun_host --build-arg STATIC_ARG=host --build-arg EXPOSE_ARG=5000 -t XXXXXX/host:XXX .
sudo docker build --build-arg ENV_ARG=aliyun_peer --build-arg STATIC_ARG=peer --build-arg EXPOSE_ARG=5001 -t XXXXXX/peer:XXX .

docker push XXXXXX/host:XXX
docker push XXXXXX/peer:XXX
```

### console deployment

- After modifying the corresponding parameters, deploy the host and peer services. First deploy the host, which includes the Minio services shared by both sides.
  
  - Note to modify the nodeName (node name of k8s cluster in cloud service) in l83 and the service URL in l203 in `console-host.yaml` (It is recommended to use the public IP of ingress);
   
  - Note to modify the service URL in l95 in `console-peer.yaml`;
   
  - Note to modify the image name in the two yaml files, corresponding to the image name.

```bash
kubectl apply -f /manifests/console-host.yaml
kubectl apply -f /manifests/console-peer.yaml
```

- ingress deployment

```bash
kubectl apply -f /manifests/alifl-console-host-ing.yaml
```

- database initialization

```bash
curl --request POST 'http://xxx/host/db'
curl --request POST 'http://xxx/peer/db'
```

### quick_start

Please refer to [documentation](quick_start_efls_console_CN.md)



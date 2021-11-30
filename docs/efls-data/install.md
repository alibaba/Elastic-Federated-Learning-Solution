# K8S环境准备
阿里联邦学习依赖k8s基础环境及flink-k8s，可参考[文档](https://kubernetes.io/docs/setup/) 创建k8s集群。推荐使用[阿里云k8s服务](https://www.aliyun.com/product/kubernetes) 。
需要安装kubectl工具。参考[文档](https://kubernetes.io/docs/tasks/tools/)
K8S环境要求：

- Kubernetes >= 1.9. 使用kubectl version查看
- 验证kubctl集群连通性和权限。使用`kubectl auth can-i <list|create|edit|delete> pods`命令查看
- 开启k8s集群上的DNS服务。参照[文档](https://kubernetes.io/docs/tasks/administer-cluster/dns-debugging-resolution/) 调试和验证DNS服务有效性。
- 使用如下命令设置Flink-k8s的所需RBAC
```bash
kubectl create clusterrolebinding flink-role-binding-default --clusterrole=edit --serviceaccount=default:default
```
建议先参照[flink文档](https://ci.apache.org/projects/flink/flink-docs-release-1.13/docs/deployment/resource-providers/native_kubernetes/) ， 在k8s集群上部署一个flink-cluster并跑通测试任务。

# 镜像准备
我们提供了Dockerfile 和 build.sh脚本，用于环境构建。
环境要求
- kubectl工具，参考[文档](https://kubernetes.io/docs/tasks/tools/) 
- grpc_tools (pip install grpcio-tools)
- Maven 下载[链接](https://dlcdn.apache.org/maven/maven-3/3.8.2/binaries/apache-maven-3.8.2-bin.tar.gz) 

在构建镜像的过程前，可以通过export设置环境变量来指定镜像生成的名字。

```bash
export YOUR_DOCKER_NAME= XXXXXX:XXXX
bash build.sh
```

构建镜像完成后，可以在镜像生成的容器内运行测试文件测试本地数据求交的可行性，默认采用psi加密的数据求交。

```bash
python deploy/test/data_join_results_test.py
```

# 数据处理模块安装


## 1. 安装及验证流程
如果只做数据求交中的client方，只需按照Part A进行安装和验证；如果需要做server，则还需增加Part B中的步骤。

---

### Part A（仅做client）:
```shell
#1.下载xfl代码，假设在./xfl路径下
cd xfl/

#2. 构造docker镜像
docker build . -t ${YOUR_DOCKER_NAME}

#3. push docker镜像到私有仓库
docker push ${YOUR_DOCKER_NAME}

#3. 启动flink集群
docker run -v ${HOME}/.kube/:/root/.kube ${YOUR_DOCKER_NAME} /opt/flink/bin/kubernetes-session.sh -Dkubernetes.cluster-id=my-first-flink-cluster -Dkubernetes.container.image=${YOUR_DOCKER_NAME}

#3. 查看dashboard链接：
kubectl get svc |grep my-first-flink-cluster
#使用 my-first-flink-cluster-rest 这个service的ip和端口即可查看dashboard


#4. 运行测试任务，终端输出word count结果即为flink部署成功
CMD="docker run -v ${HOME}/.kube/:/root/.kube ${YOUR_DOCKER_NAME} /opt/flink/bin/flink run --target kubernetes-session -Dkubernetes.cluster-id=my-first-flink-cluster"
$CMD /opt/flink/examples/batch/WordCount.jar

#5. 测试数据io，该脚本会读取-i路径下所有tf-record文件，全部输出至-o路径下。
# $INPUT_DIR为输入目录 例如 "hdfs://my_data_dir/"，输入目录下包含若干tensorflow record文件, 每条record内应该有example_id列（也可通过hash_col_name和sort_col_name参数自定义为其他列名）
# 该命令为阻塞命令，运行完毕后检查OUTPUT_DIR path下输出结果。
$CMD --python /xfl/xfl/data/main/run_data_io.py -i ${INPUT_DIR} -o ${OUTPUT_DIR} --jars="file:///xfl/lib/xfl-java.jar" --hash_col_name="example_id" --sort_col_name="example_id"
```

### Part B（需要做server）：

- 参照[文档](https://kubernetes.github.io/ingress-nginx/) 部署ingress-nginx。

# 本地客户端版本
我们提供了一个本地客户端版本，用于环境部署完成之后，在其他机器通过公网访问与服务端进行数据求交测试，或者客户端数据量不大的情况。
本地客户端版本不依赖flink，同时可以根据需要选择是否依赖tensorflow的版本。
(tensorflow版本采用tf.io进行文件操作，非tensorflow版本采用os进行文件操作)

###部署方式
不需要构建docker镜像，clone代码后，安装requirements。

```bash
pip install -r requirements_local_client_tf.txt
or
pip install -r requirements_local_client_notf.txt
```

通过proto构建需要的_pb2.py文件

```bash
python3 -m grpc_tools.protoc -I . --python_out=. ./xfl/data/tfreecord/tfrecords.proto
python3 -m grpc_tools.protoc -I . --python_out=. --grpc_python_out=. ./proto/*.proto
```

修改/bin/k8s/run_data_join_cli_local.sh 中参数，使其保持与服务端一致,随后进行数据求交：

```bash
bash /bin/k8s/run_data_join_cli_local.sh
```


# EFL-data模块使用

EFL-data模块负责联邦学习各方之间安全高效的完成数据求交。data join 任务分为client端和server端。
本章介绍使用命令行提交datajoin任务。使用web页面提交数据任务请参考webUI使用文档。

### 作为client启动
一个例子：
```shell
CMD="docker run -v ${HOME}/.kube/:/root/.kube ${YOUR_DOCKER_NAME} /opt/flink/bin/flink run --target kubernetes-session -Dkubernetes.cluster-id=my-first-flink-cluster -Dkubernetes.cluster-id=my-first-flink-cluster"

# 运行如下命令可以启动一个data join的client方任务。
# client任务启动后会等待对方相同job_name的server任务启动，否则会一直阻塞直至超时
$CMD --python /xfl/xfl/data/main/run_data_join.py -i ${INPUT_DIR} -o ${OUTPUT_DIR} --job_name=test-data-join --bucket_num=1 --hash_col_name="example_id" --sort_col_name="example_id" --is_server=False --ingress_ip='39.106.55.247' --port=443 --host='alifl.com' --run_mode='k8s' --batch_size=2048 --file_part_size=65536 --wait_s=1800 --jars="file://${BASE_DIR}/lib/efls-flink-connectors-1.0-SNAPSHOT.jar"
```

---

### 作为server启动
一个例子：
```shell
CMD="docker run -v ${HOME}/.kube/:/root/.kube ${YOUR_DOCKER_NAME} /opt/flink/bin/flink run --target kubernetes-session -Dkubernetes.cluster-id=my-first-flink-cluster -Dkubernetes.cluster-id=my-first-flink-cluster"

# 运行如下命令可以启动一个data join的client方任务。
# client任务启动后会等待对方相同job_name的server任务启动，否则会一直阻塞直至超时
$CMD --python /xfl/xfl/data/main/run_data_join.py -i ${INPUT_DIR} -o  ${OUTPUT_DIR} --job_name=test-data-join --bucket_num=1 --hash_col_name="example_id" --sort_col_name="example_id" --is_server=True --run_mode='k8s' --batch_size=2048 --file_part_size=65536 --wait_s=1800 --jars="file://${BASE_DIR}/lib/efls-flink-connectors-1.0-SNAPSHOT.jar"
```

---

### 2.3 任务参数说明



| 参数名 | 角色 (s->server, c->client) | 说明 |
| --- | --- | --- |
| input_path (-i) | s,c | 输入数据目录路径，求交程序会递归扫描该路径下除"_" 和 "." 开头的文件。 |
| output_path (-o) | s,c | 输出数据目录路径 |
| job_name | s,c | 任务名，用于与对方配对。必须符合URL编码要求。建议使用英文与'-'构造 |
| bucket_num | s,c | 样本分桶个数，配对的任务分桶数需一致。 |
| hash_col_name | s,c | 样本中用于分桶的列 |
| sort_col_name | s,c | 样本中用于桶内排序的列 |
| is_server | s,c | 是否是server任务 |
| ingress_ip | c | client任务填写对方server端的公网ip |
| port | c | client任务对方server端的公网端口 |
| host | c | client任务填写对方server端使用的host，目前默认为'alifl.com' |
| run_mode | s,c | 默认使用k8s模式 |
| batch_size | s,c | 求交任务一次发送的id个数，可以设置大一些以提高吞吐 |
| file_part_size | s,c | 输出文件中，单文件内包含的样本条数。两边需要一致，保证后续训练任务正常对齐。 |
| wait_s | s,c | 任务等待server任务的秒数，等待超时则自动失败 |
| use_psi | s,c | 是否使用psi加密求交，默认false，两边需要一致 |
| tls_path | c | client任务链接server使用的ca证书。使用样例中默认值即可。 |
| jars | s,c | 插件包，使用样例中默认值即可。 |

## 3. 文件系统
数据处理模块支持多种输入输出的文件系统。直接使用-i -o参数中的filesystem schema即可。例如本地文件使用"file://"开头，oss文件使用"oss://"开头。
### 3.1 本地文件
k8s运行环境中，本地文件本身是临时存储，一般需结合[PV](https://kubernetes.io/docs/concepts/storage/persistent-volumes/)使用。例如将某个nfs存储挂载到pod的/mnt/data上。则数据任务的-i -o参数填写"file:///mnt/data/xxx"后即可对接远程存储。
​

### 3.2 OSS存储
支持阿里云OSS存储的读取和写入。启动flink集群时，需要修改/opt/flink/conf/flink-conf.yaml，填入oss的
ak/aid/endpoint即可，参考[这里](https://ci.apache.org/projects/flink/flink-docs-release-1.13/docs/deployment/filesystems/oss/)。
​

### 3.3 云上存储
输入输出使用云上存储，需要依赖k8s的[PV](https://kubernetes.io/docs/concepts/storage/persistent-volumes/)功能。前置步骤：

- 1. 按实际情况建立k8s上PV和PVC资源。
- 2. 使用pod-template启动flink集群，-Dkubernetes.pod-template-file=/path_to/flink_pod_template.yaml，以下为参考



- 启动命令参考
```bash
docker run -v ${HOME}/.kube/:/root/.kube ${YOUR_DOCKER_NAME} /opt/flink/bin/kubernetes-session.sh -Dkubernetes.cluster-id=my-first-flink-cluster -Dkubernetes.container.image=${YOUR_DOCKER_NAME} -Dkubernetes.pod-template-file=/pathto/flink_pod_template.yaml
```

- flink_pod_template.yaml参考
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: taskmanager-pod-template
spec:
  containers:
  - name: flink-main-container
    resources:
      requests:
        ephemeral-storage: 2048Mi
      limits:
        ephemeral-storage: 2048Mi
    volumeMounts:
      - mountPath: /opt/flink/volumes/hostpath
        name: flink-volume-hostpath
      - mountPath: /opt/flink/artifacts
        name: flink-artifact
      - mountPath: /opt/flink/log
        name: flink-logs
      # 在定义挂在的文件路径，任务里文件路径使用"file:///data/..."即可。
      - mountPath: "/data"
        name: nas-pv-storage
  volumes:
    - name: flink-volume-hostpath
      hostPath:
        path: /tmp
        type: Directory
    - name: flink-artifact
      emptyDir: { }
    - name: flink-logs
      emptyDir: { }
    # 在这里填写挂载的pvc
    - name: nas-pv-storage
      persistentVolumeClaim:
        claimName: nas-pvc
```

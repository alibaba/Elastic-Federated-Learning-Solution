

# EFLS-data参数介绍

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
| host | c | client任务填写对方server端使用的host，目前默认为'www.alibaba.com' |
| run_mode | s,c | 默认使用k8s模式 |
| batch_size | s,c | 求交任务一次发送的id个数，可以设置大一些以提高吞吐 |
| file_part_size | s,c | 输出文件中，单文件内包含的样本条数。两边需要一致，保证后续训练任务正常对齐。 |
| wait_s | s,c | 任务等待server任务的秒数，等待超时则自动失败 |
| use_psi | s,c | 是否使用psi加密求交，默认false，两边需要一致 |
| tls_path | c | client任务链接server使用的ca证书。使用样例中默认值即可。 |
| jars | s,c | 插件包，使用样例中默认值即可。 |

# EFLS-train参数介绍
##启动任务前环境准备
1. 参考集群部署手册构建并上传docker镜像<YOUR_DOCKER_IMAGE>
2. 参考集群部署手册创建训练ingress通信密钥对，并将公钥trainer.crt放置到nas的目录中<YOUR_CERT_FILE_PATH>
3. 参考集群部署手册生成docker拉取认证sercret<YOUR_DOCKER_SECRET>
4. 阿里云上申请部署zookeeper <YOUR_ZK_ADDR>
5. 将数据放到nas目录中<YOUR_DATA_PATH>
6. 将代码放到nas目录中<YOUR_CODE_DIR>，对应训练脚本<YOUR_CODE_SCRIPT>

##新建训练任务
###leader侧
1. 点击创建任务
2. 填写任务名称，例如：train-demo
3. 选择任务类型：TRAIN
4. 填写内部配置

```yaml
{
  "cert_file_path": "<YOUR_CERT_FILE_PATH>",
  "docker_secret": "<YOUR_DOCKER_SECRET>",
  "ingress_cert_name": "efl-trainer",
  "appid": "efls-train-leader",
  "peer_appid": "efls-train-follower",
  "worker": {
    "core": 1,
    "memory": "500",
    "instance_num": 1
  },
  "ps": {
    "core": 1,
    "memory": "500",
    "instance_num": 1
  },
  "code_dir": "<YOUR_CODE_DIR>",
  "script": "<YOUR_CODE_SCRIPT>",
  "docker_image": "YOUR_DOCKER_IMAGE",
  "job_type": "federal",
  "federal_role": "leader",
  "zk_addr": "<YOUR_ZK_ADDR>",
  "peer_addr": "<INGRESS_IP:PORT>",
  "target_hostname": "<PEER_HOST_NAME>"
}
```

###follower侧
1. 点击创建任务
2. 填写任务名称，例如：train-demo
3. 选择任务类型：TRAIN
4. 填写内部配置

```yaml
{
  "cert_file_path": "<YOUR_CERT_FILE_PATH>",
  "docker_secret": "<YOUR_DOCKER_SECRET>",
  "ingress_cert_name": "efl-trainer",
  "appid": "efls-train-follower",
  "peer_appid": "efls-train-leader",
  "worker": {
    "core": 1,
    "memory": "500",
    "instance_num": 1
  },
  "ps": {
    "core": 1,
    "memory": "500",
    "instance_num": 1
  },
  "code_dir": "<YOUR_CODE_DIR>",
  "script": "<YOUR_CODE_SCRIPT>",
  "docker_image": "YOUR_DOCKER_IMAGE",
  "job_type": "federal",
  "federal_role": "follower",
  "zk_addr": "<YOUR_ZK_ADDR>",
  "peer_addr": "<INGRESS_IP:PORT>",
  "target_hostname": "<PEER_HOST_NAME>"
}
```

###参数解析
- cert_file_path：用于训练过程中ingress验证的密钥
- ingress_cert_name：训练过程中的ingress名字
- target_hostname：对方在创建ingress验证密钥时申请的域名
- docker_image：拉取的镜像名称
- docker_secret：docker镜像拉取密钥
- appid：任务名
- peer_appid：对方任务名（当两侧任务名相同时可不填）
- worker：worker相关配置
  - core：启动worker的cpu核数
  - memory：启动worker的内存（MB）
  - instance_num：启动worker个数
- ps：param server相关配置，与worker相同
- code_dir：训练代码路径
- script：训练代码启动脚本
- job_type：联邦任务使用 federal
- federal_role：联邦学习角色 leader/follower 可选
- zk_addr：用于训练时worker ps scheduler角色服务发现的zk地址
- peer_addr：对方的连接ip地址和端口号
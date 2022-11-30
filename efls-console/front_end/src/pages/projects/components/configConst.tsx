export const trainConfigTips = `{
  "appid": "当前任务appid",
  "peer_appid": "对方任务appid",
  "worker": {
    "core": "启动的worker cpu核数",
    "memory": "启动的worker 内存单位MB",
    "instance_num": "启动的worker个数"
  },
  "ps": {
    "core": "启动的worker cpu核数",
    "memory": "启动的worker 内存单位MB",
    "instance_num": "启动的worker个数"
  },
  "code_dir": "代码目录",
  "script": "代码脚本",
  "docker_image": "启动镜像",
  "job_type": "federal",
  "federal_role": "follower或leader",
  "zk_addr": "任务服务发现zk地址",
  "peer_addr": "配对ip"
}`;
export const trainDefault = `{
"cert_file_path": "<YOUR_CERT_FILE_PATH>",
"docker_secret": "<YOUR_DOCKER_SECRET>",
"ingress_cert_name": "efl-trainer",
"appid": "<APP_ID>",
"peer_appid": "<PEER_APPID>",
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
"federal_role": "<ROLE>",
"zk_addr": "<YOUR_ZK_ADDR>",
"peer_addr": "<INGRESS_IP:PORT>",
"target_hostname": "<PEER_HOST_NAME>"
}`;
export const sampleConfigTips = `{
  "docker_image": "docker 镜像，需要用户填写如:registry.cn-hangzhou.aliyuncs.com/efls/xfl:test_with_ossconfig",
  "docker_secret": "docker secret，用于k8s pod验证并拉去相应的docker 镜像，根据需要填写",
  "input_path": "输入文件路径，需要用户填写如:oss://efls/test/",
  "output_path": "输出文件路径，需要用户填写如:oss://efls/test_output_cli/",
  "hash_col_name": "分桶采用的key，数据将按该维度分桶后多线程处理",
  "sort_col_name": "数据排序采用的key，最终每个桶内的数据将按该维度排序",
  "job_name": "任务名称，双方需要一致",
  "flink_claster": "双方采用的flink集群名，需要用户约定并设置",
  "ingress_ip":"服务端的ip地址",
  "port":"服务端提供的连接端口",
  "host":"服务端的ingress需求的host",
  "tls_path": "ssh rsa密钥,用于服务端与客户端之间数据传输时加密，在镜像构建时默认生成在/xfl/deploy/quickstart/tls.crt目录",
  "run_mode": "k8s",    （运行模式，采用k8s运行）
  "is_server": "false",    （是否为服务端，对于客户端 选 false）
  "wait_s": "18000",    （项目启动后，等待对方连接的时间，默认为18000）
  "bucket_num": "8",    （分桶数量，也可以理解为并发数，默认为8）
  "batch_size": "10240",    （每次grpc交互时数据传输批大小，默认为10240）
  "file_part_size": "65536"    （输出文件中，每个文件包含的最大数据数量，默认为65536）
  }`;
export const sampleDefault = `{
  "k8s_config": "k8s config用于验证访问k8s集群，需要用户提供",
  "docker_image": "docker 镜像，需要用户填写如:registry.cn-hangzhou.aliyuncs.com/efls/xfl:test_with_ossconfig",
  "docker_secret": "docker secret，用于k8s pod验证并拉去相应的docker 镜像，根据需要填写",
  "input_path": "输入文件路径，需要用户填写如:oss://efls/test/",
  "output_path": "输出文件路径，需要用户填写如:oss://efls/test_output_cli/",
  "hash_col_name": "分桶采用的key，数据将按该维度分桶后多线程处理",
  "sort_col_name": "数据排序采用的key，最终每个桶内的数据将按该维度排序",
  "job_name": "任务名称，双方需要一致",
  "flink_claster": "双方采用的flink集群名，需要用户约定并设置",
  "ingress_ip":"服务端的ip地址",
  "port":"服务端提供的连接端口",
  "host":"服务端的ingress需求的host",
  "tls_path": "/xfl/deploy/quickstart/tls.crt", 
  "run_mode": "k8s",
  "is_server": "false",
  "wait_s": "18000",
  "bucket_num": "8",
  "batch_size": "10240",
  "file_part_size": "65536"
  }`;


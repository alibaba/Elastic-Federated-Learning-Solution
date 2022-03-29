

# EFL-data feature-inc模块使用

EFLS-data支持了本地特征增量join功能, 单方拥有主表和辅表，可以利用辅表更新主表的特征（增加不存在的列，覆盖存在的列）

### 示例任务参数说明

```bash
--job_name=feature-inc      #任务名称，同时间同集群内需要唯一
--input_dir=file:///data/xfl-test/local_join_primary/  #输入目录，会递归查找该路径下tfrecord文件，默认忽略以'.'和'_'开头的文件
--output_dir=file:///data/test/local_join_output/ #输入目录，输出的文件名和结构会与输入文件目录保持一致，以确保不会破坏求交关系。
--worker_num=5 #task逻辑拆分粒度。越大task拆分越细。实际处理并发数由.spec.parallelism决定。建议设置为worker_num==.spec.parallelism
--left_key=key # 一组(left_key, right_key, aux_table) 确定一个join关系，多张辅表依次向后添加即可。 left_key为这个join关系中主表的key列名，right_key为辅表key列名，aux_table为辅表目录，会递归查找该路径下tfrecord文件，默认忽略以'.'和'_'开头的文件。
--right_key=aux1_key
--aux_table=file:///data/xfl-test/local_join_aux1
--left_key=key
--right_key=aux2_key
--aux_table=file:///data/xfl-test/local_join_aux2
```

### Join行为说明
不会自动清空输出文件目录，同名文件会覆盖，需要手动保证输出目录安全。

由于tfrecord是一种schemafree的数据结构（不会强制要求同一个文件内所有tfrecord message具备同样的schema），因此目前efls-data没有对schema做检查，具体join行为为protobuf的MergeFrom语义，会由主表tfrecord依次mergefrom辅表上查找到的tfrecord。

支持nas/oss, oss路径填写oss://${YOUR_BUCKET}?id=${YOUR_ID}&key=${YOUR_KEY}&host=${YOUR_HOST}/dir

### 启动命令参考
#### 常规模式
参照efls_data/bin/run_data_join_cli_local.sh

#### 采用redis工作队列
1: 通过apply k8s yaml部署redis, 参见efls_data/deploy/redis

2: 参照以下，提交k8s job
```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: feature-inc-job
spec:
  parallelism: 10
  backoffLimit: 1
  template:
    spec:
      restartPolicy: Never
      volumes:
        #nas 挂载，如果未部署nas，需要删除
        - name: nas-pv-storage
          persistentVolumeClaim:
            claimName: nas-pvc
      containers:
        - name: worker
          image: registry.cn-hangzhou.aliyuncs.com/fedlearn/xfl:feature-inc
          imagePullPolicy: Always
          command:
            - "python"
            - "-m"
            - "xfl.data.main.run_wq_local_join"
            - "--job_name=feature-inc-1106"
            - "--input_dir=oss://${YOUR_BUCKET}?id=${YOUR_ID}&key=${YOUR_KEY}&host=${YOUR_HOST}/dir"
            - "--output_dir=oss://${YOUR_BUCKET}?id=${YOUR_ID}&key=${YOUR_KEY}&host=${YOUR_HOST}/dir"
            - "--split_num=20"
            - "--left_key=example_id"
            - "--right_key=example_id"
            - "--aux_table=oss://${YOUR_BUCKET}?id=${YOUR_ID}&key=${YOUR_KEY}&host=${YOUR_HOST}/dir"
          volumeMounts:
          - mountPath: "/data"
            name: nas-pv-storage
      imagePullSecrets:
        - name: ali-docker-secret
```

#!/bin/bash

JOB_NAME='test-k8s-job'
BASE_DIR=$(cd "$(dirname "$0")/../../"; pwd)
INPUT_DIR="oss://efls/test/"
OUTPUT_DIR="oss://efls/test_output_cli/"
[ ! $STORE ] && STORE='memory'
[ ! $BUCKET_NUM ] && BUCKET_NUM=8

${FLINK_HOME}/bin/flink run --target kubernetes-session  -Dkubernetes.cluster-id=my-first-flink-cluster \
    --python ${BASE_DIR}/xfl/data/main/run_data_join.py \
    --input_path=${INPUT_DIR} \
    --output_path=${OUTPUT_DIR} \
    --job_name=${JOB_NAME} \
	--host='www.alibaba.com' \
    --port=443 \
    --ingress_ip='192.168.0.43' \
    --bucket_num=${BUCKET_NUM} \
    --run_mode='k8s' \
    --hash_col_name='example_id' \
    --sort_col_name='example_id' \
    --is_server=False \
    --sample_store_type=${STORE} \
    --batch_size=1024 \
    --file_part_size=65536 \
    --wait_s=1800 \
    --tls_path='/xfl/deploy/quickstart/tls.crt' \
    --jars="file://${BASE_DIR}/lib/efls-flink-connectors-1.0-SNAPSHOT.jar"


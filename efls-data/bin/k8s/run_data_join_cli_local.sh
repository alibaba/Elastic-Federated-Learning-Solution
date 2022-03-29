#!/bin/bash

JOB_NAME='test-k8s-job'
BASE_DIR=$(cd "$(dirname "$0")/../../"; pwd)
[ ! $INPUT_DIR ] && INPUT_DIR="/${BASE_DIR}/test_data"
[ ! $OUTPUT_DIR ] && OUTPUT_DIR="/tmp/output/${JOB_NAME}"
[ ! $STORE ] && STORE='memory'
[ ! $BUCKET_NUM ] && BUCKET_NUM=8

python -m xfl.data.main.run_data_join \
    --input_path=${INPUT_DIR} \
    --output_path=${OUTPUT_DIR} \
    --job_name=${JOB_NAME} \
    --host='www.alibaba.com' \
    --port=32443 \
    --ingress_ip='101.200.147.60' \
    --bucket_num=${BUCKET_NUM} \
    --run_mode='k8s' \
    --hash_col_name='example_id' \
    --sort_col_name='example_id' \
    --is_server=false \
    --sample_store_type=${STORE} \
    --batch_size=1024 \
    --file_part_size=65536 \
    --wait_s=1800 \
    --local_client='local_no_tf'\
    --tls_path='/xfl/deploy/quickstart/tls.crt' \
    --jars="file://${BASE_DIR}/lib/efls-flink-connectors-1.0-SNAPSHOT.jar"

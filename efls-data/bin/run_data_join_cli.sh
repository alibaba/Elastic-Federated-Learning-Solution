#!/bin/bash

JOB_NAME='TEST_DATA_JOIN_CLI'
BASE_DIR=$(cd "$(dirname "$0")/.."; pwd)
[ ! $INPUT_DIR ] && INPUT_DIR="file://${BASE_DIR}/test_data"
[ ! $OUTPUT_DIR ] && OUTPUT_DIR="file:///tmp/output/${JOB_NAME}"
[ ! $STORE ] && STORE='memory'
[ ! $BUCKET_NUM ] && BUCKET_NUM=8
USER='client'
python -m xfl.data.main.run_data_join \
    --input_path=${INPUT_DIR} \
    --output_path=${OUTPUT_DIR} \
    --job_name=${JOB_NAME} \
    --host='localhost' \
    --port=50051 \
    --bucket_num=${BUCKET_NUM} \
    --run_mode='local' \
    --hash_col_name='example_id' \
    --sort_col_name='event_time' \
    --is_server=false \
    --sample_store_type=${STORE} \
    --batch_size=1024 \
    --file_part_size=65536 \
    --wait_s=1800 \
    --jars="file://${BASE_DIR}/lib/efls-flink-connectors-1.0-SNAPSHOT.jar"

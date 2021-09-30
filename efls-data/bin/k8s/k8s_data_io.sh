#!/bin/bash

JOB_NAME='TEST_DATA_IO'
BASE_DIR=$(cd "$(dirname "$0")/../../"; pwd)
INPUT_DIR="oss://efls/test/"
OUTPUT_DIR="oss://efls/test_output/"
${FLINK_HOME}/bin/flink run --target kubernetes-session  -Dkubernetes.cluster-id=my-first-flink-cluster --python ${BASE_DIR}/xfl/data/main/run_data_io.py \
    --input_path=${INPUT_DIR} \
    --output_path=${OUTPUT_DIR} \
    --hash_col_name='example_id' \
    --sort_col_name='example_id' \
    --jars="file:///xfl/lib/efls-flink-connectors-1.0-SNAPSHOT.jar"

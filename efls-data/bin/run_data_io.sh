#!/bin/bash

JOB_NAME='TEST_DATA_IO'
BASE_DIR=$(cd "$(dirname "$0")/.."; pwd)
[ ! $INPUT_DIR ] && INPUT_DIR="file://${BASE_DIR}/test_data"
[ ! $OUTPUT_DIR ] && OUTPUT_DIR="file:///tmp/output/${JOB_NAME}"

python -m xfl.data.main.run_data_io \
    --input_path=${INPUT_DIR} \
    --output_path=${OUTPUT_DIR} \
    --hash_col_name='example_id' \
    --sort_col_name='example_id' \
    --jars="file://${BASE_DIR}/lib/efls-flink-connectors-1.0-SNAPSHOT.jar"
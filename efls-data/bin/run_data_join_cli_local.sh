#!/bin/bash

JOB_NAME='TEST_LOCAL_JOIN'
BASE_DIR=$(cd "$(dirname "$0")/.."; pwd)
[ ! $INPUT_DIR ] && INPUT_DIR="file:///data/xfl-test/local_join_primary/"
[ ! $OUTPUT_DIR ] && OUTPUT_DIR="file:///data/test/local_join_output"
python -m xfl.data.local_join.clean_job -n ${JOB_NAME}
python -m xfl.data.main.run_wq_local_join \
    --job_name=${JOB_NAME} \
    --input_dir=${INPUT_DIR} \
    --output_dir=${OUTPUT_DIR} \
    --split_num=1 \
    --left_key='key' \
    --right_key='aux1_key' \
    --aux_table='file:///data/xfl-test/local_join_aux1' \
    --left_key='key' \
    --right_key='aux2_key' \
    --aux_table='file:///data/xfl-test/local_join_aux2'

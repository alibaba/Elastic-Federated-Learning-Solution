#!/bin/bash

JOB_NAME='follower-data-join'
BASE_DIR=/xfl

function show_err_and_exit()
{
    echo "DataJoin ERROR: env INPUT_DIR and OUTPUT_DIR can't be None"
    exit 1
}

[ ! $INPUT_DIR ] && show_err_and_exit
[ ! $OUTPUT_DIR ] && show_err_and_exit
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
    --hash_col_name='sample_id' \
    --sort_col_name='sample_id' \
    --is_server=false \
    --sample_store_type=${STORE} \
    --batch_size=1024 \
    --file_part_size=65536 \
    --wait_s=1800 \
    --jars="file://${BASE_DIR}/lib/efls-flink-connectors-1.0-SNAPSHOT.jar"

LOCAL_OUTPUT_DIR=${OUTPUT_DIR:7}
TRAIN_DATA_DIR=$LOCAL_OUTPUT_DIR/train
TEST_DATA_DIR=$LOCAL_OUTPUT_DIR/test

mkdir -p $TRAIN_DATA_DIR
for ((i=0; i < $(($BUCKET_NUM-1)); i++))
do
  mv $LOCAL_OUTPUT_DIR/$i $TRAIN_DATA_DIR/$i
done

mkdir -p $TEST_DATA_DIR
mv $LOCAL_OUTPUT_DIR/$(($BUCKET_NUM-1)) $TEST_DATA_DIR/$(($BUCKET_NUM-1))

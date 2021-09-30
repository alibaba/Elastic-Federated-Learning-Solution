#!/bin/bash
set -eu

function help() {
    echo "Usage: $0 <source_data_path> <mode>"
    echo "  source_data_path: Criteo data path"
    echo "              mode: data-join or local"
}

if [ $# -lt 2 ]
then
    help
    exit 1
fi

SOURCE_DATA_PATH=$1
MODE=$2
ROOT_DIR=`pwd`
WORKSPACE="`pwd`/$(dirname $0)"

function data_join_task()
{
    # step1. prepare raw data
    python $WORKSPACE/data_join/generate_criteo_data_join.py -d $SOURCE_DATA_PATH -p 32 -o $ROOT_DIR/raw_data
    
    # step2. run data join leader task
    INPUT_DIR="file://$ROOT_DIR/raw_data/leader"   \
    OUTPUT_DIR="file://$ROOT_DIR/data_join/leader" \
    bash $WORKSPACE/data_join/run_data_join.sh &
    
    # step2. run data join follower task
    INPUT_DIR="file://$ROOT_DIR/raw_data/follower"   \
    OUTPUT_DIR="file://$ROOT_DIR/data_join/follower" \
    bash $WORKSPACE/data_join/run_data_join_cli.sh &

    wait
}

function local_task()
{
    python $WORKSPACE/local/generate_criteo_local.py -d $SOURCE_DATA_PATH -p 32 -o $ROOT_DIR/local_data
}

if [ $MODE == "data-join" ]
then
    data_join_task
elif [ $MODE == "local" ]
then
    local_task
else
    help
    exit 1
fi

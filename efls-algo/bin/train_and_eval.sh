#!/bin/bash
set -eu

function help()
{
    echo "Usage: $0 <data_dir> <data_dir_local> <data_mode> <model>"
    echo "data_dir: input data dir"
    echo "data_dir_local: input data dir"
    echo "data_mode: data-join or local"
    echo "model: hierarchical or level"
}

if [ $# -lt 3 ]
then
    help
    exit 1
fi

DATA_DIR=$1
DATA_DIR_LOCAL=$2
DATA_MODE=$3
MODEL=$4

function kill_old_task()
{
    old_tasks=`ps aux | egrep "(leader|follower)" | grep -v grep | awk '{print $2}'`
    if [ "X$old_tasks" != "X" ]; then
      echo "kill old tasks: $old_tasks"
      echo $old_tasks  | xargs kill -9
    fi
}

function run_fl_task()
{
    # step1. run fl leader
    python ./models/$MODEL/leader.py \
        --federal_role=leader        \
        --data_dir=$DATA_DIR         \
        --data_dir_local=$DATA_DIR_LOCAL         \
        --data_mode=$DATA_MODE       \
        --worker_num=1               \
        --task_name=worker           \
        --task_index=0               \
        >leader.log 2>&1 &
    sleep 5s

    # step2. run fl follower
    python ./models/$MODEL/follower.py \
        --federal_role=follower        \
        --data_dir=$DATA_DIR           \
        --data_dir_local=$DATA_DIR_LOCAL     \
        --data_mode=$DATA_MODE         \
        --worker_num=1                 \
        --task_name=worker             \
        --task_index=0                 \
        >follower.log 2>&1 &

    wait
}

kill_old_task
sleep 3s
run_fl_task

echo "train and eval run finish."

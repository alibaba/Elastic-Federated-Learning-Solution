LOG_PATH=/data/efl-logs/${APPID}/${TASK_NAME}_${TASK_INDEX}
if [ -d ${LOG_PATH} ];then
  rm -rf ${LOG_PATH}
fi
mkdir -p ${LOG_PATH}

cd ${CODE_DIR}
python ${JOB_SCRIPT} \
  -c "${TRAIN_CONFIG}" \
  --ckpt_dir "${MODEL_DIR}" \
  --app_id "${APPID}" \
  --ps_num "${PS_NUM}" \
  --worker_num "${WORKER_NUM}" \
  --federal_role "${FEDERAL_ROLE}" \
  --zk_addr "${ZK_ADDR}/${APPID}" \
  --task_name "${TASK_NAME}" \
  --task_index "${TASK_INDEX}" \
  --peer_addr "${PEER_ADDR}" \
  1> ${LOG_PATH}/stdout 2> ${LOG_PATH}/stderr

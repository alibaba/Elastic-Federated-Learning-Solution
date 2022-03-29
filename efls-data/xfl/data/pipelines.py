# Copyright 2021 Alibaba Group Holding Limited. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ==============================================================================

from pyflink.common.typeinfo import Types
from pyflink.common.watermark_strategy import WatermarkStrategy
from pyflink.common import Configuration
from pyflink.util.java_utils import get_j_env_configuration
from pyflink.datastream import StreamExecutionEnvironment
from pyflink.datastream.execution_mode import RuntimeExecutionMode

from xfl.common.common import RunMode
from xfl.common.logger import log
from xfl.data.connectors import input_sink, input_keyed_source
from xfl.data.functions import DefaultKeySelector, ClientSortJoinFunc, ServerSortJoinFunc, ServerPsiJoinFunc, \
  ClientPsiJoinFunc, ClientBatchJoinFunc

from xfl.data.ecdh_psi import ClientEcdhJoinFunc, ServerEcdhJoinFunc
from xfl.data.store.sample_kv_store import DictSampleKvStore
from xfl.data.store.flink_state_kv_store import FlinkStateKvStore
from xfl.data.store.etcd_kv_store import EtcdSampleKvStore
from xfl.data.store.level_db_kv_store import LevelDbKvStore

TYPE_BYTE_ARRAY = Types.PRIMITIVE_ARRAY(Types.BYTE())

SAMPLE_STORE_TYPE = {
  "memory": DictSampleKvStore,
  "state": FlinkStateKvStore,
  "etcd": EtcdSampleKvStore,
  "leveldb": LevelDbKvStore
}

def get_flink_batch_env(conf: dict = {}) -> StreamExecutionEnvironment:
  env = StreamExecutionEnvironment.get_execution_environment()
  env.set_runtime_mode(RuntimeExecutionMode.BATCH)
  config = Configuration(j_configuration=get_j_env_configuration(env._j_stream_execution_environment))
  config.set_integer("python.fn-execution.bundle.size", 10000)
  if 'jars' in conf:
    env.add_jars(*conf['jars'])
  return env

class data_join_pipeline(object):
  def __init__(self,
               input_path: str,
               output_path: str,
               job_name: str,
               host: str,
               port: int,
               ip: str,
               bucket_num: int,
               run_mode: str,
               hash_col_name: str,
               sort_col_name: str,
               is_server: bool,
               sample_store_type: str,
               batch_size: int,
               file_part_size: int,
               tls_crt_path: str,
               rsa_pub_path: str,
               rsa_pri_path: str,
               wait_s: int = 1800,
               use_psi: bool = False,
               psi_type: str = 'rsa',
               need_sort: bool = False,
               db_root_path: str = '/tmp',
               inputfile_type: str = 'tfrecord',
               loaddata_parallelism: int = 0,
               client2multiserver: int = 1,
               conf: dict = {}):
    self._job_name = job_name
    env = get_flink_batch_env(conf)
    self._loaddata_parallelism = loaddata_parallelism
    if self._loaddata_parallelism == 0:
      self._loaddata_parallelism = bucket_num
    env.set_max_parallelism(max(bucket_num, self._loaddata_parallelism))
    env.set_parallelism(bucket_num)
    ds = env.from_source(
      source=input_keyed_source(input_path, hash_col_name, sort_col_name, inputfile_type),
      watermark_strategy=WatermarkStrategy.for_monotonous_timestamps(),
      type_info=Types.TUPLE([TYPE_BYTE_ARRAY] * 3),
      source_name=job_name + "_tf_record_source_with_key").set_parallelism(self._loaddata_parallelism)

    log.info('=================Data join pipeline info================')
    log.info('job_name: %s'%job_name)
    log.info('is_server: %s'%is_server)
    log.info('bucket_num: %d'%bucket_num)
    log.info('host: %s'%host)
    log.info('ip: %s'%ip)
    log.info('port: %d'%port)
    log.info('use_psi: %s'%use_psi)
    log.info('need_sort: %s'%need_sort)
    log.info('psi_type: %s'%psi_type)
    log.info('sample_store_type: %s'%sample_store_type)
    log.info('db_root_path: %s'%db_root_path)
    log.info('client2multiserver num: %d'% client2multiserver)
    log.info('inputfile_type: %s'% inputfile_type)
    log.info('========================================================')
    tls_crt = b''
    if tls_crt_path is not None:
      with open(tls_crt_path, 'rb') as f:
        tls_crt = f.read()
        log.info("tls path:{} \n tls value:{}".format(tls_crt_path, tls_crt))
    rsa_pub = None
    if rsa_pub_path is not None:
      with open(rsa_pub_path, 'rb') as f:
        rsa_pub = f.read()
        log.info("rsa_pub path:{} \n rsa_pub value:{}".format(rsa_pub_path, rsa_pub))
    rsa_pri = None
    if rsa_pri_path is not None:
      with open(rsa_pri_path, 'rb') as f:
        rsa_pri = f.read()
        log.info("rsa_pri path:{} \n rsa_pri value:{}".format(rsa_pri_path, rsa_pri))
    output_type=Types.ROW([Types.STRING(), TYPE_BYTE_ARRAY])
    if inputfile_type == 'csv':
      output_type=Types.ROW([Types.STRING(), Types.STRING()])

    if is_server:
      if use_psi:
        if psi_type == 'rsa':
          server_func = ServerPsiJoinFunc
        elif psi_type == 'ecdh':
          server_func = ServerEcdhJoinFunc
        else:
          raise RuntimeError('Unsupported psi type %s'%psi_type)
      else:
        server_func = ServerSortJoinFunc
      ds = ds.key_by(DefaultKeySelector(bucket_num=bucket_num), key_type=Types.INT()) \
        .process(server_func(
        job_name=job_name,
        bucket_num=bucket_num,
        port=port,
        sample_store_cls=SAMPLE_STORE_TYPE[sample_store_type],
        wait_s=wait_s,
        run_mode=RunMode(run_mode),
        batch_size=batch_size,
        rsa_public_key_bytes=rsa_pub,
        rsa_private_key_bytes=rsa_pri,
        inputfile_type=inputfile_type,
        db_root_path=db_root_path),
        output_type=output_type) \
        .name(job_name + "_merge_sort_join_server")
    else:
      if use_psi:
        if psi_type == 'rsa':
          client_func = ClientPsiJoinFunc
        elif psi_type == 'ecdh':
          client_func = ClientEcdhJoinFunc
        else:
          raise RuntimeError('Unsupported psi_type %s'%psi_type)
      else:
        log.info("Client need sort: {}.".format(need_sort))
        if need_sort:
          client_func = ClientSortJoinFunc
        else:
          client_func = ClientBatchJoinFunc
      ds = ds.key_by(DefaultKeySelector(bucket_num=bucket_num, client2multiserver=client2multiserver), key_type=Types.INT()) \
        .process(client_func(
        job_name=job_name,
        peer_host=host,
        peer_ip=ip,
        peer_port=port,
        bucket_num=bucket_num,
        sample_store_cls=SAMPLE_STORE_TYPE[sample_store_type],
        batch_size=batch_size,
        run_mode=RunMode(run_mode),
        wait_s=wait_s,
        tls_crt=tls_crt,
        client2multiserver=client2multiserver,
        inputfile_type=inputfile_type,
        db_root_path=db_root_path),
        output_type=output_type) \
        .name(job_name + "_merge_sort_join_cli")

    ds.sink_to(input_sink(output_path, 0, 1, part_size=file_part_size, inputfile_type=inputfile_type))
    self._env = env

  def run(self):
    return self._env.execute(self._job_name)

  def get_execution_plan(self):
    return self._env.get_execution_plan()

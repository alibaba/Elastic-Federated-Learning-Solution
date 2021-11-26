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
from xfl.data.connectors import tf_record_sink, tf_record_keyed_source
from xfl.data.functions import DefaultKeySelector, ClientSortJoinFunc, ServerSortJoinFunc, ServerPsiJoinFunc, \
  ClientPsiJoinFunc, ClientBatchJoinFunc
from xfl.data.store.sample_kv_store import DictSampleKvStore
from xfl.data.store.flink_state_kv_store import FlinkStateKvStore
from xfl.data.store.etcd_kv_store import EtcdSampleKvStore

TYPE_BYTE_ARRAY = Types.PRIMITIVE_ARRAY(Types.BYTE())

SAMPLE_STORE_TYPE = {
  "memory": DictSampleKvStore,
  "state": FlinkStateKvStore,
  "etcd": EtcdSampleKvStore
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
               wait_s: int = 1800,
               use_psi: bool = False,
               need_sort: bool = False,
               conf: dict = {}):
    self._job_name = job_name
    env = get_flink_batch_env(conf)
    env.set_max_parallelism(bucket_num)
    env.set_parallelism(bucket_num)
    ds = env.from_source(
      source=tf_record_keyed_source(input_path, hash_col_name, sort_col_name),
      watermark_strategy=WatermarkStrategy.for_monotonous_timestamps(),
      type_info=Types.TUPLE([TYPE_BYTE_ARRAY] * 3),
      source_name=job_name + "_tf_record_source_with_key")

    tls_crt = b''
    if tls_crt_path is not None:
      with open(tls_crt_path, 'rb') as f:
        tls_crt = f.read()
        log.info("tls path:{} \n tls value:{}".format(tls_crt_path, tls_crt))
    if is_server:
      if use_psi:
        server_func = ServerPsiJoinFunc
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
        batch_size=batch_size),
        output_type=Types.ROW([Types.STRING(), TYPE_BYTE_ARRAY])) \
        .name(job_name + "_merge_sort_join_server")
    else:
      if use_psi:
        client_func = ClientPsiJoinFunc
      else:
        log.info("Client need sort: {}.".format(need_sort))
        if need_sort:
          client_func = ClientSortJoinFunc
        else:
          client_func = ClientBatchJoinFunc
      ds = ds.key_by(DefaultKeySelector(bucket_num=bucket_num), key_type=Types.INT()) \
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
        tls_crt=tls_crt),
        output_type=Types.ROW([Types.STRING(), TYPE_BYTE_ARRAY])) \
        .name(job_name + "_merge_sort_join_cli")

    ds.sink_to(tf_record_sink(output_path, 0, 1, part_size=file_part_size))
    self._env = env

  def run(self):
    return self._env.execute(self._job_name)

  def get_execution_plan(self):
    return self._env.get_execution_plan()

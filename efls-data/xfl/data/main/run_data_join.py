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
import argparse

from xfl.common.argutil import str_to_bool
from xfl.common.logger import log

if __name__ == '__main__':
  parser = argparse.ArgumentParser(description='data join job start command')
  parser.add_argument('-n', '--job_name', type=str,
                      help='job name', required=True)
  parser.add_argument('--is_server', type=str_to_bool,
                      const=True, nargs='?',
                      help="True if this job is data join server.")
  parser.add_argument('-i', '--input_path', type=str,
                      help='the input_path of data join, should be a dir, eg `file:///home/xxx` or `oss://bucket/file`',
                      required=True)
  parser.add_argument('-o', '--output_path', type=str,
                      help='the output_path of data join, should be a dir, eg `file:///home/xxx` or `oss://bucket/file`',
                      required=True)
  parser.add_argument('--hash_col_name', type=str,
                      help='name of record col which used for generating hash-bucket.')
  parser.add_argument('--sort_col_name', type=str,
                      help='name of record col which used for sorting.')
  parser.add_argument('--bucket_num', type=int,
                      help='bucket number for data join.')
  parser.add_argument('--sample_store_type', type=str, default='memory',
                      choices=['memory', 'state', 'etcd'],
                      help='the backend for sample store.')
  parser.add_argument('--host', type=str, default='localhost',
                      help='server host address, `localhost` for running mode local,'
                           '`service domain` for running mode k8s`')
  parser.add_argument('--port', type=int,
                      help='server port',
                      default=50051)
  parser.add_argument('--ingress_ip', type=str,
                      help='k8s ingress ip for client, only for k8s rum mode',
                      default=None)

  parser.add_argument('--batch_size', type=int,
                      help='the batch size of request ids for data joining',
                      default=2048)
  parser.add_argument('--file_part_size', type=int,
                      help='the number of row in each file of data join output',
                      default=1024)
  parser.add_argument('--job_plan_output_path', type=str,
                      help='write flink job plan json to this path.',
                      default=None)
  parser.add_argument('--jars', type=str,
                      help='jar paths used by flink job, seprated by `,`.',
                      default=None)
  parser.add_argument('--run_mode', type=str, default='local',
                      choices=['local', 'k8s'],
                      help='task running mode')
  parser.add_argument('--tls_path', type=str,
                      help='ca.cat file path for tls rpc connection',
                      default=None)

  parser.add_argument('--wait_s', type=int,
                      help='task waiting timeout time (second)',
                      default=1800)

  parser.add_argument('--use_psi', type=str_to_bool,
                      const=True, nargs='?',
                      help="True if this job use rsa-psi method.")

  parser.add_argument('--local_client', type=str, default='no',
                      choices=['local_no_tf', 'local', 'no'],
                      help='running client without pyflink')

  args = parser.parse_args()
  conf = {}
  if args.jars and len(args.jars) > 0:
    conf['jars'] = args.jars.split(',')
  if args.local_client == 'local_no_tf':
    from xfl.data.client_no_tf import data_join_pipeline_local_no_tf
    pipeline_func = data_join_pipeline_local_no_tf
  elif args.local_client == 'local':
    from xfl.data.client_local import data_join_pipeline_local
    pipeline_func = data_join_pipeline_local
  else:
    from xfl.data.pipelines import data_join_pipeline
    pipeline_func = data_join_pipeline
  pipeline = pipeline_func(
    input_path=args.input_path,
    output_path=args.output_path,
    job_name=args.job_name,
    host=args.host,
    port=args.port,
    ip=args.ingress_ip,
    bucket_num=args.bucket_num,
    run_mode=args.run_mode,
    hash_col_name=args.hash_col_name,
    sort_col_name=args.sort_col_name,
    is_server=args.is_server,
    sample_store_type=args.sample_store_type,
    batch_size=args.batch_size,
    file_part_size=args.file_part_size,
    tls_crt_path=args.tls_path,
    wait_s=args.wait_s,
    use_psi=args.use_psi,
    conf=conf)
  if args.job_plan_output_path:
    with open(args.job_plan_output_path, "w") as f:
      f.write(pipeline.get_execution_plan())
  log.info("Job {} begin to run... bucket num {}".format(args.job_name, args.bucket_num))
  log.info("input path:{}".format(args.input_path))
  log.info("output path:{}".format(args.output_path))
  res = pipeline.run()
  log.info("Job {} run finish..., res status:\n{}".format(args.job_name, str(res)))

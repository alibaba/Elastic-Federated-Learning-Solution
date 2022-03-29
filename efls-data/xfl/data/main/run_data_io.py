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

from pyflink.common import WatermarkStrategy
from pyflink.common.typeinfo import Types

from xfl.common.logger import log
from xfl.data.connectors import tf_record_keyed_source, tf_record_sink
from xfl.data.pipelines import get_flink_batch_env

TYPE_BYTE_ARRAY = Types.PRIMITIVE_ARRAY(Types.BYTE())
if __name__ == "__main__":
  parser = argparse.ArgumentParser(description='oss io test job start command')
  parser.add_argument('-i', '--input_path', type=str,
                      help='the input_path of data join, should be a dir, eg `file:///home/xxx` or `oss://bucket/file`',
                      required=True)
  parser.add_argument('-o', '--output_path', type=str,
                      help='the output_path of data join, should be a dir, eg `file:///home/xxx` or `oss://bucket/file`',
                      required=True)
  parser.add_argument('--jars', type=str,
                      help='jar paths used by flink job, seprated by `,`.',
                      default=None)
  parser.add_argument('--hash_col_name', type=str,
                      help='name of record col which used for generating hash-bucket.',
                      default='example_id')
  parser.add_argument('--sort_col_name', type=str,
                      help='name of record col which used for sorting.',
                      default='event_time')
  parser.add_argument('--inputfile_type', type=str, default='tfrecord',
                      choices=['tfrecord', 'csv'],
                      help='the type of input file.')

  args = parser.parse_args()
  conf = {}
  if args.jars and len(args.jars) > 0:
    conf['jars'] = args.jars.split(',')
  env = get_flink_batch_env(conf)
  ds = env.from_source(
    source=tf_record_keyed_source(args.input_path, args.hash_col_name, args.sort_col_name, args.inputfile_type),
    watermark_strategy=WatermarkStrategy.for_monotonous_timestamps(),
    type_info=Types.TUPLE([TYPE_BYTE_ARRAY] * 3),
    source_name="oss tf record io test")
  def helper(value):
    return '0', value[2]
  ds = ds.map(helper, output_type=Types.ROW([Types.STRING(), TYPE_BYTE_ARRAY]))
  ds.sink_to(tf_record_sink(args.output_path, 0, 1, part_size=65536))
  log.info("data io job input:{}".format(args.input_path))
  log.info("data io job output:{}".format(args.output_path))
  env.execute("data_io_test")
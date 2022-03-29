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

from pyflink.common.serialization import Encoder
from pyflink.datastream.connectors import FileSource, StreamFormat, FileSink, BucketAssigner, RollingPolicy
from pyflink.java_gateway import get_gateway


def tf_record_stream_format(read_buffer_size: int = 4096, crc_check: bool = True) -> 'StreamFormat':
  """
  Creates a reader format that read TFRecord from a file.
  @param read_buffer_size:  Buffer size for TFRecordInputStream.
  @param crc_check: True if there is CRC in tf_record files, otherwise false.
  @return: StreamFormat: type is 'TYPE_BYTE_ARRAY'
  """
  j_stream_format = get_gateway().jvm.com.alibaba.xfl.flink.connectors. \
    TfRecordStreamFormat(read_buffer_size, crc_check)
  return StreamFormat(j_stream_format)


def tf_record_keyed_stream_format(hash_col_name: str, sort_col_name: str,
                                  read_buffer_size: int = 4096, crc_check: bool = True) -> 'StreamFormat':
  """
  Creates a reader format that read TFRecord with key from a file.
  @param hash_col_name: the col name of hash key in record.
  @param sort_col_name: the col name of sort key in record.
  @param read_buffer_size:  Buffer size for TFRecordInputStream.
  @param crc_check: True if there is CRC in tf_record files, otherwise false.
  @return: StreamFormat: type is Types.TUPLE([TYPE_BYTE_ARRAY]*3)
  """
  j_stream_format = get_gateway().jvm.com.alibaba.xfl.flink.connectors. \
    TfRecordKeyedStreamFormat(read_buffer_size, crc_check, hash_col_name, sort_col_name)
  return StreamFormat(j_stream_format)

def csv_keyed_stream_format(hash_col_name: str, sort_col_name: str, read_buffer_size: int = 4096) -> 'StreamFormat':
  j_stream_format = get_gateway().jvm.com.alibaba.xfl.flink.connectors. \
    CsvKeyedStreamFormat(read_buffer_size, hash_col_name, sort_col_name)
  return StreamFormat(j_stream_format)


def tf_record_source(input_path: str):
  return FileSource.for_record_stream_format(tf_record_stream_format(), input_path) \
    .build()


def input_keyed_source(input_path: str, hash_col_name, sort_col_name, inputfile_type):
  if inputfile_type == 'csv':
    return FileSource.for_record_stream_format(csv_keyed_stream_format(hash_col_name, sort_col_name), input_path) \
      .build()
  else :
    return FileSource.for_record_stream_format(tf_record_keyed_stream_format(hash_col_name, sort_col_name), input_path) \
      .build()



def tf_record_bucket_assigner(bucket_col_idx: int) -> BucketAssigner:
  j_bucket_assigner = get_gateway().jvm.com.alibaba.xfl.flink.connectors. \
    TfRecordRowBucketAssigner(bucket_col_idx)
  return BucketAssigner(j_bucket_assigner)


def tf_record_sink_encoder(value_col_idx: int):
  j_encoder = get_gateway().jvm.com.alibaba.xfl.flink.connectors. \
    TfRecordEncoder(value_col_idx)
  return Encoder(j_encoder)

def csv_sink_encoder(value_col_idx: int):
  j_encoder = get_gateway().jvm.com.alibaba.xfl.flink.connectors. \
    CsvEncoder(value_col_idx)
  return Encoder(j_encoder)

def tf_record_file_sink_rolling_policy(row_number_per_file: int):
  JRowNumberRollingPolicy = get_gateway().jvm.com.alibaba.xfl.flink.connectors. \
    RowNumberRollingPolicy
  j_rolling_policy = JRowNumberRollingPolicy.builder().withRowNumber(row_number_per_file).build()
  return RollingPolicy(j_rolling_policy)


def input_sink(output_path: str, bucket_col_idx: int, value_col_idx: int, part_size=64, inputfile_type='tfrecord'):
  if inputfile_type == 'tfrecord':
    return FileSink.for_row_format(output_path, tf_record_sink_encoder(value_col_idx)) \
      .with_bucket_assigner(tf_record_bucket_assigner(bucket_col_idx)) \
      .with_rolling_policy(tf_record_file_sink_rolling_policy(part_size)) \
      .build()
  else:
   return FileSink.for_row_format(output_path, csv_sink_encoder(value_col_idx)) \
      .with_bucket_assigner(tf_record_bucket_assigner(bucket_col_idx)) \
      .with_rolling_policy(tf_record_file_sink_rolling_policy(part_size)) \
      .build()
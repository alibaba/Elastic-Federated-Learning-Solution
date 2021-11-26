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

from collections import OrderedDict

from xfl.common.logger import log


def convert_tf_example_to_dict(src_tf_example):
  assert isinstance(src_tf_example, tf.train.Example)
  dst_dict = OrderedDict()
  tf_feature = src_tf_example.features.feature
  for key, feat in tf_feature.items():
    if feat.HasField('int64_list'):
      csv_val = [item for item in feat.int64_list.value]  # pylint: disable=unnecessary-comprehension
    elif feat.HasField('bytes_list'):
      csv_val = [item for item in feat.bytes_list.value]  # pylint: disable=unnecessary-comprehension
    elif feat.HasField('float_list'):
      csv_val = [item for item in feat.float_list.value]  # pylint: disable=unnecessary-comprehension
    else:
      assert False, "feat type must in int64, byte, float"
    assert isinstance(csv_val, list)
    dst_dict[key] = csv_val[0] if len(csv_val) == 1 else csv_val
  return dst_dict


def check_path(filenames):
  from itertools import chain
  if not isinstance(filenames, list) or len(filenames) == 0 or \
          not all(isinstance(_, tuple) for _ in filenames) or \
          not all(isinstance(_, str) or isinstance(_, unicode) for _ in chain.from_iterable(filenames)):
    raise ValueError("filenames should be a filled list of tuple of strings, got{}".format(filenames))


def gather_res(ids, existence):
  assert len(ids) == len(existence), \
    'ids size {}, existence size {}'.format(len(ids), len(existence))
  res = []
  for i in range(0, len(existence)):
    if existence[i]:
      res.append(ids[i])
  return res


def to_bytes(v):
  if isinstance(v, bytes):
    return v
  return str(v).encode('utf-8')


def get_sample_store_key(hash_col_value, sort_col_value: int):
  return to_bytes(hash_col_value) + b'#' + to_bytes(sort_col_value)


def split_sample_store_key(sample_store_key: bytes):
  t = sample_store_key.split(b'#')
  return t

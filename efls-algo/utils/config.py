# Copyright (C) 2016-2021 Alibaba Group Holding Limited
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

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import argparse
import os

import efl

parser = argparse.ArgumentParser(description="fl demo arguments")
parser.add_argument('--data_dir', type=str, required=True)
parser.add_argument('--data_dir_local', type=str, required=True)
parser.add_argument('--data_mode', type=str, required=True)
parser.add_argument('--federal_role', type=str, required=True)
_CMD_ARGS, unknown = parser.parse_known_args()

def get_data_mode():
  data_mode = _CMD_ARGS.data_mode
  if data_mode not in ('data-join', 'local'):
    raise ValueError("Unkown data mode: [{}]".format(data_mode))
  return data_mode

def get_federal_role():
  federal_role = _CMD_ARGS.federal_role
  if federal_role not in ('leader', 'follower'):
    raise ValueError("Unkown federal role: [{}]".format(federal_role))
  return federal_role

def get_data_path(mode):
  if mode not in (efl.MODE.TRAIN, efl.MODE.EVAL):
    raise ValueError("Unknown mode: [{}]".format(mode))
  if mode == efl.MODE.TRAIN:
    sub_dir = "train"
  else:
    sub_dir = "test"
  data_dir = _CMD_ARGS.data_dir.strip()
  federal_role = get_federal_role()
  return os.sep.join([data_dir, federal_role, sub_dir])

def get_data_local_path(mode):
  if mode not in (efl.MODE.TRAIN, efl.MODE.EVAL):
    raise ValueError("Unknown mode: [{}]".format(mode))
  if mode == efl.MODE.TRAIN:
    sub_dir = "train"
  else:
    sub_dir = "test"
  data_dir = _CMD_ARGS.data_dir_local.strip()
  federal_role = get_federal_role()
  return os.sep.join([data_dir, federal_role, sub_dir])


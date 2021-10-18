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

import tensorflow as tf
from tensorflow.python.framework import errors
from tensorflow.python.framework import ops
from tensorflow.python.training.session_manager import SessionManager
from tensorflow.python.client import session
from tensorflow.python.training import distribution_strategy_context
from tensorflow.python.training import checkpoint_management

from efl.utils import func_patcher
from efl.utils import config

_SENTINEL_VARS = '_SENTINEL_VARS'
_FEDERAL_ROLE_ = "_FEDERAL_ROLE_"
_FEDERAL_COMMUNICATOR_ = "_FEDERAL_COMMUNICATOR_"

def create_sentinel_variables():
  for i in range(config.get_server_num()):
    tf.get_variable("efl_sentinel_var_{}".format(i),
                    shape = [],
                    dtype=tf.bool,
                    initializer=tf.constant_initializer(True),
                    collections=[ops.GraphKeys.LOCAL_VARIABLES, _SENTINEL_VARS],
                    trainable=False)

def init_federal_env(role, communicator):
  ops.add_to_collection(_FEDERAL_ROLE_, role)
  ops.add_to_collection(_FEDERAL_COMMUNICATOR_, communicator)

def _need_initialize(sess):
  try:
    sentinel_vars = ops.get_default_graph().get_collection(_SENTINEL_VARS)
    sess.run(sentinel_vars)
    return False
  except (errors.FailedPreconditionError, errors.UnavailableError):
    return True
  except Exception as e:
    return False

def _restore_checkpoint_hook(self,
                             master,
                             saver=None,
                             checkpoint_dir=None,
                             checkpoint_filename_with_path=None,
                             wait_for_checkpoint=False,
                             max_wait_secs=7200,
                             config=None):
  federal_role = ops.get_collection(_FEDERAL_ROLE_)
  communicator = ops.get_collection(_FEDERAL_COMMUNICATOR_)
  federal_role = None if len(federal_role) == 0 else federal_role[0]
  communicator = None if len(communicator) == 0 else communicator[0]
  if communicator is not None and federal_role not in ('follower', 'leader'):
    raise ValueError('Federal role must be one of `leader` or `follower` when communicator is set.')
  self._target = master
  sess = session.Session(self._target, graph=self._graph, config=config)

  need_initialize = _need_initialize(sess)
  if need_initialize:
    tf.logging.info('fresh start or ps failover, worker0 need do initialization')

    if checkpoint_dir and checkpoint_filename_with_path:
      raise ValueError("Can not provide both checkpoint_dir and "
                       "checkpoint_filename_with_path.")
    # If either saver or checkpoint_* is not specified, cannot restore. Just
    # return.
    if not saver or not (checkpoint_dir or checkpoint_filename_with_path):
      return sess, False

    if checkpoint_filename_with_path:
      saver.restore(sess, checkpoint_filename_with_path)
      return sess, True

    # Waits up until max_wait_secs for checkpoint to become available.
    wait_time = 0
    ckpt = checkpoint_management.get_checkpoint_state(checkpoint_dir)
    find_ckpt_success = False
    while not ckpt or not ckpt.model_checkpoint_path:
      if wait_for_checkpoint and wait_time < max_wait_secs:
        logging.info("Waiting for checkpoint to be available.")
        time.sleep(self._recovery_wait_secs)
        wait_time += self._recovery_wait_secs
        ckpt = checkpoint_management.get_checkpoint_state(checkpoint_dir)
        find_ckpt_success = True
      else:
        find_ckpt_success = False
        break
    if communicator is None:
      if not find_ckpt_success:
        return  sess, False
      # Loads the checkpoint.
      saver.restore(sess, ckpt.model_checkpoint_path)
      saver.recover_last_checkpoints(ckpt.all_model_checkpoint_paths)
    elif federal_role == 'leader':
      if not find_ckpt_success:
        communicator.send_ckpt_version(sess, "")
        return  sess, False
      # Loads the checkpoint.
      saver.restore(sess, ckpt.model_checkpoint_path)
      saver.recover_last_checkpoints(ckpt.all_model_checkpoint_paths)
      ckpt_prefix_len = len(checkpoint_dir)
      communicator.send_ckpt_version(
          sess, ckpt.model_checkpoint_path[ckpt_prefix_len:])
    else:
      ckpt_version = communicator.recv_ckpt_version(sess)
      if (not find_ckpt_success) and ckpt_version == "":
        return sess, False
      elif (not find_ckpt_success) and (not ckpt_version == ""):
        raise ValueError("Current checkpoint is empty. However federal leader load a valid checkpoint")
      else:
        ckpt_path = os.path.join(checkpoint_dir, ckpt_version)
        saver.restore(sess, ckpt.model_checkpoint_path)

    return sess, True
  else:
    tf.logging.info('worker failover, worker0 do not need do initialization')
    return sess, True

def patch():
  func_patcher.patch(_restore_checkpoint_hook, SessionManager, "_restore_checkpoint")

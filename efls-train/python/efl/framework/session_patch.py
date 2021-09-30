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

import os
import copy
import json
import threading
import contextlib

import tensorflow.compat.v1 as tf
from tensorflow.python.training import session_run_hook
from tensorflow.core.protobuf import config_pb2
from tensorflow.python.framework import errors
from tensorflow.python.framework import ops
from tensorflow.python.distribute import distribute_coordinator_context
from tensorflow.python.training import queue_runner
from tensorflow.python.training import coordinator
from tensorflow.python.training.monitored_session import _HookedSession, \
  _WrappedSession, _MonitoredSession, _RecoverableSession, _CoordinatedSession

from efl.framework.hook_manager import get_hook_manager
from efl.utils import func_patcher

class _HookedSessionV2(_HookedSession):
  r''' session can deal with feaxible hook use cases, 
  support task scope(for multitask learning) and temporary hooks
  '''
  def __init__(self, sess, hooks):
    _HookedSession.__init__(self, sess, hooks)

  def run(self, fetches, feed_dict=None, options=None, run_metadata=None):
    """See base class."""
    if self.should_stop():
      raise RuntimeError('Run called even after should_stop requested.')

    actual_fetches = {'caller': fetches}
    run_context = session_run_hook.SessionRunContext(
        original_args=session_run_hook.SessionRunArgs(fetches, feed_dict),
        session=self._sess)
    options = options or config_pb2.RunOptions()
    feed_dict = self._call_hook_before_run(run_context, actual_fetches,
                                           feed_dict, options)
    # Do session run.
    run_metadata = run_metadata or config_pb2.RunMetadata()
    outputs = _WrappedSession.run(self,
                                  fetches=actual_fetches,
                                  feed_dict=feed_dict,
                                  options=options,
                                  run_metadata=run_metadata)
    for hook in self._hooks + get_hook_manager().get_running_hooks():
      hook.after_run(
          run_context,
          session_run_hook.SessionRunValues(
              results=outputs[hook] if hook in outputs else None,
              options=options,
              run_metadata=run_metadata))
    self._should_stop = self._should_stop or run_context.stop_requested
    return outputs['caller']

  def _call_hook_before_run(self, run_context, fetch_dict, user_feed_dict,
                            options):
    """Calls hooks.before_run and handles requests from hooks."""
    hook_feeds = {}
    for hook in self._hooks + get_hook_manager().get_running_hooks():
      request = hook.before_run(run_context)
      if request is not None:
        if request.fetches is not None:
          fetch_dict[hook] = request.fetches
        if request.feed_dict:
          self._raise_if_feeds_intersects(
              hook_feeds, request.feed_dict,
              'Same tensor is fed by two hooks.')
          hook_feeds.update(request.feed_dict)
        if request.options:
          self._merge_run_options(options, request.options)

    if not hook_feeds:
      return user_feed_dict

    if not user_feed_dict:
      return hook_feeds

    self._raise_if_feeds_intersects(
        user_feed_dict, hook_feeds,
        'Same tensor is fed by a SessionRunHook and user.')
    hook_feeds.update(user_feed_dict)
    return hook_feeds

def _init_patch(self, session_creator, hooks, should_recover,
                stop_grace_period_secs=120, scaffold=None):
  """Sets up a Monitored or Hooked Session.

  Args:
    session_creator: A factory object to create session. Typically a
      `ChiefSessionCreator` or a `WorkerSessionCreator`.
    hooks: An iterable of `SessionRunHook' objects.
    should_recover: A bool. Indicates whether to recover from `AbortedError`
      and `UnavailableError` or not.
    stop_grace_period_secs: Number of seconds given to threads to stop after
      `close()` has been called.
  """
  self._scaffold = scaffold
  self._graph_was_finalized = ops.get_default_graph().finalized
  self._hooks = hooks or []
  self._is_chief = False
  tf_config = json.loads(os.environ.get('TF_CONFIG', '{}'))

  # get chief from TF_CONF
  if tf_config is not None and 'task' in tf_config \
    and 'type' in tf_config['task'] \
    and tf_config['task']['type'] == 'chief':
    self._is_chief = True

  for h in self._hooks + get_hook_manager().all_hooks:
    h.begin()

  worker_context = distribute_coordinator_context.get_current_worker_context()
  if not session_creator and worker_context:
    session_creator = worker_context.session_creator()

  # Create the session.
  self._coordinated_creator = self._CoordinatedSessionCreator(
      session_creator=session_creator or ChiefSessionCreator(),
      hooks=self._hooks,
      stop_grace_period_secs=stop_grace_period_secs)
  if should_recover:
    self._sess = _RecoverableSession(self._coordinated_creator)
  else:
    self._sess = self._coordinated_creator.create_session()

def _create_session_patch(self):
  """Creates a coordinated session."""
  # Keep the tf_sess for unit testing.
  self.tf_sess = self._session_creator.create_session()
  # We don't want coordinator to suppress any exception.
  self.coord = coordinator.Coordinator(clean_stop_exception_types=[])
  # set sess and coord
  get_hook_manager().set_sess_and_coord(self.tf_sess, self.coord)
  if ops.get_collection(ops.GraphKeys.QUEUE_RUNNERS):
    queue_runner.start_queue_runners(sess=self.tf_sess, coord=self.coord)
  # Inform the hooks that a new session has been created.
  for hook in self._hooks + get_hook_manager().all_hooks:
    hook.after_create_session(self.tf_sess, self.coord)
  return _CoordinatedSession(
      _HookedSessionV2(self.tf_sess, self._hooks), self.coord,
      self._stop_grace_period_secs)
  
def _close_internal_patch(self, exception_type=None):
  try:
    if not exception_type:
      for h in self._hooks:
        h.end(self._coordinated_creator.tf_sess)
      get_hook_manager().call_hook_end()
  finally:
    try:
      if self._sess is None:
        raise RuntimeError('Session is already closed.')
      self._sess.close()
    finally:
      self._sess = None
      self._coordinated_creator.tf_sess = None
      self._coordinated_creator.coord = None
      if not self._graph_was_finalized:
        ops.get_default_graph()._unsafe_unfinalize()  # pylint: disable=protected-access

def patch():
  func_patcher.patch(_init_patch, _MonitoredSession, "__init__")
  func_patcher.patch(_create_session_patch, _MonitoredSession._CoordinatedSessionCreator, "create_session")
  func_patcher.patch(_close_internal_patch, _MonitoredSession, "_close_internal")

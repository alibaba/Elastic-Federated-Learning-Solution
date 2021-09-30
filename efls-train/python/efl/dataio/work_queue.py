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

"""Work queue for storing input paths."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import os
import re
from six import string_types
from six.moves import xrange

from tensorflow.python.eager import context
from tensorflow.python.framework import constant_op
from tensorflow.python.data.ops import dataset_ops
from tensorflow.python.framework import dtypes
from tensorflow.python.framework import ops
from tensorflow.python.framework import tensor_shape
from tensorflow.python.ops import control_flow_ops
from tensorflow.python.ops import array_ops
from tensorflow.python.ops import data_flow_ops
from tensorflow.python.ops import io_ops
from tensorflow.python.ops import logging_ops
from tensorflow.python.ops import math_ops
from tensorflow.python.ops import random_ops
from tensorflow.python.ops import string_ops
from tensorflow.python.ops import variable_scope as vs
from tensorflow.python.platform import gfile
from tensorflow.python.platform import tf_logging as logging
from tensorflow.python.summary import summary
from tensorflow.python.training import queue_runner
from tensorflow.python.training import saver
from tensorflow.python.training import checkpoint_utils
from tensorflow.python.training import training

from efl import lib

class WorkQueue(saver.BaseSaverBuilder.SaveableObject):
  """A queue of works shared by all workers.

  A work queue is a queue that shares works for all workers. Any worker can use
  `take` or `input_producer` to take a work from this queue. On initialization,
  this queue will be populated by multiple epochs of work slices. Once failover
  happened, this queue can be restored from latest checkpoint.
  """
  class Resource(object): # pylint: disable=useless-object-inheritance
    """Resource object of a work queue."""
    def __init__(self, name, works):
      self._name = name
      self._works = works

    @property
    def name(self):
      """Resource name of the work queue."""
      return self._name

    @property
    def handle(self):
      """Resource handle of the work queue."""
      return self._works._handle  # pylint: disable=protected-access

    @property
    def create(self):
      """Resource creation op of the work queue."""
      return self._works._create  # pylint: disable=protected-access

    @property
    def is_initialized(self):
      """Resource creation check op of the work queue."""
      return self._works._is_initialized  # pylint: disable=protected-access

  def __init__(
      self,
      works,
      num_epochs=1,
      shuffle=True,
      seed=None,
      set_end_file=False,
      name=None):
    """Constructs a work queue.

    Args:
      works: A list of input paths.
      num_epochs: (Optional.) An integer. If specified, this work queue
        produces each work from `works` `num_epochs` times before
        generating an `OutOfRange` error. 1 by default.
      shuffle: (Optional.) Boolean. If true, the works are randomly shuffled
        within each epoch.
      seed: (Optional.) An integer. Seed used if shuffle == True.
      name: (Optional.) Name of the work queue.

    Raises:
      ValueError: If one of the arguments is invalid.
    """
    try:
      executing_eagerly = context.executing_eagerly()
    except: # pylint: disable=bare-except
      executing_eagerly = context.in_eager_mode()
    else:
      executing_eagerly = False
    if not executing_eagerly:
      name = ops.get_default_graph().unique_name(name or 'work_queue')
    else:
      name = name or context.context().scope_name

    if not isinstance(works, list) or not works:
      raise ValueError(
          "WorkQueue requires works as a list of strings")

    works = [
        w.encode() if isinstance(w, string_types) else w for w in works]
    if not all([isinstance(w, bytes) for w in works]):
      raise ValueError(
          "WorkQueue requires works as a list of strings not {}".format(
              [type(w) for w in works]))
    self._works = [w.strip() for w in works]

    if num_epochs <= 0:
      raise ValueError("num_epochs must be > 0 not {}.".format(num_epochs))

    with ops.name_scope(name):
      self._remote_device = vs.variable(
          0,
          name="colocator",
          trainable=False,
          validate_shape=False,
          collections=[ops.GraphKeys.LOCAL_VARIABLES]).device
      self._local_device = control_flow_ops.no_op().device
      with ops.device(self._remote_device):
        self._handle = lib.ops.work_queue_handle_op(shared_name=name)
        self._digest_op = ops.convert_to_tensor(
            self.digest, dtype=dtypes.string)
        self._save = lib.ops.work_queue_save(self._handle)
        specs = [
            saver.BaseSaverBuilder.SaveSpec(
                self._digest_op, "", name + "_digest"),
            saver.BaseSaverBuilder.SaveSpec(
                self._save, "", name + "_works")]
        self._capacity = len(self._works)
        works_tensor = ops.convert_to_tensor(
            self._works, dtype=dtypes.string)
        self._create = lib.ops.work_queue_create(
            self._handle, shared_name=name, set_end_file=set_end_file)
        for epoch_index in xrange(num_epochs):
          with ops.control_dependencies([self._create]):
            with ops.name_scope('epochs/{}'.format(epoch_index)):
              epoch = works_tensor
              if shuffle:
                epoch = random_ops.random_shuffle(epoch, seed=seed)
              with ops.control_dependencies(
                  [logging_ops.print_v2(
                      "Add epoch of",
                      array_ops.size(epoch),
                      "elements:",
                      epoch,
                      summarize=8)]):
                epoch = array_ops.identity(epoch)
              self._create = lib.ops.work_queue_put(self._handle, epoch)
        with ops.control_dependencies([self._create]):
          self._create = lib.ops.work_queue_close(self._handle)
        self._is_initialized = lib.ops.work_queue_is_initialized(
            self._handle)

    ops.add_to_collection(ops.GraphKeys.SAVEABLE_OBJECTS, self)
    ops.add_to_collection(
        ops.GraphKeys.RESOURCES, WorkQueue.Resource(name, self))
    logging.info("%s placed at %s.", name, self._remote_device)
    super(WorkQueue, self).__init__(self, specs, name)

  def __len__(self):
    """Number of elements in the work queue."""
    return self._capacity

  @property
  def works(self):
    """The works in the work queue."""
    return self._works

  @property
  def digest(self):
    """The digest of works."""
    return b','.join(self._works)

  def load_from_checkpoint(
      self, ckpt_dir_or_file, filename_tensor, preferred_shard):
    """Loads tensors from the checkpoint.
    """
    del preferred_shard

    ckpt_ready = False
    try:
      ckpt_reader = checkpoint_utils.load_checkpoint(ckpt_dir_or_file)
      tensors_in_ckpt = ckpt_reader.get_variable_to_shape_map()
      ckpt_ready = all([spec.name in tensors_in_ckpt for spec in self.specs])
      del tensors_in_ckpt
      del ckpt_reader
    except:  # pylint: disable=bare-except
      pass

    # If tensors found in the checkpoint, do normal restoration.
    if ckpt_ready:
      return [
          io_ops.restore_v2(
              filename_tensor,
              [spec.name],
              [spec.slice_spec],
              [spec.dtype])[0]
          for spec in self.specs]

    # If no tensors found in the checkpoint, just return None.
    return [None, None]

  def restore(self, restored_tensors, _):
    """Restores the work queue from restored_tensors.

    Args:
      restored_tensors: Tensor tuple (digest, works).
    """
    if len(restored_tensors) != 2:
      raise ValueError('WorkQueue requires 2 tensors to restore')
    if restored_tensors[0] is None or restored_tensors[1] is None:
      logging.info("Work queue %s not found in checkpoint.", self.name)
      with ops.name_scope("{}_restore".format(self.name)):
        return self._create
    logging.info("Restore work queue %s.", self.name)
    packed_digest = ops.convert_to_tensor(
        restored_tensors[0], dtype=dtypes.string)
    current_digest = ops.convert_to_tensor(
        self.digest, dtype=dtypes.string)
    same_works_again = math_ops.equal(packed_digest, current_digest)
    works = ops.convert_to_tensor(
        restored_tensors[1], dtype=dtypes.string)
    with ops.control_dependencies([self._create]):
      create_with_prompt = logging_ops.print_v2(
          "Works queue {} abandoned in checkpoint.".format(self.name))
    with ops.name_scope("{}/restore".format(self.name)):
      return control_flow_ops.cond(
          same_works_again,
          lambda: lib.ops.work_queue_restore(self._handle, works),
          lambda: create_with_prompt)

  def take_fn(self):
    """Take work from remote worker."""
    with ops.name_scope(self.name):
      with ops.device(self._remote_device):
        taken = lib.ops.work_queue_take(
            self._handle)
    with ops.device(self._local_device):
      local_work = array_ops.identity(taken)
      return local_work

  def take(self):
    """Take work from the work queue."""
    return self.take_fn()

  def input_producer(self):
    """Returns a FIFOQueue as input producer.

    Returns:
      A local queue of work items.  A `QueueRunner` for the Queue
      is added to the current `Graph`'s `QUEUE_RUNNER` collection.
    """
    work = self.take()
    with ops.name_scope(self.name):
      with ops.device(self._local_device):
        proxy = data_flow_ops.FIFOQueue(
            capacity=1,
            dtypes=[dtypes.string],
            shapes=[tensor_shape.TensorShape([1])],
            name='proxy')
        with ops.control_dependencies(
            [logging_ops.print_v2("Take work:", work)]):
          work = array_ops.identity(work)
        enqueue_proxy = proxy.enqueue(array_ops.reshape(work, (1,)))
        cancel_proxy = proxy.close(cancel_pending_enqueues=True)
        proxy_runner = queue_runner.QueueRunner(
            proxy, [enqueue_proxy], cancel_op=cancel_proxy)
        queue_runner.add_queue_runner(proxy_runner)
        return proxy

  def input_dataset(self):
    """Returns a dataset as input dataset

    Returns:
      A local dataset of work items.
    """
    proxy = self.input_producer()
    def get_next_work(_):
      work = array_ops.reshape(proxy.dequeue(), [])
      with ops.control_dependencies(
          [logging_ops.print_v2("Take work outof local queue:", work)]):
        return work
    with ops.name_scope(self.name):
      with ops.device(self._local_device):
        dataset = dataset_ops.Dataset.from_tensors(0).repeat()
        dataset = dataset.map(get_next_work)
        return dataset

  def add_summary(self):
    """Gets size of the work queue.

    Returns:
      Size of the work queue.
    """
    with ops.name_scope(self.name):
      with ops.device(self._remote_device):
        size = lib.ops.work_queue_size(self._handle)
    summary.scalar(
        "{}/fraction_of_{}_full".format(self.name, self._capacity),
        math_ops.to_float(size) * (1. / self._capacity))


class FederalWorkQueue(WorkQueue):

  def __init__(
      self,
      works,
      num_epochs=1,
      shuffle=True,
      seed=None,
      name=None):
    super(FederalWorkQueue, self).__init__(
        works,
        num_epochs=num_epochs,
        shuffle=shuffle,
        seed=seed,
        set_end_file=True,
        name=name
        )

  def input_dataset(self):
    """Returns a dataset as input dataset

    Returns:
      A local dataset of work items.
    """
    proxy = self.input_producer()
    def get_next_work(_):
      work = array_ops.reshape(proxy.dequeue(), [])
      return work
    with ops.name_scope(self.name):
      with ops.device(self._local_device):
        dataset = dataset_ops.Dataset.from_tensors(0).repeat()
        dataset = dataset.map(get_next_work)
        return dataset

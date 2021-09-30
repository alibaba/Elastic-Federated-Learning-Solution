import sys
sys.path.insert(0, '.')

import os
import shutil
import numpy as np
import unittest

import tensorflow as tf
from tensorflow.python.framework import ops
from tensorflow.python.training import saver as saver_module

import efl
from efl.lib import ops as fed_ops
from efl.dataio import dataio_hook


class TestDataIO(unittest.TestCase):

  @classmethod
  def setUpClass(cls):
    def build_tfrecord(file_path, sample_num, offset=0, file_num=1):
      if not os.path.exists(file_path):
        os.mkdir(file_path)
      for j in range(file_num):
        writer = tf.io.TFRecordWriter(
            os.path.join(file_path, "data_{}.tfrd".format(j)))
        for i in range(sample_num):
          sample_id = str(j * sample_num + i)
          features = np.asarray([offset + j * sample_num + i for _ in range(32)])
          example = tf.train.Example(features=tf.train.Features(
              feature={
                  'sample_id': tf.train.Feature(bytes_list = tf.train.BytesList(value=[bytes(sample_id, 'utf-8')])), 
                  'feature':tf.train.Feature(int64_list = tf.train.Int64List(value=features))
                  }))
          writer.write(example.SerializeToString()) 
        writer.close()
    build_tfrecord("./leader", 100, file_num=4)
    build_tfrecord("./follower", 100, offset=1000, file_num=4)

  @classmethod
  def tearDownClass(cls):
    shutil.rmtree('./leader')
    shutil.rmtree('./follower')
  
  def test_dataio_list_file(self):
    dataio = efl.data.DataIO("./", 2, 0, 1)
    dataio.add_file_node("leader")
    dataio.add_file_nodes(["follower"])
    file_list = dataio._list_block_ids()
    expect_list = ['./follower/data_0.tfrd', './follower/data_1.tfrd', './follower/data_2.tfrd', './follower/data_3.tfrd',
                   './leader/data_0.tfrd', './leader/data_1.tfrd', './leader/data_2.tfrd', './leader/data_3.tfrd']
    self.assertTrue(file_list == expect_list)

  def test_dataio_add_feature(self):
    dataio = efl.data.DataIO("./", 2, 0, 1)
    dataio.add_file_node("leader")
    dataio.fixedlen_feature('feature', 32, dtype=tf.int64)
    dataio.varlen_feature('sample_id', dtype=tf.string)
    batch = dataio.read()
    self.assertTrue('feature' in batch)
    self.assertTrue('sample_id' in batch)
  
  def test_dataio_read(self):
    dataio = efl.data.DataIO("./", 2, 0, 1)
    dataio.add_file_node("leader")
    dataio.fixedlen_feature('feature', 32, dtype=tf.int64)
    dataio.varlen_feature('sample_id', dtype=tf.string)
    batch = dataio.read()
    sample_id = batch['sample_id']
    feature = batch['feature']
    with tf.compat.v1.train.MonitoredTrainingSession() as sess:
      dataio.initialize_iter(sess)
      for i in range(3):
        sid, fea = sess.run([sample_id, feature])
      self.assertTrue((fea == np.array([[4] * 32, [5] * 32])).all())

  def test_dataio_save_restore(self):
    checkpoint_directory = './ckpt_dir'
    if not os.path.exists(checkpoint_directory):
      os.mkdir(checkpoint_directory)
    checkpoint_prefix = os.path.join(checkpoint_directory, "ckpt")
    save_graph = ops.Graph()
    with save_graph.as_default():
      dataio = efl.data.DataIO("./", 2, 0, 1)
      dataio.add_file_node("leader")
      dataio.fixedlen_feature('feature', 32, dtype=tf.int64)
      dataio.varlen_feature('sample_id', dtype=tf.string)
      batch = dataio.read()
      sample_id = batch['sample_id']
      feature = batch['feature']
      g_step = tf.compat.v1.train.get_or_create_global_step()
      g_step = tf.compat.v1.assign_add(g_step, 101)
      with tf.compat.v1.train.MonitoredTrainingSession(save_checkpoint_steps=100, checkpoint_dir=checkpoint_prefix) as sess:
        dataio.initialize_iter(sess)
        for i in range(5):
          sid, fea = sess.run([sample_id, feature])
        sess.run(g_step)
        sid, fea = sess.run([sample_id, feature])

    restore_graph = ops.Graph()
    with restore_graph.as_default():
      dataio = efl.data.DataIO("./", 2, 0, 1)
      dataio.add_file_node("leader")
      dataio.fixedlen_feature('feature', 32, dtype=tf.int64)
      dataio.varlen_feature('sample_id', dtype=tf.string)
      batch = dataio.read()
      sample_id = batch['sample_id']
      feature = batch['feature']
      g_step = tf.compat.v1.train.get_or_create_global_step()
      with tf.compat.v1.train.MonitoredTrainingSession(checkpoint_dir=checkpoint_prefix) as sess:
        dataio.initialize_iter(sess)
        for i in range(3):
          sid, fea = sess.run([sample_id, feature])
    shutil.rmtree('./ckpt_dir')

  def test_dataio_hook_save_restore(self):
    checkpoint_directory = './ckpt_dir'
    if not os.path.exists(checkpoint_directory):
      os.mkdir(checkpoint_directory)
    checkpoint_prefix = os.path.join(checkpoint_directory, "ckpt")
    save_graph = ops.Graph()
    first_run_sid = None
    first_run_fea = None
    with save_graph.as_default():
      dataio = efl.data.DataIO("./", 2, 0, 1)
      dataio.add_file_node("leader")
      dataio.fixedlen_feature('feature', 32, dtype=tf.int64)
      dataio.varlen_feature('sample_id', dtype=tf.string)
      batch = dataio.read()
      d_hook = dataio_hook.DataIOHook(dataio, save_interval=1)
      sample_id = batch['sample_id']
      feature = batch['feature']
      g_step = tf.compat.v1.train.get_or_create_global_step()
      g_step = tf.compat.v1.assign_add(g_step, 101)
      with tf.compat.v1.train.MonitoredTrainingSession(hooks=[d_hook], save_checkpoint_steps=100, checkpoint_dir=checkpoint_prefix) as sess:
        for i in range(3):
          sid, fea = sess.run([sample_id, feature])
        sess.run(g_step)
        sess.run(d_hook._save_state)
        first_run_sid, first_run_fea = sess.run([sample_id, feature])

    restore_graph = ops.Graph()
    with restore_graph.as_default():
      dataio = efl.data.DataIO("./", 2, 0, 1)
      dataio.add_file_node("leader")
      dataio.fixedlen_feature('feature', 32, dtype=tf.int64)
      dataio.varlen_feature('sample_id', dtype=tf.string)
      batch = dataio.read()
      d_hook = dataio_hook.DataIOHook(dataio, save_interval=1)
      sample_id = batch['sample_id']
      feature = batch['feature']
      g_step = tf.compat.v1.train.get_or_create_global_step()
      with tf.compat.v1.train.MonitoredTrainingSession(hooks=[d_hook], checkpoint_dir=checkpoint_prefix) as sess:
        sid, fea = sess.run([sample_id, feature])
        self.assertTrue((fea == first_run_fea).all())
    shutil.rmtree('./ckpt_dir')

if __name__ == '__main__':  
    unittest.main()


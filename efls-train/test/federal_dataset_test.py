import sys
sys.path.insert(0, '.')

import os
import shutil
import numpy as np
import unittest

import tensorflow as tf
from tensorflow.python.data.ops import dataset_ops
import efl
from efl.lib import ops

class TestFederalDataset(unittest.TestCase):

  @classmethod
  def setUpClass(cls):
    def build_tfrecord(file_path, sample_num, offset=0):
      if not os.path.exists(file_path):
        os.mkdir(file_path)
      writer = tf.io.TFRecordWriter(os.path.join(file_path, "data.tfrd"))
      for i in range(sample_num):
        features = np.asarray([offset + i for _ in range(32)])
        example = tf.train.Example(features=tf.train.Features(
            feature={
                'sample_id': tf.train.Feature(int64_list = tf.train.Int64List(value=[i])), 
                'feature':tf.train.Feature(int64_list = tf.train.Int64List(value=features))
                }))
        writer.write(example.SerializeToString()) 
      writer.close()
    build_tfrecord("./leader", 100)
    build_tfrecord("./follower", 100, 100)

  @classmethod
  def tearDownClass(cls):
    shutil.rmtree('./leader')
    shutil.rmtree('./follower')

  def generate_feature_map(self):
    feature_map = {}
    feature_map['sample_id'] = tf.io.FixedLenFeature([1], tf.int64)
    feature_map['feature'] = tf.io.FixedLenFeature([32], tf.int64)
    return feature_map
  
  def test_read_leader(self):
    dataset = efl.data.FederalDataset(["./leader/data.tfrd"])
    dataset = dataset.batch(2)
    data_record = dataset_ops.make_one_shot_iterator(dataset).get_next()
    features = tf.io.parse_example(data_record, features=self.generate_feature_map())
    sample_id = features["sample_id"]
    feature = features["feature"]
    sess = tf.compat.v1.Session()
    for i in range(3):
      sid, fea = sess.run([sample_id, feature])
    self.assertTrue((sid == np.array([[4], [5]])).all())
    self.assertTrue((fea == np.array([[4] * 32, [5] * 32])).all())

  def test_read_leader_with_offset(self):
    dataset = efl.data.FederalDataset(["./leader/data.tfrd"], sample_index=3)
    dataset = dataset.batch(2)
    data_record = dataset_ops.make_one_shot_iterator(dataset).get_next()
    features = tf.io.parse_example(data_record, features=self.generate_feature_map())
    sample_id = features["sample_id"]
    feature = features["feature"]
    sess = tf.compat.v1.Session()
    for i in range(3):
      sid, fea = sess.run([sample_id, feature])
    self.assertTrue((sid == np.array([[7], [8]])).all())
    self.assertTrue((fea == np.array([[7] * 32, [8] * 32])).all())

  def test_reader_state_restore(self):
    file_ph = tf.compat.v1.placeholder(tf.string, shape=[None])
    dataset = efl.data.FederalDataset(file_ph)
    dataset = dataset.batch(2)
    data_iterator = dataset_ops.make_initializable_iterator(dataset)
    data_record = data_iterator.get_next()
    features = tf.io.parse_example(data_record, features=self.generate_feature_map())
    sample_id = features["sample_id"]
    feature = features["feature"]
    reader_state = ops.serialize_iterator_to_string(
        data_iterator._iterator_resource)

    file_ph1 = tf.compat.v1.placeholder(tf.string, shape=[None])
    dataset1 = efl.data.FederalDataset(file_ph1)
    dataset1 = dataset1.batch(2)
    data_iterator1 = dataset_ops.make_initializable_iterator(dataset1)
    data_record1 = data_iterator1.get_next()
    features1 = tf.io.parse_example(data_record1, features=self.generate_feature_map())
    sample_id1 = features1["sample_id"]
    feature1 = features1["feature"]
    restore_state = ops.deserialize_iterator_from_string(
        data_iterator1._iterator_resource, reader_state)
   
    sess = tf.compat.v1.Session()
    sess.run(tf.compat.v1.global_variables_initializer())
    sess.run(data_iterator.initializer, feed_dict={file_ph: ["./leader/data.tfrd"]})
    sess.run(data_iterator1.initializer, feed_dict={file_ph1: ["./leader/data.tfrd"]})
    for i in range(3):
      sid, fea = sess.run([sample_id, feature])
    sess.run(restore_state)
    sid, fea = sess.run([sample_id1, feature1])
    self.assertTrue((sid == np.array([[6], [7]])).all())
    self.assertTrue((fea == np.array([[6] * 32, [7] * 32])).all())

  def test_get_sample_index(self):
    file_ph = tf.compat.v1.placeholder(tf.string, shape=[None])
    dataset = efl.data.FederalDataset(file_ph)
    dataset = dataset.batch(2)
    data_iterator = dataset_ops.make_initializable_iterator(dataset)
    data_record = data_iterator.get_next()
    features = tf.io.parse_example(data_record, features=self.generate_feature_map())
    sample_id = features["sample_id"]
    feature = features["feature"]
    reader_state = ops.serialize_iterator_to_string(
        data_iterator._iterator_resource)
    sample_index = ops.get_sample_index_from_iter_string(reader_state)
    sess = tf.compat.v1.Session()
    sess.run(tf.compat.v1.global_variables_initializer())
    sess.run(data_iterator.initializer, feed_dict={file_ph: ["./leader/data.tfrd"]})
    for i in range(3):
      sid, fea = sess.run([sample_id, feature])
    sidx = sess.run(sample_index)
    self.assertTrue(sidx == 6)

  def test_get_block_id(self):
    dataset = efl.data.FederalDataset(["./leader/data.tfrd"], ["leader0"], sample_index=3)
    dataset = dataset.batch(2)
    data_iterator = dataset_ops.make_initializable_iterator(dataset)
    data_record = data_iterator.get_next()
    features = tf.io.parse_example(data_record, features=self.generate_feature_map())
    sample_id = features["sample_id"]
    feature = features["feature"]
    reader_state = ops.serialize_iterator_to_string(
        data_iterator._iterator_resource)
    block_id = ops.get_block_id_from_iter_string(reader_state)
    sess = tf.compat.v1.Session()
    sess.run(tf.compat.v1.global_variables_initializer())
    sess.run(data_iterator.initializer)
    for i in range(3):
      sid, fea = sess.run([sample_id, feature])
    sidx = sess.run(block_id)
    self.assertTrue(sidx == b"leader0")

  def test_restore_from_sample_index(self):
    file_ph = tf.compat.v1.placeholder(tf.string, shape=[None])
    dataset = efl.data.FederalDataset(file_ph)
    dataset = dataset.batch(2)
    data_iterator = dataset_ops.make_initializable_iterator(dataset)
    data_record = data_iterator.get_next()
    features = tf.io.parse_example(data_record, features=self.generate_feature_map())
    sample_id = features["sample_id"]
    feature = features["feature"]
    reader_state = ops.serialize_iterator_to_string(
        data_iterator._iterator_resource)
    index_state = ops.set_sample_index_from_iter_string(reader_state, 6)
    restore_state = ops.deserialize_iterator_from_string(
        data_iterator._iterator_resource, index_state)

    sess = tf.compat.v1.Session()
    sess.run(tf.compat.v1.global_variables_initializer())
    sess.run(data_iterator.initializer, feed_dict={file_ph: ["./leader/data.tfrd"]})
    sess.run(restore_state)
    sid, fea = sess.run([sample_id, feature])
    self.assertTrue((sid == np.array([[6], [7]])).all())
    self.assertTrue((fea == np.array([[6] * 32, [7] * 32])).all())

  def test_init_from_leader_reader_state(self):
    file_ph = tf.compat.v1.placeholder(tf.string, shape=[None])
    dataset = efl.data.FederalDataset(file_ph)
    dataset = dataset.batch(2)
    data_iterator = dataset_ops.make_initializable_iterator(dataset)
    data_record = data_iterator.get_next()
    features = tf.io.parse_example(data_record, features=self.generate_feature_map())
    sample_id = features["sample_id"]
    feature = features["feature"]
    reader_state = ops.serialize_iterator_to_string(
        data_iterator._iterator_resource)
    sample_index = ops.get_sample_index_from_iter_string(reader_state)

    file_ph1 = tf.compat.v1.placeholder(tf.string, shape=[None])
    dataset1 = efl.data.FederalDataset(file_ph1)
    dataset1 = dataset1.batch(2)
    data_iterator1 = dataset_ops.make_initializable_iterator(dataset1)
    data_record1 = data_iterator1.get_next()
    features1 = tf.io.parse_example(data_record1, features=self.generate_feature_map())
    sample_id1 = features1["sample_id"]
    feature1 = features1["feature"]
    reader_state1 = ops.serialize_iterator_to_string(
        data_iterator1._iterator_resource)
    index_state = ops.set_sample_index_from_iter_string(reader_state1, sample_index)
    restore_state = ops.deserialize_iterator_from_string(
        data_iterator1._iterator_resource, index_state)
   
    sess = tf.compat.v1.Session()
    sess.run(tf.compat.v1.global_variables_initializer())
    sess.run(data_iterator.initializer, feed_dict={file_ph: ["./leader/data.tfrd"]})
    sess.run(data_iterator1.initializer, feed_dict={file_ph1: ["./follower/data.tfrd"]})
    for i in range(3):
      sid, fea = sess.run([sample_id, feature])
    sess.run(restore_state)
    sid, fea = sess.run([sample_id1, feature1])
    self.assertTrue((sid == np.array([[6], [7]])).all())
    self.assertTrue((fea == np.array([[106] * 32, [107] * 32])).all())

if __name__ == '__main__':  
    unittest.main()


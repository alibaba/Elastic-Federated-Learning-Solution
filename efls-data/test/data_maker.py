import os
import random
import shutil
import tensorflow as tf

Max_v = 10000000000
data_list = []
data_dict_list_x = {}
data_dict_list_y = {}
data_id_client = []
data_id_server = []
data_dict_client = {}
data_dict_server = {}
data_seq_client = []
data_seq_server = []
#default val,
data_list_size, client_data_size, server_data_size = 100000, 50000, 50000
client_data_path = "/tmp/input/test_data_client"
server_data_path = "/tmp/input/test_data_server"
file_batch_size = 4096
file_cnt = 10
# dataformat: example_id, event_time, emb


def init():
  global data_list, data_dict_list_x, data_dict_list_y, data_id_client \
  ,data_id_server, data_dict_client, data_dict_server,  \
  data_seq_client, data_seq_server

  data_list = []
  data_dict_list_x = {}
  data_dict_list_y = {}
  data_id_client = []
  data_id_server = []
  data_dict_client = {}
  data_dict_server = {}
  data_seq_client = []
  data_seq_server = []

def _bytes_feature(value):
    """Returns a bytes_list from a string / byte."""
    if isinstance(value, type(tf.constant(0))):
        value = value.numpy()  # BytesList won't unpack a string from an EagerTensor.
    return tf.train.Feature(bytes_list=tf.train.BytesList(value=[value]))

def _float_feature(value):
    """Returns a float_list from a float / double."""
    return tf.train.Feature(float_list=tf.train.FloatList(value=[value]))

def _int64_feature(value):
    """Returns an int64_list from a bool / enum / int / uint."""
    return tf.train.Feature(int64_list=tf.train.Int64List(value=[value]))


def write_data(write_path, data_id, data_seq):
    cnt_file = 0
    cnt_data = 0
    output_file_path = os.path.join(write_path, str(cnt_file) + '.tfrecords')
    output_file = tf.io.TFRecordWriter(output_file_path)
    for i in range(client_data_size):  # random.sample(sequence, k)
        x = random.randint(0, data_list_size - 1)
        while x in data_id:
            x = random.randint(0, data_list_size - 1)
        data_id[x] = 1
        data_seq.append(x)
        output_file.write(data_list[x].SerializeToString())
        cnt_data += 1
        if cnt_data >= file_batch_size:
            output_file.close()
            cnt_file += 1
            output_file_path = os.path.join(write_path, str(cnt_file) + '.tfrecords')
            output_file = tf.io.TFRecordWriter(output_file_path)
            cnt_data = 0

def data_prepare():
    for i in range(data_list_size):
        x, y, z = random.randint(0, Max_v), random.randint(0, Max_v), random.randint(0, Max_v)
        while x in data_dict_list_x:
            x = random.randint(0, Max_v)
        while y in data_dict_list_y:
            y = random.randint(0, Max_v)
        data_dict_list_x[x] = 1
        data_dict_list_y[y] = 1
        tf_example = tf.train.Example(
            features=tf.train.Features(
                feature={
                    'example_id': _bytes_feature(x.to_bytes(length=8, byteorder='big', signed=False)),
                    'event_time': _int64_feature(y),
                    'aliemb': _float_feature(float(z)),
                }
            ))
        data_list.append(tf_example)

def get_common_data(seq1, seq2):
    common_data = []
    seq1.sort()
    seq2.sort()
    len1, len2 = 0, 0
    while len1 < len(seq1) and len2 < len(seq2):
        if seq1[len1] == seq2[len2]:
            common_data.append(data_list[seq1[len1]])
            len1 += 1
            len2 += 1
        elif seq1[len1] < seq2[len2]:
            len1 += 1
        else:
            len2 += 1
    return common_data

def make_data(client_size = 60000, client_path = "/tmp/input/test_data_client", server_size = 60000, server_path = "/tmp/input/test_data_server"):
    init()
    client_data_size = client_size
    client_data_path = client_path
    server_data_size = server_size
    server_data_path = server_path
    data_list_size = (client_data_size + server_data_size) * 2  // 3
    file_batch_size = client_size // file_cnt

    data_prepare()

    if os.path.exists(client_data_path):
        shutil.rmtree(client_data_path)
    os.makedirs(client_data_path)
    if os.path.exists(server_data_path):
        shutil.rmtree(server_data_path)
    os.makedirs(server_data_path)
    write_data(client_data_path, data_dict_client, data_seq_client)
    write_data(server_data_path, data_dict_server, data_seq_server)
    common_data = get_common_data(data_seq_client, data_seq_server)
    print("data maker finished")
    return common_data

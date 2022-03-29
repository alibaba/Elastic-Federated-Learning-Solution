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

import os
import shutil
import threading

import numpy as np
import tensorflow as tf
import unittest

from data_maker import make_data
from xfl.data.pipelines import data_join_pipeline
from xfl.service.nginx import Nginx

tf.enable_eager_execution()
#default file path
client_result_path = "/tmp/output/TEST_DATA_JOIN_CLI"
server_result_path = "/tmp/output/TEST_DATA_JOIN_SERVER"
client_data_path = "/tmp/input/test_data_client"
server_data_path = "/tmp/input/test_data_server"
np.random.seed(0)
JOB_NAME='TEST_DATA_JOIN'

class model_thread(threading.Thread):
    def __init__(self,
                 job_name: str,
                 is_server: bool,
                 input_path: str,
                 output_path: str,
                 hash_col_name: str,
                 sort_col_name: str,
                 bucket_num: int,
                 sample_store_type = 'memory',
                 host='localhost',
                 port=50051,
                 ingress_ip='127.0.0.1',
                 batch_size=2048,
                 file_part_size=1024,
                 jar='file:///xfl/lib/efls-flink-connectors-1.0-SNAPSHOT.jar',
                 run_mode='local',
                 tls_crt_path=None,
                 rsa_pub_path=None,
                 rsa_pri_path=None,
                 wait_s=1800,
                 use_psi=False,
                 psi_type='ecdh',
                 need_sort=True,
                 client2multiserver=1):
        threading.Thread.__init__(self)
        conf = {'jars': jar.split(',')}

        self.pipeline = data_join_pipeline(
            input_path=input_path,
            output_path=output_path,
            job_name=job_name,
            host=host,
            port=port,
            ip=ingress_ip,
            bucket_num=bucket_num,
            run_mode=run_mode,
            hash_col_name=hash_col_name,
            sort_col_name=sort_col_name,
            is_server=is_server,
            sample_store_type=sample_store_type,
            batch_size=batch_size,
            file_part_size=file_part_size,
            tls_crt_path=tls_crt_path,
            rsa_pub_path=rsa_pub_path,
            rsa_pri_path=rsa_pri_path,
            wait_s=wait_s,
            use_psi=use_psi,
            psi_type=psi_type,
            need_sort=need_sort,
            db_root_path='/opt',
            client2multiserver=client2multiserver,
            conf=conf)

    def run(self):
        self.pipeline.run()

def run_client_and_server(sample_store_type, use_psi, need_sort=True, psi_type='ecdh', client2multiserver=1):
    if os.path.exists(client_result_path):
        shutil.rmtree(client_result_path)
    if os.path.exists(server_result_path):
        shutil.rmtree(server_result_path)
    print("Server startup")
    server_thread = model_thread(JOB_NAME, True,
                                 server_data_path, server_result_path,
                                 'example_id', 'example_id', 8,
                                 sample_store_type=sample_store_type,
                                 use_psi=use_psi,
                                 psi_type=psi_type,
                                 need_sort=need_sort,
                                 client2multiserver=client2multiserver)
    print("Client startup")
    client_thread = model_thread(JOB_NAME, False,
                                 client_data_path, client_result_path,
                                 'example_id', 'example_id', int(8/client2multiserver),
                                 ingress_ip='127.0.0.1',
                                 port=80,
                                 sample_store_type=sample_store_type,
                                 use_psi=use_psi,
                                 psi_type=psi_type,
                                 need_sort=need_sort,
                                 client2multiserver=client2multiserver)

    server_thread.start()
    client_thread.start()

    server_thread.join()
    client_thread.join()
    print("Server and client end")

def get_event_time(example):
    return list(example.features.feature['event_time'].int64_list.value)[0]

def get_tfrecord(filename, data_):
    filename_ = [filename]
    raw_dataset = tf.data.TFRecordDataset(filename_)
    for raw_record in raw_dataset:
        example = tf.train.Example()
        example.ParseFromString(raw_record.numpy())
        data_.append(example)

def result_judge(data_common):
    data_cli = []
    data_server = []

    for dirs_bucket in os.listdir(client_result_path):
        path_cli_bucket = os.path.join(client_result_path, dirs_bucket)
        print("processing client result files in : %s" % path_cli_bucket)
        for files in os.listdir(path_cli_bucket):
            get_tfrecord(os.path.join(path_cli_bucket, files), data_cli)
    for dirs_bucket in os.listdir(server_result_path):
        path_server_bucket = os.path.join(server_result_path, dirs_bucket)
        print("processing server result files in : %s" % path_server_bucket)
        for files in os.listdir(path_server_bucket):
            get_tfrecord(os.path.join(path_server_bucket, files), data_server)

    record_cnt_cli = len(data_cli)
    record_cnt_server = len(data_server)
    record_cnt_groundtrue = len(data_common)
    data_cli.sort(key=get_event_time)
    data_server.sort(key=get_event_time)
    data_common.sort(key=get_event_time)

    print("Client result size: %d and server result size: %d" % (record_cnt_cli, record_cnt_server))
    print("Groundtrue result size: %d" % record_cnt_groundtrue)
    if record_cnt_cli != record_cnt_groundtrue:
        print("Client datajoin result size error")
    if record_cnt_server != record_cnt_groundtrue:
        print("Server datajoin result size error")

    cnt1, cnt2 = 0, 0
    if record_cnt_cli == record_cnt_server:
        get_error = False
        for i in range(record_cnt_cli):
            if i < record_cnt_cli - 1 and data_cli[i] == data_cli[i + 1]:
                cnt1 += 1
            if i < record_cnt_cli - 1 and data_server[i] == data_server[i + 1]:
                cnt2 += 1
            if data_cli[i] != data_common[i]:
                print("client data not equal to groundtrue on %d", i)
                print(data_cli[i])
                print(data_common[i])
                get_error = True
                break
            if data_server[i] != data_common[i]:
                print("server data not equal to groundtrue on %d", i)
                print(data_server[i])
                print(data_common[i])
                get_error = True
                break

        assert not get_error, "Some error occur!"
        print("data repeat %d times in client" % cnt1)
        print("data repeat %d times in server" % cnt2)

class TestPsiDataJoin(unittest.TestCase):
    def setUp(self):
        print("setup make data...")
        self._data_common = make_data()
        print('prepare nginx...')
        nginx = Nginx(JOB_NAME, 8)
        nginx.stop()
        nginx.dumps('/tmp/efls_nginx_test.conf')
        nginx.start('/tmp/efls_nginx_test.conf')

    def test_join(self):
        print('test common join...')
        run_client_and_server(sample_store_type='memory', use_psi=False)
        result_judge(self._data_common)

    def test_join_with_level_db(self):
        print('test leveldb join...')
        run_client_and_server(sample_store_type='leveldb', use_psi=False)
        result_judge(self._data_common)

    def test_join_no_need_sort(self):
        print('test leveldb join...')
        run_client_and_server(sample_store_type='memory', use_psi=False, need_sort=False)
        result_judge(self._data_common)

    def test_rsa_join_with_level_db(self):
        print('test leveldb psi join...')
        run_client_and_server(sample_store_type='leveldb', use_psi=True, psi_type='rsa')
        result_judge(self._data_common)

    def test_ecdh_join_with_level_db(self):
        print('test leveldb psi join...')
        run_client_and_server(sample_store_type='leveldb', use_psi=True, psi_type='ecdh')
        result_judge(self._data_common)

    def test_c2ms_join(self):
        print('test c2ms common join...')
        run_client_and_server(sample_store_type='memory', use_psi=True, psi_type='ecdh', client2multiserver=2)
        result_judge(self._data_common)

    def tearDown(self):
        print("tearDown, remove tmp data...")
        shutil.rmtree(client_result_path)
        shutil.rmtree(server_result_path)
        shutil.rmtree(client_data_path)
        shutil.rmtree(server_data_path)

if __name__ == '__main__':
    unittest.main(verbosity=1)

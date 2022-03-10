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
import time
import queue
import random
import threading
from functools import cmp_to_key

import mmh3

from xfl.common.common import RunMode
from xfl.common.logger import log
from xfl.data import utils
from xfl.data.check_sum import CheckSum
from xfl.data.store.sample_kv_store import DictSampleKvStore
from xfl.data.store.etcd_kv_store import EtcdSampleKvStore
from xfl.data.utils import get_sample_store_key, split_sample_store_key
from xfl.service.data_join_client import create_data_join_client
from xfl.data.tfreecord.tfreecord import RecordReader, RecordWriter

class DefaultKeySelector:
    def __init__(self, bucket_num: int = 64):
        self._bucket_num = bucket_num

    def get_key(self, value):
        return mmh3.hash(value[0]) % self._bucket_num


SAMPLE_STORE_TYPE = {
    "memory": DictSampleKvStore,
    "etcd": EtcdSampleKvStore
}


def record_cmp(left, right):
    a = split_sample_store_key(left)
    b = split_sample_store_key(right)
    if a[1] < b[1]:
        return -1
    if a[1] > b[1]:
        return 1
    if a[0] < b[0]:
        return -1
    if a[0] > b[0]:
        return 1
    return 0


def getKeyBytes(feature):
    if feature is None:
        raise RuntimeError("Null feature Input")
    if feature.bytes_list.value:
        return feature.bytes_list.value[0]
    elif feature.int64_list.value:
        return bytes(str(feature.int64_list.value[0]), 'utf-8')
    elif feature.float_list.value:
        return bytes(str(feature.float_list.value[0]), 'utf-8')
    else:
        raise RuntimeError("Feature Type Error!")


def get_value_from_example(example, hash_col_name, sort_col_name):
    return getKeyBytes(example.features.feature[hash_col_name]), getKeyBytes(example.features.feature[sort_col_name])


class ClientSortJoinFunc_local(object):
    def __init__(
            self,
            job_name: str,
            peer_host: str,
            peer_ip: str,
            peer_port: int,
            bucket_num: int = 64,
            cmp_func=record_cmp,
            sample_store_cls=DictSampleKvStore,
            batch_size: int = 2048,
            wait_s: int = 1800,
            tls_crt: str = '',
            run_mode: RunMode = RunMode.LOCAL,
            output_bucket_file='',
            bucket_id=0,
            hash_col_name='',
            sort_col_name=''):
        self._job_name = job_name
        self._bucket_num = bucket_num
        self._state = None
        self._delay = 10000
        self._cmp_func = cmp_func
        self._sample_store_cls = sample_store_cls
        self._peer_host = peer_host
        self._peer_ip = peer_ip
        self._peer_port = peer_port
        self._batch_size = batch_size
        self._run_mode = run_mode
        self._wait_s = wait_s
        self._tls_crt = tls_crt
        self._output_bucket_file = output_bucket_file
        self._bucket_id = bucket_id
        self._hash_col_name = hash_col_name
        self._sort_col_name = sort_col_name

        if self._sample_store_cls is DictSampleKvStore:
            self._sample_store = DictSampleKvStore()
        else:
            raise RuntimeError("sample_store_cls is not supported by now{}".format(self._sample_store_cls))

        self.cnt = 0

    def data_join_client_bucket_file(self, bucket_dir_path):
        tf_reader = RecordReader()
        tf_writer = RecordWriter()
        for now_path, subfolder, files in os.walk(bucket_dir_path):
            for filename in files:
                bucket_file_path = os.path.join(now_path, filename)
                raw_dataset = tf_reader.read_from_tfrecord(bucket_file_path)

                for raw_record in raw_dataset:
                    example = tf_reader.example
                    example.ParseFromString(raw_record)
                    value0, value1 = get_value_from_example(example, self._hash_col_name, self._sort_col_name)
                    value = (value0, value1, raw_record)
                    self._sample_store.put(get_sample_store_key(value[0], value[1]), value[2])
                    self.cnt += 1

        log.info("")
        keys_to_join = sorted(self._sample_store.keys(), key=cmp_to_key(self._cmp_func))
        if self._run_mode == RunMode.K8S:
            if self._tls_crt is None or len(self._tls_crt) == 0:
                raise RuntimeError("tls crt should not be empty in k8s mode client job!")
        client_port = self._peer_port
        if self._run_mode == RunMode.LOCAL:
            client_port = client_port + self._bucket_id
        client = create_data_join_client(host=self._peer_host,
                                         ip=self._peer_ip,
                                         port=client_port,
                                         job_name=self._job_name,
                                         bucket_id=self._bucket_id,
                                         run_mode=self._run_mode,
                                         tls_crt=self._tls_crt)
        check_sum = CheckSum()
        client.wait_ready(timeout=self._wait_s)
        log.info(
            "Client begin to join, bucket id:{}, all size:{}, unique size:{}".format(self._bucket_id, self.cnt,
                                                                                     len(keys_to_join)))
        cur = 0
        while cur < len(keys_to_join):
            end = min(cur + self._batch_size, len(keys_to_join))
            request_ids = keys_to_join[cur:end]
            existence = client.sync_join(request_ids)
            res_ids = utils.gather_res(request_ids, existence=existence)
            check_sum.add_list(res_ids)
            cur = end
            for i in res_ids:
                self._output_bucket_file.write(tf_writer.encode_example(self._sample_store.get(i)))
            log.info("client sync join current idx: {}, all: {}".format(cur, len(keys_to_join)))
        log.info("End join, checkSum:{}".format(check_sum.get_check_sum()))
        res = client.finish_join(check_sum.get_check_sum())
        self._sample_store.clear()
        if not res:
            raise ValueError("Join finish error")


class data_join_pipeline_local_no_tf(object):
    def __init__(self,
                 input_path: str,
                 output_path: str,
                 job_name: str,
                 host: str,
                 port: int,
                 ip: str,
                 bucket_num: int,
                 run_mode: str,
                 hash_col_name: str,
                 sort_col_name: str,
                 is_server: bool,
                 sample_store_type: str,
                 batch_size: int,
                 file_part_size: int,
                 tls_crt_path: str,
                 rsa_pub_path: str,
                 rsa_pri_path: str,
                 wait_s: int = 1800,
                 use_psi: bool = False,
                 need_sort: bool = False,
                 inputfile_type: str = 'tfrecord',
                 conf: dict = {}):
        self._input_path = input_path
        self._output_path = output_path
        self._job_name = job_name
        self._bucket_num = bucket_num
        self._state = None
        self._delay = 10000
        self._sample_store_cls = SAMPLE_STORE_TYPE[sample_store_type]
        self._peer_host = host
        self._peer_ip = ip
        self._peer_port = port
        self._batch_size = batch_size
        self._run_mode = RunMode(run_mode)
        self._hash_col_name = hash_col_name
        self._sort_col_name = sort_col_name
        self._wait_s = wait_s
        self._bucket_path = os.path.join(self._output_path, 'tmp_bucket')
        self._DefaultKeySelector = DefaultKeySelector(bucket_num=bucket_num)

        self._data_to_bucket_threads_num = self._bucket_num
        self._data_to_bucket_file_list_sum = []
        self._data_to_bucket_file_name = "{}_{}.tfrecords"
        self._data_to_bucket_threads_queue = queue.Queue()
        self._data_to_bucket_threads_data_buffer = []
        self._data_to_bucket_now_threads = []
        self._data_to_bucket_batch_size = batch_size

        tls_crt = b''
        if tls_crt_path is not None:
            with open(tls_crt_path, 'rb') as f:
                tls_crt = f.read()
                log.info("tls path:{} \n tls value:{}".format(tls_crt_path, tls_crt))
        self._tls_crt = tls_crt

    def read_buffer_data_to_bucket(self, thread_id):
        tf_reader = RecordReader()
        tf_writer = RecordWriter()
        for raw_record in self._data_to_bucket_threads_data_buffer[thread_id]:
            example = tf_reader.example
            example.ParseFromString(raw_record)
            value0, value1 = get_value_from_example(example, self._hash_col_name, self._sort_col_name)
            value = (value0, value1, raw_record)
            bucket_id = self._DefaultKeySelector.get_key(value)
            self._data_to_bucket_file_list_sum[thread_id][bucket_id].write(tf_writer.encode_example(example.SerializeToString()))
        self._data_to_bucket_threads_data_buffer[thread_id].clear()
        self._data_to_bucket_now_threads[thread_id] = None
        self._data_to_bucket_threads_queue.put(thread_id)

    def read_tf_record_data_to_bucket(self):
        # Multithreading preparation
        if not os.path.exists(self._bucket_path):
            os.makedirs(self._bucket_path)
        for worker in range(self._data_to_bucket_threads_num):
            _data_to_bucket_file_list = []
            for i in range(self._bucket_num):
                bucket_dir_path = os.path.join(self._bucket_path, str(i))
                if not os.path.exists(bucket_dir_path):
                    os.makedirs(bucket_dir_path)
                bucket_file_path = os.path.join(bucket_dir_path, self._data_to_bucket_file_name.format(i, worker))
                bucket_file = open(bucket_file_path, 'ab')
                _data_to_bucket_file_list.append(bucket_file)
            self._data_to_bucket_file_list_sum.append(_data_to_bucket_file_list)
            self._data_to_bucket_threads_queue.put(worker)
            self._data_to_bucket_threads_data_buffer.append([])
            self._data_to_bucket_now_threads.append(None)

        now_thread = None
        tf_reader = RecordReader()
        for now_path, subfolder, files in os.walk(self._input_path):
            for _file in files:
                filename = os.path.join(now_path, _file)
                raw_dataset_tmp = tf_reader.read_from_tfrecord(filename)
                raw_dataset = []
                for raw_record in raw_dataset_tmp:
                    raw_dataset.append(raw_record)

                size_data = len(raw_dataset)
                now_whe = 0

                while True:
                    if now_thread is None:
                        if self._data_to_bucket_threads_queue.empty():
                            time.sleep(1)
                            continue
                        now_thread = self._data_to_bucket_threads_queue.get()
                    if len(self._data_to_bucket_threads_data_buffer[now_thread]) + size_data - now_whe \
                            < self._data_to_bucket_batch_size:
                        self._data_to_bucket_threads_data_buffer[now_thread] += raw_dataset[now_whe:]
                        break
                    elif len(self._data_to_bucket_threads_data_buffer[now_thread]) + size_data - now_whe \
                            < 2 * self._data_to_bucket_batch_size:
                        self._data_to_bucket_threads_data_buffer[now_thread] += raw_dataset[now_whe:]
                        thread_worker = threading.Thread(target=self.read_buffer_data_to_bucket, args=(now_thread,))
                        self._data_to_bucket_now_threads[now_thread] = thread_worker
                        thread_worker.start()
                        now_thread = None
                        break
                    else:
                        empty_size = self._data_to_bucket_batch_size - \
                                     len(self._data_to_bucket_threads_data_buffer[now_thread])
                        self._data_to_bucket_threads_data_buffer[now_thread] += \
                            raw_dataset[now_whe:now_whe + empty_size]
                        thread_worker = threading.Thread(target=self.read_buffer_data_to_bucket, args=(now_thread,))
                        self._data_to_bucket_now_threads[now_thread] = thread_worker
                        thread_worker.start()
                        now_whe += empty_size
                        now_thread = None

        for thread_worker in self._data_to_bucket_now_threads:
            if thread_worker is not None:
                thread_worker.join()
        for _data_to_bucket_file_list in self._data_to_bucket_file_list_sum:
            for bucket_file in _data_to_bucket_file_list:
                bucket_file.close()

    def worker_for_data_join_bucket(self, bucket_id):
        bucket_dir_path = os.path.join(self._bucket_path, str(bucket_id))
        output_bucket_dir_path = os.path.join(self._output_path, str(bucket_id))
        if not os.path.exists(output_bucket_dir_path):
            os.makedirs(output_bucket_dir_path)
        output_bucket_file_path = os.path.join(output_bucket_dir_path, str(bucket_id) + '.tfrecords')
        output_bucket_file = open(output_bucket_file_path, 'ab')
        tmp_client = ClientSortJoinFunc_local(
            job_name=self._job_name,
            peer_host=self._peer_host,
            peer_ip=self._peer_ip,
            peer_port=self._peer_port,
            bucket_num=self._bucket_num,
            sample_store_cls=self._sample_store_cls,
            batch_size=self._batch_size,
            run_mode=self._run_mode,
            wait_s=self._wait_s,
            tls_crt=self._tls_crt,
            output_bucket_file=output_bucket_file,
            bucket_id=bucket_id,
            hash_col_name=self._hash_col_name,
            sort_col_name=self._sort_col_name)
        tmp_client.data_join_client_bucket_file(bucket_dir_path)
        output_bucket_file.close()

    def data_join_client_workers(self):
        threads_list = []
        for i in range(self._bucket_num):
            thread_worker = threading.Thread(target=self.worker_for_data_join_bucket, args=(i,))
            threads_list.append(thread_worker)
            thread_worker.start()

        for thread_worker in threads_list:
            thread_worker.join()

        shutil.rmtree(self._bucket_path)

    def run(self):
        self.read_tf_record_data_to_bucket()

        self.data_join_client_workers()
        return "Program execution finished"

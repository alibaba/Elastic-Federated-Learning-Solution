import os
import tensorflow as tf
import numpy as np
import shutil
import tempfile
import functools
import threading
from data_maker import make_data
from xfl.data.pipelines import data_join_pipeline

tf.enable_eager_execution()
#default file path
client_result_path = "/tmp/output/TEST_DATA_JOIN_CLI"
server_result_path = "/tmp/output/TEST_DATA_JOIN_SERVER"
client_data_path = "/tmp/input/test_data_client"
server_data_path = "/tmp/input/test_data_server"
np.random.seed(0)

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
                 host = 'localhost',
                 port = 50051,
                 ingress_ip = None,
                 batch_size = 2048,
                 file_part_size = 1024,
                 jar = 'file:///xfl/lib/efls-flink-connectors-1.0-SNAPSHOT.jar',
                 run_mode = 'local',
                 tls_crt_path = '/xfl/deploy/quickstart/tls.crt',
                 wait_s = 1800,
                 use_psi = True):
        threading.Thread.__init__(self)
        conf = {}
        conf['jars'] = jar.split(',')

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
            wait_s=wait_s,
            use_psi=use_psi,
            conf=conf)

    def run(self):
        self.pipeline.run()

def run_client_and_server():
    if os.path.exists(client_result_path):
        shutil.rmtree(client_result_path)
    if os.path.exists(server_result_path):
        shutil.rmtree(server_result_path)
    print("Server startup")
    server_thread = model_thread('TEST_DATA_JOIN_SERVER', True,
                                 server_data_path, server_result_path,
                                 'example_id', 'example_id', 8)
    print("Client startup")
    client_thread = model_thread('TEST_DATA_JOIN_CLI', False,
                                 client_data_path, client_result_path,
                                 'example_id', 'example_id', 8)

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

    print("Client result size: %d and server result size: %d" % (record_cnt_cli, record_cnt_cli))
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

        if get_error == False:
            print("No error")
        print("data repeat %d times in client" % cnt1)
        print("data repeat %d times in server" % cnt2)

data_common = make_data()
run_client_and_server()
result_judge(data_common)

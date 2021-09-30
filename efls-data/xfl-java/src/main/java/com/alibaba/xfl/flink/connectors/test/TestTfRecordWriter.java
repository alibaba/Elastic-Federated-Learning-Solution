/* Copyright 2020 Alibaba Group Holding Limited. All Rights Reserved.
Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
==============================================================================*/

package com.alibaba.xfl.flink.connectors.test;

import org.tensorflow.example.Example;
import org.tensorflow.hadoop.util.TFRecordReader;
import org.tensorflow.hadoop.util.TFRecordWriter;

import java.io.*;

public class TestTfRecordWriter {
    public File tempfile;
    public TFRecordWriter writer;

    public TFRecordWriter createTempWriter() throws IOException {
        File tempfile = File.createTempFile("test","rd");
        FileOutputStream out = new FileOutputStream(tempfile);
        DataOutputStream dataOutputStream = new DataOutputStream(out);
        TFRecordWriter writer = new TFRecordWriter(dataOutputStream);
        this.tempfile = tempfile;
        this.writer = writer;
        return writer;
    }
    public static void main(String[] args) throws IOException {
        TestTfRecordWriter test = new TestTfRecordWriter();
        TFRecordWriter writer = test.createTempWriter();

        FileInputStream inputStream = new FileInputStream(args[0]);
        TFRecordReader tfReader = new TFRecordReader(inputStream, true);
        int recordCnt = 0;
        while(true) {
            try {
                byte[] data = tfReader.read();
                if(data == null) {
                    System.out.println("read end!");
                    break;
                }
                Example example = Example.parseFrom(data);
                recordCnt++;
                writer.write(data);
            } catch (IOException e) {
                e.printStackTrace();
                throw e;
            }
        }

        System.out.println("read raw data len:" + recordCnt);

        inputStream = new FileInputStream(test.tempfile);
        tfReader = new TFRecordReader(inputStream, true);
        int recordCnt2 = 0;
        while(true) {
            try {
                byte[] data = tfReader.read();
                if(data == null) {
                    System.out.println("read end!");
                    break;
                }
                Example example = Example.parseFrom(data);
                recordCnt2++;
            } catch (IOException e) {
                e.printStackTrace();
                throw e;
            }
        }
        System.out.println("read temp data len:" + recordCnt2);
        assert recordCnt == recordCnt2;

    }
}

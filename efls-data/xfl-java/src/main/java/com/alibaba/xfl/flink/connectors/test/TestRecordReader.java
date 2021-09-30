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
import org.tensorflow.example.Feature;
import org.tensorflow.hadoop.util.TFRecordReader;

import java.io.FileInputStream;
import java.io.IOException;
import java.util.Map;

public class TestRecordReader {
    public static void main(String[] args) throws IOException {
        FileInputStream inputStream = new FileInputStream(args[0]);
        TFRecordReader tfReader = new TFRecordReader(inputStream, true);
        int recordCnt = 1;
        while(true) {
            try {
                byte[] data = tfReader.read();
                if(data == null) {
                    System.out.println("read end!");
                    return;
                }
                Example example = Example.parseFrom(data);
                Map<String, Feature> featureMap = example.getFeatures().getFeatureMap();
                System.out.println((recordCnt++) + ": feature:" + featureMap);
            } catch (IOException e) {
                e.printStackTrace();
                throw e;
            }
        }

    }
}

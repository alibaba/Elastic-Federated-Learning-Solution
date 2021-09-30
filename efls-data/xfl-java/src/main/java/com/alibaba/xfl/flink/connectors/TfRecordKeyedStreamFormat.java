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

package com.alibaba.xfl.flink.connectors;

import org.apache.flink.api.common.typeinfo.TypeHint;
import org.apache.flink.api.common.typeinfo.TypeInformation;
import org.apache.flink.api.java.tuple.Tuple3;
import org.apache.flink.configuration.Configuration;
import org.apache.flink.connector.file.src.reader.SimpleStreamFormat;
import org.apache.flink.connector.file.src.reader.StreamFormat;
import org.apache.flink.core.fs.FSDataInputStream;
import org.tensorflow.example.Example;
import org.tensorflow.example.Feature;
import org.tensorflow.hadoop.util.TFRecordReader;

import javax.annotation.Nullable;
import java.io.BufferedInputStream;
import java.io.IOException;
import java.io.InputStream;
import java.util.Map;

/**
 * parse tf record file, and extract hashkey and sortkey, so that downstream tasks
 * will not need to parse record again.
 */
public class TfRecordKeyedStreamFormat extends SimpleStreamFormat<Tuple3<byte[], byte[], byte[]>> {
    private final long serialVersionUID = 1L;
    private int bufferSize = 4096;
    private boolean crcCheck = true;
    private final String hashKeyName;
    private final String sortKeyName;

    public TfRecordKeyedStreamFormat(int bufferSize, boolean crcCheck, String hashKeyName, String sortKeyName) {
        this.bufferSize = bufferSize;
        this.crcCheck = crcCheck;
        this.hashKeyName = hashKeyName;
        this.sortKeyName = sortKeyName;
    }

    private static final class Reader implements StreamFormat.Reader<Tuple3<byte[], byte[], byte[]>> {
        private final TFRecordReader tfReader;
        private final InputStream stream_internal;
        private final String hashKeyName;
        private final String sortKeyName;

        Reader(TFRecordReader tfReader, InputStream inputStream, String hashKeyName, String sortKeyName) {
            this.tfReader = tfReader;
            stream_internal = inputStream;
            this.hashKeyName = hashKeyName;
            this.sortKeyName = sortKeyName;
        }

        /**
         *
         * @return hashkey, sortkey, value
         * @throws IOException
         */
        @Override
        @Nullable
        public Tuple3<byte[], byte[], byte[]> read() throws IOException {
            byte[] data = tfReader.read();
            if(data == null) {
                return null;
            }
            try {
                Example example = Example.parseFrom(data);
                Map<String, Feature> featureMap = example.getFeatures().getFeatureMap();
                return Tuple3.of(Utils.getKeyBytes(featureMap.get(hashKeyName)),
                        Utils.getKeyBytes(featureMap.get(sortKeyName)),
                        data);
            } catch (Exception e) {
                return null;
            }
        }

        @Override
        public void close() throws IOException {
            stream_internal.close();
        }
    }


    @Override
    public StreamFormat.Reader<Tuple3<byte[], byte[], byte[]>> createReader(Configuration configuration, FSDataInputStream fsDataInputStream) throws IOException {
        BufferedInputStream bufferedStream = new BufferedInputStream(fsDataInputStream, bufferSize);
        Reader reader = new Reader(new TFRecordReader(fsDataInputStream, crcCheck), bufferedStream, hashKeyName, sortKeyName);
        return reader;
    }

    @Override
    public TypeInformation<Tuple3<byte[], byte[], byte[]>> getProducedType() {
       return TypeInformation.of(new TypeHint<Tuple3<byte[], byte[], byte[]>>() {});
    }
}

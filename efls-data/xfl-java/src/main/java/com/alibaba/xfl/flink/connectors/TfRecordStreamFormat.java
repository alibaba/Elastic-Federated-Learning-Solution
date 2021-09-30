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

import org.apache.flink.api.common.typeinfo.PrimitiveArrayTypeInfo;
import org.apache.flink.api.common.typeinfo.TypeInformation;
import org.apache.flink.configuration.Configuration;
import org.apache.flink.connector.file.src.reader.SimpleStreamFormat;
import org.apache.flink.connector.file.src.reader.StreamFormat;
import org.apache.flink.core.fs.FSDataInputStream;
import org.tensorflow.hadoop.util.TFRecordReader;

import javax.annotation.Nullable;
import java.io.BufferedInputStream;
import java.io.IOException;
import java.io.InputStream;

public class TfRecordStreamFormat extends SimpleStreamFormat<byte[]> {
    private final long serialVersionUID = 1L;
    private int bufferSize = 4096;
    private boolean crcCheck = true;
    public TfRecordStreamFormat(int bufferSize, boolean crcCheck) {
        this.bufferSize = bufferSize;
        this.crcCheck = crcCheck;
    }

    private static final class Reader implements org.apache.flink.connector.file.src.reader.StreamFormat.Reader<byte[]> {
        private final TFRecordReader tfReader;
        private final InputStream stream_internal;

        Reader(TFRecordReader tfReader, InputStream inputStream) {
            this.tfReader = tfReader;
            stream_internal = inputStream;
        }

        @Override
        @Nullable
        public byte[] read() throws IOException {
            return tfReader.read();
        }

        @Override
        public void close() throws IOException {
            stream_internal.close();
        }
    }


    @Override
    public StreamFormat.Reader<byte[]> createReader(Configuration configuration, FSDataInputStream fsDataInputStream) throws IOException {
        BufferedInputStream bufferedStream = new BufferedInputStream(fsDataInputStream, bufferSize);
        Reader reader = new Reader(new TFRecordReader(fsDataInputStream, crcCheck), bufferedStream);
        return reader;
    }

    @Override
    public TypeInformation<byte[]> getProducedType() {
        return PrimitiveArrayTypeInfo.BYTE_PRIMITIVE_ARRAY_TYPE_INFO;
    }
}

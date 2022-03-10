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

import javax.annotation.Nullable;
import java.io.BufferedInputStream;
import java.io.InputStreamReader;
import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStream;

/**
 * read csv file, and extract hashkey and sortkey
 */
public class CsvKeyedStreamFormat extends SimpleStreamFormat<Tuple3<byte[], byte[], byte[]>> {
    private final long serialVersionUID = 1L;
    private int bufferSize = 4096;
    private final String hashKeyName;
    private final String sortKeyName;

    public CsvKeyedStreamFormat(int bufferSize, String hashKeyName, String sortKeyName) {
        this.bufferSize = bufferSize;
        this.hashKeyName = hashKeyName;
        this.sortKeyName = sortKeyName;
    }

    private static final class Reader implements StreamFormat.Reader<Tuple3<byte[], byte[], byte[]>> {
        private final BufferedReader CsvReader;
        private final InputStream stream_internal;
        private final String hashKeyName;
        private final String sortKeyName;
        private boolean is_key_inited;        
        private int hashKeyId, sortKeyId;      
        private String[] key_list;      
        
        Reader(BufferedReader CsvReader, InputStream inputStream, String hashKeyName, String sortKeyName) {
            this.CsvReader = CsvReader;
            stream_internal = inputStream;
            this.hashKeyName = hashKeyName;
            this.sortKeyName = sortKeyName;
            this.is_key_inited = false;
        }

        /**
         *
         * @return hashkey, sortkey, value
         * @throws IOException
         */
        @Override
        @Nullable
        public Tuple3<byte[], byte[], byte[]> read() throws IOException {
            if (is_key_inited == false) {
                is_key_inited = true;
                key_list = CsvReader.readLine().split(","); 
                for (int i = 0,len = key_list.length;i < len;i++) {
                    if (key_list[i].equals(hashKeyName))
                        hashKeyId = i;
                    if (key_list[i].equals(sortKeyName))
                        sortKeyId = i; 
                }
            }
            String data = CsvReader.readLine();
            if(data == null) {
                return null;
            }
            try {
                String item[] = data.split(",");
                return Tuple3.of(item[hashKeyId].getBytes("utf-8"),
                        item[sortKeyId].getBytes("utf-8"),
                        data.getBytes("utf-8"));
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
        Reader reader = new Reader(new BufferedReader(new InputStreamReader(fsDataInputStream)), bufferedStream, hashKeyName, sortKeyName);
        return reader;
    }

    @Override
    public TypeInformation<Tuple3<byte[], byte[], byte[]>> getProducedType() {
       return TypeInformation.of(new TypeHint<Tuple3<byte[], byte[], byte[]>>() {});
    }
}

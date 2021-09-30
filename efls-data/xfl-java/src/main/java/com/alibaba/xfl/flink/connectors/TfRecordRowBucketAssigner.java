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

import org.apache.flink.core.io.SimpleVersionedSerializer;
import org.apache.flink.streaming.api.functions.sink.filesystem.BucketAssigner;
import org.apache.flink.streaming.api.functions.sink.filesystem.bucketassigners.SimpleVersionedStringSerializer;
import org.apache.flink.types.Row;
import org.tensorflow.example.Example;
import org.tensorflow.example.Feature;

import java.nio.charset.StandardCharsets;

public class TfRecordRowBucketAssigner implements BucketAssigner<Row, String> {

    private final int bucketIdx;

    public TfRecordRowBucketAssigner(){
        this(0);
    }
    public TfRecordRowBucketAssigner(int bucketIdx) {
        this.bucketIdx = bucketIdx;
    }

    /**
     * 生成tf格式数据分桶，输入是一个flink row， 某列为桶号。
     * @param in
     * @param context
     * @return 分桶结果
     */
    @Override
    public String getBucketId(Row in, Context context) {
        Object value = in.getField(bucketIdx);
        try {
            if (value instanceof byte[]) {
                return new String((byte[]) value);
            } else {
                return value.toString();
            }
        } catch (Exception e) {
            e.printStackTrace();
            return "parse_error_bucket";
        }

    }

    @Override
    public SimpleVersionedSerializer<String> getSerializer() {
        return SimpleVersionedStringSerializer.INSTANCE;
    }

}

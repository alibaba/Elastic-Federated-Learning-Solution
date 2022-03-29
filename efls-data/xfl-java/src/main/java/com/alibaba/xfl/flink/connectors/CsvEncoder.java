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

import org.apache.flink.api.common.serialization.Encoder;
import org.apache.flink.types.Row;

import java.io.OutputStreamWriter;
import java.io.BufferedWriter;
import java.io.IOException;
import java.io.OutputStream;

public class CsvEncoder implements Encoder<Row> {

    private final int valueIdx;
    private BufferedWriter writer;

    public CsvEncoder() {
        this(0);
    }
    public CsvEncoder(int valueIdx) {
        this.valueIdx = valueIdx;
    }

    /**
     *
     * @param row
     * @param outputStream
     * @throws IOException
     */
    @Override
    public void encode(Row row, OutputStream outputStream) throws IOException {
        writer = new BufferedWriter(new OutputStreamWriter(outputStream));
        writer.write(row.getField(valueIdx).toString());
        writer.flush();
    }
}

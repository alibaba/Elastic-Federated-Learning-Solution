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

import org.tensorflow.example.Feature;

import java.io.UnsupportedEncodingException;

public class Utils {
    public static byte[] getKeyBytes(Feature feature) throws UnsupportedEncodingException {
        if(feature == null) {
            throw new IllegalArgumentException("Null feature Input");
        }
        if (feature.hasBytesList()) {
            return feature.getBytesList().getValue(0).toByteArray();
        } else if (feature.hasFloatList()) {
            return String.valueOf(feature.getFloatList().getValue(0)).getBytes("utf-8");
        } else if (feature.hasInt64List()) {
            return String.valueOf(feature.getInt64List().getValue(0)).getBytes("utf-8");
        } else {
            throw new IllegalArgumentException("Feature Type Error!");
        }
    }
}

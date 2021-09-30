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

import org.apache.flink.streaming.api.functions.sink.filesystem.PartFileInfo;
import org.apache.flink.streaming.api.functions.sink.filesystem.RollingPolicy;
import org.apache.flink.streaming.api.functions.sink.filesystem.rollingpolicies.DefaultRollingPolicy;
import org.apache.flink.util.Preconditions;

import java.io.IOException;

public class RowNumberRollingPolicy <IN, BucketID> implements RollingPolicy<IN, BucketID> {

    private final int rowNumberToRoll;
    private int curRowNumber;

    public RowNumberRollingPolicy(int rowNumberToRoll) {
        this.rowNumberToRoll = rowNumberToRoll;
        this.curRowNumber = 0;
    }

    @Override
    public boolean shouldRollOnCheckpoint(PartFileInfo<BucketID> partFileInfo) throws IOException {
        return false;
    }

    @Override
    public boolean shouldRollOnEvent(PartFileInfo<BucketID> partFileInfo, IN in) throws IOException {
        if(++curRowNumber == rowNumberToRoll){
            curRowNumber = 0;
            return true;
        }
        return false;
    }

    @Override
    public boolean shouldRollOnProcessingTime(PartFileInfo<BucketID> partFileInfo, long l) throws IOException {
        return false;
    }

    public static RowNumberRollingPolicy.PolicyBuilder builder() {
        return new RowNumberRollingPolicy.PolicyBuilder(10240);
    }

    public static final class PolicyBuilder {

        private final int rowNumberToRoll;

        private PolicyBuilder(int rowNumberToRoll) {
            this.rowNumberToRoll = rowNumberToRoll;
        }
        public RowNumberRollingPolicy.PolicyBuilder withRowNumber(int rowNumberToRoll) {
            Preconditions.checkState(rowNumberToRoll > 0);
            return new RowNumberRollingPolicy.PolicyBuilder(rowNumberToRoll);
        }
        public <IN, BucketID> RowNumberRollingPolicy<IN, BucketID> build() {
            return new RowNumberRollingPolicy(this.rowNumberToRoll);
        }
    }
}

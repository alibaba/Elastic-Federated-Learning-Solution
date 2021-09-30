/*
 * Licensed to the Apache Software Foundation (ASF) under one or more
 * contributor license agreements.  See the NOTICE file distributed with
 * this work for additional information regarding copyright ownership.
 * The ASF licenses this file to You under the Apache License, Version 2.0
 * (the "License"); you may not use this file except in compliance with
 * the License.  You may obtain a copy of the License at
 *
 *    http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

package org.apache.flink.streaming.runtime.partitioner;

import org.apache.flink.annotation.Internal;
import org.apache.flink.api.java.functions.KeySelector;
import org.apache.flink.runtime.io.network.api.writer.SubtaskStateMapper;
import org.apache.flink.runtime.plugable.SerializationDelegate;
import org.apache.flink.runtime.state.KeyGroupRangeAssignment;
import org.apache.flink.streaming.runtime.streamrecord.StreamRecord;
import org.apache.flink.types.Row;
import org.apache.flink.util.Preconditions;

import java.io.Serializable;
import java.util.Objects;

/**
 * Partitioner selects the target channel based on the key group index.
 *
 * @param <T> Type of the elements in the Stream being partitioned
 */
@Internal
public class KeyGroupStreamPartitioner<T, K> extends StreamPartitioner<T>
        implements ConfigurableStreamPartitioner {
    private static final long serialVersionUID = 2L;

    private final KeySelector<T, K> keySelector;

    private final KeyToParallelOperatorIndex assigner;

    private int maxParallelism;

    @FunctionalInterface
    interface KeyToParallelOperatorIndex extends Serializable {
        int apply(Object key, int maxParallelism, int parallelism);
    }

    public KeyGroupStreamPartitioner(KeySelector<T, K> keySelector, int maxParallelism) {
        Preconditions.checkArgument(maxParallelism > 0, "Number of key-groups must be > 0!");
        this.keySelector = Preconditions.checkNotNull(keySelector);
        this.maxParallelism = maxParallelism;

        // Data join for Elastic Federated Learning need to use Operator State,
        // but it is not supported in Python DataStream API until flink-1.13, so we let
        // keySelector return channel index to make Keyed State equivalent to Operate State
        final String pyKeySelectorClass =
                "org.apache.flink.streaming.api.functions.python.KeyByKeySelector";
        if (pyKeySelectorClass.equals(keySelector.getClass().getName())) {
            assigner = (key, maxParallelism1, parallelism) -> {
                int index = (int) ((Row) key).getField(0);
                if (index >= maxParallelism1) {
                    throw new IllegalStateException("KeySelector return value out of bound");
                }
                return index;
            };
        } else {
            assigner = KeyGroupRangeAssignment::assignKeyToParallelOperator;
        }
    }

    public int getMaxParallelism() {
        return maxParallelism;
    }

    @Override
    public int selectChannel(SerializationDelegate<StreamRecord<T>> record) {
        K key;
        try {
            key = keySelector.getKey(record.getInstance().getValue());
        } catch (Exception e) {
            throw new RuntimeException(
                    "Could not extract key from " + record.getInstance().getValue(), e);
        }
        return assigner.apply(key, maxParallelism, numberOfChannels);
    }

    @Override
    public SubtaskStateMapper getDownstreamSubtaskStateMapper() {
        return SubtaskStateMapper.RANGE;
    }

    @Override
    public StreamPartitioner<T> copy() {
        return this;
    }

    @Override
    public boolean isPointwise() {
        return false;
    }

    @Override
    public String toString() {
        return "HASH";
    }

    @Override
    public void configure(int maxParallelism) {
        KeyGroupRangeAssignment.checkParallelismPreconditions(maxParallelism);
        this.maxParallelism = maxParallelism;
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) {
            return true;
        }
        if (o == null || getClass() != o.getClass()) {
            return false;
        }
        if (!super.equals(o)) {
            return false;
        }
        final KeyGroupStreamPartitioner<?, ?> that = (KeyGroupStreamPartitioner<?, ?>) o;
        return maxParallelism == that.maxParallelism && keySelector.equals(that.keySelector);
    }

    @Override
    public int hashCode() {
        return Objects.hash(super.hashCode(), keySelector, maxParallelism);
    }
}

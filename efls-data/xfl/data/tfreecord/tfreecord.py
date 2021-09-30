# Reference from https://github.com/Wikidepia/tfreecord/
#
# MIT License   Copyright (c) 2021 Muhammad Naswan Izzudin Akmal
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

# Change made to the origin file:
# - Motify the return val of RecordReader.read_from_tfrecord and parameter of
# RecordWriter.encode_example
#
# Copyright (C) 2016-2021 Alibaba Group Holding Limited
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ==============================================================================

import struct
import warnings

import crc32c
import numpy as np

from xfl.data.tfreecord import tfrecords_pb2

kmask_delta = 0xA282EAD8


def mask_crc(crc):
    return (((crc >> 15) | (crc << 17)) + kmask_delta) & 0xFFFFFFFF


class RecordReader:
    def __init__(self):
        self.example = tfrecords_pb2.Example()

    def decode_example(self, buffer):
        ret = {}
        self.example.ParseFromString(buffer)
        for name in self.example.features.feature:
            feature = self.example.features.feature[name]
            if len(feature.bytes_list.value) > 0:
                ret[name] = feature.bytes_list.value
            elif len(feature.int64_list.value) > 0:
                ret[name] = np.asarray(list(feature.int64_list.value), dtype=np.int64)
            elif len(feature.float_list.value) > 0:
                ret[name] = np.asarray(list(feature.float_list.value), dtype=np.float32)
        return ret

    # From https://github.com/jongwook/tfrecord_lite
    def read_from_tfrecord(self, filename, skip_error=False):
        i = 0
        with open(filename, "rb") as file_handle:
            while True:
                # Read the header
                header_str = file_handle.read(8)
                if len(header_str) != 8:
                    # Hit EOF so exit
                    break
                header = struct.unpack("Q", header_str)

                # Read the crc32, which is 4 bytes, and disregard
                crc_header_bytes = file_handle.read(4)
                crc_header = struct.unpack("I", crc_header_bytes)

                # Verify header with crc32 header
                if mask_crc(crc32c.crc32c(header_str)) != crc_header[0]:
                    if skip_error:
                        warnings.warn(f"corrupted record at {i}")
                    else:
                        raise ValueError(f"corrupted record at {i}")

                # The length of the header tells us how many bytes the Event
                # string takes
                header_len = int(header[0])
                event_bytes = file_handle.read(header_len)

                # The next 4 bytes contain the crc32 of the Event string,
                # which we check for integrity. Sometimes, the last Event
                # has no crc32, in which case we skip.
                crc_event_bytes = file_handle.read(4)
                crc_event = struct.unpack("I", crc_event_bytes)

                # Verify event with crc32 event
                if mask_crc(crc32c.crc32c(event_bytes)) != crc_event[0]:
                    if skip_error:
                        warnings.warn(f"corrupted record at {i}")
                    else:
                        raise ValueError(f"corrupted record at {i}")
                i += 1
                yield event_bytes


class RecordWriter:
    def __init__(self):
        self.example = tfrecords_pb2.Example
        self.feature = tfrecords_pb2.Feature

    def bytes_feature(self, values):
        if not isinstance(values, (tuple, list)):
            values = [values]
        return self.feature(bytes_list=tfrecords_pb2.BytesList(value=values))

    def int64_feature(self, values):
        if not isinstance(values, (tuple, list)):
            values = [values]
        return self.feature(int64_list=tfrecords_pb2.Int64List(value=values))

    def float_feature(self, values):
        if not isinstance(values, (tuple, list)):
            values = [values]
        return self.feature(float_list=tfrecords_pb2.FloatList(value=values))

    def encode_example(self, data):
        # Calculate data size
        data_len = struct.pack("Q", len(data))

        # Calculate data size crc
        len_crc = mask_crc(crc32c.crc32c(data_len))
        len_crc = struct.pack("I", len_crc)

        # Calculate data crc
        data_crc = mask_crc(crc32c.crc32c(data))
        data_crc = struct.pack("I", data_crc)

        # Append everything
        # Following record_writer.cc
        return (data_len + len_crc) + data + (data_crc)

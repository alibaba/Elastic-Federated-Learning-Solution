# Copyright 2021 Alibaba Group Holding Limited. All Rights Reserved.
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
from enum import Enum
from socket import socket

import grpc

from xfl.common.logger import log


class ChannelType(Enum):
  INTERNAL = 0
  REMOTE = 1


def check_address_valid(address):
  try:
    (ip, port_str) = address.split(':')
    if ip == 'localhost' or (socket.inet_aton(ip) and ip.count('.') == 3):
      port = int(port_str)
      if 0 <= port <= 65535:
        return True
    return False
  except Exception as e:  # pylint: disable=broad-except
    log.debug('%s is not valid address. detail is %s.', address,
              repr(e))
  return False


def get_insecure_channel(address: str,
                         mode=ChannelType.INTERNAL,
                         options: list = [],
                         compression=None):
  if mode == ChannelType.INTERNAL:
    if check_address_valid(address):
      return grpc.insecure_channel(address, options, compression)
    else:
      raise ValueError("address error: %s" % address)

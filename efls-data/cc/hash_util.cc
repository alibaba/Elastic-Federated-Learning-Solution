/* Copyright 2021 Alibaba Group Holding Limited. All Rights Reserved.

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

#include "hash_util.h"
#include "openssl/sha.h"

namespace efls {
  std::string Sha256(const std::string& item) {
    unsigned char sha_bytes[SHA256_DIGEST_LENGTH];
    SHA256_CTX sha256;
    SHA256_Init(&sha256);
    SHA256_Update(&sha256, item.data(), item.length());
    SHA256_Final(sha_bytes, &sha256);
    std::string ret(SHA256_DIGEST_LENGTH, '\0');
    std::copy(sha_bytes, sha_bytes + SHA256_DIGEST_LENGTH, ret.data());
    return ret;
  }
}

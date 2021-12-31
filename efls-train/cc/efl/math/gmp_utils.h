/* Copyright (C) 2016-2021 Alibaba Group Holding Limited

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

#ifndef EFL_GMP_UTILS_H_
#define EFL_GMP_UTILS_H_

#include <gmp.h>
#include "tensorflow/core/framework/types.h"

#define FBPOWM_MAX_TABLE_MEM (1ULL << 40)

namespace tensorflow {
namespace efl {

void mpz_set_ull(mpz_t rop, unsigned long long ull);

unsigned long long mpz_get_ull(mpz_t op);

void mpz_set_sll(mpz_t rop, long long sll);

long long mpz_get_sll(mpz_t op);

class FixedBasePowm {
 public:
  FixedBasePowm();
  ~FixedBasePowm();
  int init_table(mpz_t base, mpz_t mod, unsigned int exp_size, unsigned int group_size);
  void clear_table();
  int mpz_fbpowm(mpz_t rop, mpz_t op);

 private:
  unsigned int group_size_ = 0;
  unsigned int exp_size_ = 0;
  mpz_t base_;
  mpz_t mod_;
  mpz_t* table_ = nullptr;
};

void mpz_get_cxx_str(string& str, int base, mpz_t op);

} // efl
} // tensorflow

#endif // EFL_GMP_UTILS_H_

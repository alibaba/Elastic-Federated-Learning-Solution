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
#include "stdlib.h"
#include "gmp_utils.h"

namespace tensorflow {
namespace efl {

void mpz_set_ull(mpz_t rop, unsigned long long ull) {
  mpz_import(rop, 1, -1, sizeof(unsigned long long), 0, 0, &ull);
}

unsigned long long mpz_get_ull(mpz_t op) {
  unsigned long long result = 0; 
  mpz_export(&result, 0, -1, sizeof(unsigned long long), 0, 0, op);
  return result;
}

void mpz_set_sll(mpz_t rop, long long sll) {
  if (sll < 0) {
    mpz_set_ull(rop, -sll);
    mpz_neg(rop, rop);
  } else {
    mpz_set_ull(rop, sll);
  }
}

long long mpz_get_sll(mpz_t op) {
  auto res = (long long)mpz_get_ull(op);
  if (mpz_sgn(op) < 0) {
    return -res;
  } else {
    return res;
  }
}

FixedBasePowm::FixedBasePowm() {
  mpz_inits(base_, mod_, NULL);
}

FixedBasePowm::~FixedBasePowm() {
  mpz_clears(base_, mod_, NULL);
  clear_table();
}

int FixedBasePowm::init_table(mpz_t base, mpz_t mod, unsigned int exp_size, unsigned int group_size) {
  if (table_) {
    return 0;
  }
  mpz_set(base_, base);
  mpz_set(mod_, mod);
  group_size_ = group_size;
  exp_size_ = exp_size;
  unsigned long long col = (1 << group_size_) - 1;
  auto row = exp_size_ / group_size_;
  if (exp_size_ % group_size_) {
    row++;
  }
  auto table_size = row * col;
  auto element_size = mpz_sizeinbase(mod_, 2);
  if (table_size * element_size > FBPOWM_MAX_TABLE_MEM) {
    return -1;
  }
  table_ = new mpz_t[table_size];
  for (auto i = 0ULL; i < table_size; ++i) {
    mpz_init(table_[i]);
  }
  mpz_set(table_[0], base_);
  for (auto i = 1ULL; i < col; ++i) {
    mpz_mul(table_[i], table_[i - 1], base_);
    mpz_mod(table_[i], table_[i], mod_);
  }
  for (auto i = 1U; i < row; ++i) {
    for (auto j = 0ULL; j < col; ++j) {
      mpz_powm_ui(table_[i * col + j], table_[(i - 1) * col + j], 1 << group_size_, mod_);
    }
  }
  return 1;
}

void FixedBasePowm::clear_table() {
  if (table_) {
    unsigned long long col = (1 << group_size_) - 1;
    auto row = exp_size_ / group_size_;
    if (exp_size_ % group_size_) {
      row++;
    }
    auto table_size = row * col;
    for (auto i = 0ULL; i < table_size; ++i) {
      mpz_clear(table_[i]);
    }
    delete[] table_;
    table_ = nullptr;
  }
}

int FixedBasePowm::mpz_fbpowm(mpz_t rop, mpz_t op) {
  if (!table_) {
    return 0;
  }
  auto size = mpz_sizeinbase(op, 2);
  if (size > exp_size_) {
    return -1;
  }
  mpz_t tmp;
  mpz_init_set_ui(tmp, 1);
  auto row = size / group_size_;
  unsigned long long col = (1 << group_size_) - 1;
  for (auto i = 0U; i < row; ++i) {
    auto s = i * group_size_;
    auto idx = mpz_tstbit(op, s);
    for (auto j = 1U; j < group_size_; ++j) {
      idx <<= 1;
      idx += mpz_tstbit(op, s + j);
    }
    if (idx) {
      mpz_mul(tmp, tmp, table_[i * col + --idx]);
      mpz_mod(tmp, tmp, mod_);
    }
  }
  if (size % group_size_) {
    auto i = row * group_size_;
    auto idx = mpz_tstbit(op, i);
    for (++i; i < size; ++i) {
      idx <<= 1;
      idx += mpz_tstbit(op, i);
    }
    mpz_mul(tmp, tmp, table_[row * col + --idx]);
    mpz_mod(tmp, tmp, mod_);
  }
  mpz_set(rop, tmp);
  mpz_clear(tmp);
  return 1;
}

void mpz_get_cxx_str(string& str, int base, mpz_t op) {
  char* ptr = mpz_get_str(NULL, base, op);
  str = ptr;
  delete[] ptr;
}

} // efl
} // tensorflow

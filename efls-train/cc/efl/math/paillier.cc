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
#include <time.h>
#include <gmp.h>
#include "tensorflow/core/framework/resource_mgr.h"
#include "tensorflow/core/util/work_sharder.h"

#include "gmp_utils.h"

namespace tensorflow {
namespace efl {

void mpz_l_func(mpz_t rop, mpz_t op1, mpz_t op2) {
  mpz_sub_ui(rop, op1, 1);
  mpz_divexact(rop, rop, op2);
}

void mpz_h_func(mpz_t rop, mpz_t n, mpz_t x, mpz_t x_square) {
  mpz_t g;
  mpz_init(g);
  mpz_add_ui(g, n, 1);
  mpz_sub_ui(rop, x, 1);
  mpz_powm(rop, g, rop, x_square);
  mpz_l_func(rop, rop, x);
  mpz_invert(rop, rop, x);
  mpz_clear(g);
}

void mpz_m_func(mpz_t rop, mpz_t c, mpz_t x, mpz_t x_square, mpz_t h) {
  mpz_t tmp;
  mpz_init(tmp);
  mpz_sub_ui(tmp, x, 1);
  mpz_powm(rop, c, tmp, x_square);
  mpz_l_func(rop, rop, x);
  mpz_mul(rop, rop, h);
  mpz_mod(rop, rop, x);
  mpz_clear(tmp);
}

class PaillierKeypair : public ResourceBase {
 public:
  PaillierKeypair() {
    mpz_inits(n_, n_square_, hs_, p_, q_, hp_, hq_, p_square_, q_square_, q_invert_p_, max_, NULL);
    time_t curr_time;
    time(&curr_time);
    gmp_randinit_mt(randstate_);
    gmp_randseed_ui(randstate_, curr_time);
  }

  ~PaillierKeypair() {
    mpz_clears(n_, n_square_, hs_, p_, q_, hp_, hq_, p_square_, q_square_, q_invert_p_, max_, NULL);
    gmp_randclear(randstate_);
    fbpowm_.clear_table();
  }

  string DebugString() const override {
    return "PaillierKeypair";
  }

  int SetPublicKey(const string& n, const int n_bytes, const string& hs, const int a_bytes, const int group_size) {
    mpz_set_str(n_, n.c_str(), 16);
    mpz_set_str(hs_, hs.c_str(), 16);
    mpz_mul(n_square_, n_, n_);
    n_bytes_ = n_bytes;
    a_bytes_ = a_bytes;
    mpz_mul_2exp(max_, n_, 1);
    mpz_cdiv_q_ui(max_, max_, 3);
    has_public_key_ = true;
    has_private_key_ = false;
    auto ret = fbpowm_.init_table(hs_, n_square_, a_bytes_ << 3, group_size);
    if (!ret) {
      fbpowm_.clear_table();
      ret = fbpowm_.init_table(hs_, n_square_, a_bytes_ << 3, group_size);
    }
    return ret;
  }

  int SetPrivateKey(const string& p, const string& q) {
    if (!has_public_key_) {
      return 1;
    }
    mpz_set_str(p_, p.c_str(), 16);
    mpz_set_str(q_, q.c_str(), 16);
    mpz_mul(p_square_, p_, p_);
    mpz_mul(q_square_, q_, q_);
    mpz_h_func(hp_, n_, p_, p_square_);
    mpz_h_func(hq_, n_, q_, q_square_);
    mpz_invert(q_invert_p_, q_, p_);
    has_private_key_ = true;
    return 0;
  }

  int Encrypt(const int64 plaintext, const string& hsa, string& ciphertext) {
    if (!has_public_key_) {
      return 1;
    }

    mpz_t c, hsa_;
    mpz_inits(c, hsa_, NULL);
    mpz_set_sll(c, plaintext);
    mpz_set_str(hsa_, hsa.c_str(), 16);
    if (!mpz_sgn(hsa_)) {
      mpz_urandomb(hsa_, randstate_, a_bytes_ << 3);
      fbpowm_.mpz_fbpowm(hsa_, hsa_);
    }

    if (plaintext < 0) {
      mpz_abs(c, c);
    }
    mpz_mul(c, c, n_);
    mpz_add_ui(c, c, 1);
    if (plaintext < 0) {
      mpz_invert(c, c, n_square_);
    }
    mpz_mul(c, c, hsa_);
    mpz_mod(c, c, n_square_);
    mpz_get_cxx_str(ciphertext, 16, c);

    mpz_clears(c, hsa_, NULL);
    return 0;
  }

  int Decrypt(const string& ciphertext, string& plaintext) {
    if (!has_private_key_) {
      return 1;
    }
    mpz_t m;
    mpz_init(m);
    _Decrypt(m, ciphertext);
    mpz_get_cxx_str(plaintext, 16, m);
    mpz_clear(m);
    return 0;
  }

  int Decrypt(const string& ciphertext, int64& plaintext) {
    if (!has_private_key_) {
      return 1;
    }
    mpz_t m;
    mpz_init(m);
    _Decrypt(m, ciphertext);
    plaintext = mpz_get_sll(m);
    mpz_clear(m);
    return 0;
  }

  int Add(const string& x, const string& y, string& z) {
    if (!has_public_key_) {
      return 1;
    }
    mpz_t op, rop;
    mpz_init_set_str(rop, x.c_str(), 16);
    mpz_init_set_str(op, y.c_str(), 16);
    mpz_mul(rop, rop, op);
    mpz_mod(rop, rop, n_square_);
    mpz_get_cxx_str(z, 16, rop);
    mpz_clears(op, rop, NULL);
    return 0;
  }

  int Add(mpz_t x, mpz_t y, mpz_t z) {
    if (!has_public_key_) {
      return 1;
    }
    mpz_mul(z, x, y);
    mpz_mod(z, z, n_square_);
    return 0;
  }

  int MulScalar(const string& x, const int32 y, string& z) {
    if (!has_public_key_) {
      return 1;
    }
    mpz_t rop;
    mpz_init_set_str(rop, x.c_str(), 16);
    if (y < 0) {
      mpz_invert(rop, rop, n_square_);
      mpz_powm_ui(rop, rop, -y, n_square_);
    } else {
      mpz_powm_ui(rop, rop, y, n_square_);
    }
    mpz_get_cxx_str(z, 16, rop);
    mpz_clear(rop);
    return 0;
  }

  int MulScalar(mpz_t x, mpz_t y, mpz_t z) {
    if (!has_public_key_) {
      return 1;
    }
    if (mpz_sgn(y) < 0) {
      mpz_t abs_y;
      mpz_init(abs_y);
      mpz_neg(abs_y, y);
      mpz_invert(z, x, n_square_);
      mpz_powm(z, z, abs_y, n_square_);
      mpz_clear(abs_y);
    } else {
      mpz_powm(z, x, y, n_square_);
    }
    return 0;
  }

  int MulScalar(const string& x, mpz_t y, string& z) {
    if (!has_public_key_) {
      return 1;
    }
    mpz_t rop, op;
    mpz_init(rop);
    mpz_init_set_str(op, x.c_str(), 16);
    MulScalar(op, y, rop);
    mpz_get_cxx_str(z, 16, rop);
    mpz_clears(rop, op, NULL);
    return 0;
  }

  int MulScalar(const string& x, const int64 y, string& z) {
    if (!has_public_key_) {
      return 1;
    }
    mpz_t op;
    mpz_init(op);
    mpz_set_sll(op, y);
    MulScalar(x, op, z);
    mpz_clear(op);
    return 0;
  }

  int MulScalar(const string& x, const string& y, string& z) {
    if (!has_public_key_) {
      return 1;
    }
    mpz_t op;
    mpz_init_set_str(op, y.c_str(), 16);
    MulScalar(x, op, z);
    mpz_clear(op);
    return 0;
  }

  int MulScalar(const string& x, int64 y, mpz_t z) {
    if (!has_public_key_) {
      return 1;
    }
    mpz_t op;
    mpz_init_set_str(op, x.c_str(), 16);
    if (y < 0) {
      mpz_set_sll(z, -y);
      mpz_invert(z, z, n_square_);
    } else {
      mpz_set_sll(z, y);
    }
    mpz_powm(z, op, z, n_square_);
    mpz_clear(op);
    return 0;
  }

  int Invert(mpz_t x, mpz_t x_invert) {
    if (!has_public_key_) {
      return 1;
    }
    mpz_invert(x_invert, x, n_square_);
    return 0;
  }

  int Invert(const string& x, string& y) {
    if (!has_public_key_) {
      return 1;
    }
    mpz_t op;
    mpz_init_set_str(op, x.c_str(), 16);
    mpz_invert(op, op, n_square_);
    mpz_get_cxx_str(y, 16, op);
    mpz_clear(op);
    return 0;
  }

  int MpzGetStr(string& str, int base, mpz_t op) {
    if (!has_public_key_) {
      return 1;
    }
    mpz_get_cxx_str(str, base, op);
    return 0;
  }

 private:
  void _Decrypt(mpz_t m, const string& ciphertext) {
    mpz_t c;
    mpz_init_set_str(c, ciphertext.c_str(), 16);

    mpz_m_func(m, c, p_, p_square_, hp_);
    mpz_m_func(c, c, q_, q_square_, hq_);
    mpz_sub(m, m, c);
    mpz_mul(m, m, q_invert_p_);
    mpz_mod(m, m, p_);
    mpz_mul(m, m, q_);
    mpz_add(m, m, c);
    mpz_mod(m, m, n_);
    if (mpz_cmp(m, max_) > 0) {
      mpz_sub(m, m, n_);
    }
    mpz_clear(c);
  }

  bool has_public_key_ = false;
  bool has_private_key_ = false;
  int n_bytes_;
  int a_bytes_;
  mpz_t n_;
  mpz_t n_square_;
  mpz_t hs_;
  mpz_t p_;
  mpz_t q_;
  mpz_t hp_;
  mpz_t hq_;
  mpz_t p_square_;
  mpz_t q_square_;
  mpz_t q_invert_p_;
  mpz_t max_;
  gmp_randstate_t randstate_;
  FixedBasePowm fbpowm_;
};

REGISTER_RESOURCE_HANDLE_OP(PaillierKeypair);
REGISTER_RESOURCE_HANDLE_KERNEL(PaillierKeypair);

REGISTER_OP("CreatePaillierKeypair")
    .Input("keypair: resource")
    .SetShapeFn(shape_inference::NoOutputs)
    .Doc(R"doc(
Create a PaillierKeypair resource.

keypair: the resource to be created.
)doc");

class CreatePaillierKeypairOp : public OpKernel {
 public:
  explicit CreatePaillierKeypairOp(OpKernelConstruction* context) : OpKernel(context) {}
  void Compute(OpKernelContext* context) override {
    auto keypair = new PaillierKeypair();
    auto s = CreateResource(context, HandleFromInput(context, 0), keypair);
    if (!s.ok() && s.code() != error::ALREADY_EXISTS) {
      OP_REQUIRES(context, false, s);
    }
  }
};

REGISTER_KERNEL_BUILDER(Name("CreatePaillierKeypair").Device(DEVICE_CPU), CreatePaillierKeypairOp);

REGISTER_OP("SetPaillierPublicKey")
    .Input("keypair: resource")
    .Input("n: string")
    .Input("n_bytes: int32")
    .Input("hs: string")
    .Input("a_bytes: int32")
    .Attr("group_size: int = 1")
    .SetShapeFn(shape_inference::NoOutputs)
    .Doc(R"doc(
Set public key in Paillier Keypair.
(n, hs) is public key.

keypair: Paillier Keypair.
n_bytes: bytes of n.
)doc");

class SetPaillierPublicKeyOp : public OpKernel {
 public:
  explicit SetPaillierPublicKeyOp(OpKernelConstruction* context) : OpKernel(context) {
    OP_REQUIRES_OK(context, context->GetAttr("group_size", &group_size_));
  }

  void Compute(OpKernelContext* context) override {
    PaillierKeypair* keypair = nullptr;
    const Tensor* n_tensor = nullptr;
    const Tensor* n_bytes_tensor = nullptr;
    const Tensor* hs_tensor = nullptr;
    const Tensor* a_bytes_tensor = nullptr;
    OP_REQUIRES_OK(context, LookupResource(context, HandleFromInput(context, 0), &keypair));
    OP_REQUIRES_OK(context, context->input("n", &n_tensor));
    OP_REQUIRES_OK(context, context->input("n_bytes", &n_bytes_tensor));
    OP_REQUIRES_OK(context, context->input("hs", &hs_tensor));
    OP_REQUIRES_OK(context, context->input("a_bytes", &a_bytes_tensor));
    auto n = n_tensor->scalar<string>()();
    auto n_bytes = n_bytes_tensor->scalar<int>()();
    auto hs = hs_tensor->scalar<string>()();
    auto a_bytes = a_bytes_tensor->scalar<int>()();
    keypair->Ref();
    auto code = keypair->SetPublicKey(n, n_bytes, hs, a_bytes, group_size_);
    keypair->Unref();
    if (code == -1) {
      OP_REQUIRES_OK(context, errors::ResourceExhausted("Memory usage exceeds a predefined threshold."));
    }
  }

 private:
  int group_size_;
};

REGISTER_KERNEL_BUILDER(Name("SetPaillierPublicKey").Device(DEVICE_CPU), SetPaillierPublicKeyOp);

REGISTER_OP("SetPaillierPrivateKey")
    .Input("keypair: resource")
    .Input("p: string")
    .Input("q: string")
    .SetShapeFn(shape_inference::NoOutputs)
    .Doc(R"doc(
Set private key in Paillier Keypair.

keypair: Paillier Keypair.
(p, q) is public key.
)doc");

class SetPaillierPrivateKeyOp : public OpKernel {
 public:
  explicit SetPaillierPrivateKeyOp(OpKernelConstruction* context) : OpKernel(context) {}

  void Compute(OpKernelContext* context) override {
    PaillierKeypair* keypair = nullptr;
    const Tensor* p_tensor = nullptr;
    const Tensor* q_tensor = nullptr;
    OP_REQUIRES_OK(context, LookupResource(context, HandleFromInput(context, 0), &keypair));
    OP_REQUIRES_OK(context, context->input("p", &p_tensor));
    OP_REQUIRES_OK(context, context->input("q", &q_tensor));
    auto p = p_tensor->scalar<string>()();
    auto q = q_tensor->scalar<string>()();
    keypair->Ref();
    keypair->SetPrivateKey(p, q);
    keypair->Unref();
  }
};

REGISTER_KERNEL_BUILDER(Name("SetPaillierPrivateKey").Device(DEVICE_CPU), SetPaillierPrivateKeyOp);

REGISTER_OP("PaillierEncrypt")
    .Input("keypair: resource")
    .Input("plaintext: int64")
    .Input("hsa: string")
    .Output("ciphertext: string")
    .SetShapeFn([](shape_inference::InferenceContext* c) {
      c->set_output(0, c->input(1));
      return Status::OK();
    })
    .Doc(R"doc(
Encrypt int64 value using Paillier.

keypair: Paillier Keypair used to encrypt.
plaintext: tensor to be encrypted.
hsa: hsa is a pre-compute tensor used to encrypt. hsa is equal to hs ^ a, where 'a' is a random value.
     If hsa is 0, a random 'a' will be generated while computing.
ciphertext: the encrypted tensor.
)doc");

class PaillierEncryptOp : public OpKernel {
 public:
  explicit PaillierEncryptOp(OpKernelConstruction* context) : OpKernel(context) {}

  void Compute(OpKernelContext* context) override {
    PaillierKeypair* keypair = nullptr;
    const Tensor* plaintext_tensor = nullptr;
    const Tensor* hsa_tensor = nullptr;
    Tensor* ciphertext_tensor = nullptr;
    OP_REQUIRES_OK(context, LookupResource(context, HandleFromInput(context, 0), &keypair));
    OP_REQUIRES_OK(context, context->input("plaintext", &plaintext_tensor));
    OP_REQUIRES_OK(context, context->input("hsa", &hsa_tensor));
    OP_REQUIRES_OK(context, context->allocate_output(0, plaintext_tensor->shape(), &ciphertext_tensor));
    keypair->Ref();
    auto plaintext_flat = plaintext_tensor->flat<int64>();
    auto hsa_flat = hsa_tensor->flat<string>();
    if (plaintext_tensor->shape() != hsa_tensor->shape()) {
      OP_REQUIRES_OK(context, errors::InvalidArgument("plaintext and hsa should be the same size."));
    }

    auto ciphertext_flat = ciphertext_tensor->flat<string>();
    int error_code = 0;
    auto task = [&keypair, &error_code, &plaintext_flat, &hsa_flat, &ciphertext_flat]
        (int64 start, int64 end) {
      for (auto i = start; i < end; ++i) {
        if (keypair->Encrypt(plaintext_flat(i), hsa_flat(i), ciphertext_flat(i))) {
          error_code = 1;
        }
      }
    };

    auto worker_threads = context->device()->tensorflow_cpu_worker_threads();
    Shard(worker_threads->num_threads - 1, worker_threads->workers,
          plaintext_flat.size(), 10000, task);
    keypair->Unref();
    if (error_code) {
      OP_REQUIRES_OK(context, errors::Aborted("No public key."));
    }
  }
};

REGISTER_KERNEL_BUILDER(Name("PaillierEncrypt").Device(DEVICE_CPU), PaillierEncryptOp);

REGISTER_OP("PaillierDecrypt")
    .Input("keypair: resource")
    .Input("ciphertext: string")
    .Output("plaintext: dtype")
    .Attr("dtype: {string, int64}")
    .SetShapeFn([](shape_inference::InferenceContext* c) {
      c->set_output(0, c->input(1));
      return Status::OK();
    })
    .Doc(R"doc(
Decrypt Paillier ciphertext.

keypair: Paillier Keypair used to decrypt.
ciphertext: the tensor to be decrypted.
plaintext: the decrypted tensor.
)doc");

template<typename T>
class PaillierDecryptOp : public OpKernel {
 public:
  explicit PaillierDecryptOp(OpKernelConstruction* context) : OpKernel(context) {}

  void Compute(OpKernelContext* context) override {
    PaillierKeypair* keypair = nullptr;
    const Tensor* ciphertext_tensor = nullptr;
    Tensor* plaintext_tensor = nullptr;
    OP_REQUIRES_OK(context, LookupResource(context, HandleFromInput(context, 0), &keypair));
    OP_REQUIRES_OK(context, context->input("ciphertext", &ciphertext_tensor));
    OP_REQUIRES_OK(context, context->allocate_output(0, ciphertext_tensor->shape(), &plaintext_tensor));
    keypair->Ref();
    auto ciphertext_flat = ciphertext_tensor->flat<string>();
    auto plaintext_flat = plaintext_tensor->flat<T>();
    int error_code = 0;
    auto task = [&keypair, &error_code, &ciphertext_flat, &plaintext_flat] (int64 start, int64 end) {
      for (auto i = start; i < end; ++i) {
        if (keypair->Decrypt(ciphertext_flat(i), plaintext_flat(i))) {
          error_code = 1;
        }
      }
    };

    auto worker_threads = context->device()->tensorflow_cpu_worker_threads();
    Shard(worker_threads->num_threads - 1, worker_threads->workers,
          plaintext_flat.size(), 10000, task);
    keypair->Unref();
    if (error_code) {
      OP_REQUIRES_OK(context, errors::Aborted("No private key."));
    }
  }
};

REGISTER_KERNEL_BUILDER(
    Name("PaillierDecrypt").Device(DEVICE_CPU).TypeConstraint<string>("dtype"),
    PaillierDecryptOp<string>);
REGISTER_KERNEL_BUILDER(
    Name("PaillierDecrypt").Device(DEVICE_CPU).TypeConstraint<int64>("dtype"),
    PaillierDecryptOp<int64>);

REGISTER_OP("PaillierAdd")
    .Input("keypair: resource")
    .Input("x: string")
    .Input("y: string")
    .Output("z: string")
    .SetShapeFn([](shape_inference::InferenceContext* c) {
      c->set_output(0, c->input(1));
      return Status::OK();
    })
    .Doc(R"doc(
This op computes z = x * y, which is equivalent to computing
z' = x' + y', where z', x' and y' are unencrypted tensors.

keypair: Paillier Keypair used to compute.
x: an encrypted tensor.
y: an encrypted tensor.
z: an encrypted tensor.
)doc");

class PaillierAddOp : public OpKernel {
 public:
  explicit PaillierAddOp(OpKernelConstruction* context) : OpKernel(context) {}

  void Compute(OpKernelContext* context) override {
    PaillierKeypair* keypair = nullptr;
    const Tensor* x_tensor = nullptr;
    const Tensor* y_tensor = nullptr;
    Tensor* z_tensor = nullptr;
    OP_REQUIRES_OK(context, LookupResource(context, HandleFromInput(context, 0), &keypair));
    OP_REQUIRES_OK(context, context->input("x", &x_tensor));
    OP_REQUIRES_OK(context, context->input("y", &y_tensor));
    OP_REQUIRES_OK(context, context->allocate_output("z", x_tensor->shape(), &z_tensor));
    keypair->Ref();
    const auto& x_flat = x_tensor->flat<string>();
    const auto& y_flat = y_tensor->flat<string>();
    if (x_tensor->shape() != y_tensor->shape()) {
      OP_REQUIRES_OK(context, errors::InvalidArgument("x and y should be the same size."));
    }
    auto z_flat = z_tensor->flat<string>();
    auto task = [&keypair, &x_flat, &y_flat, &z_flat] (int64 start, int64 end) {
      for (auto i = start; i < end; ++i) {
        keypair->Add(x_flat(i), y_flat(i), z_flat(i));
      }
    };
    auto worker_threads = context->device()->tensorflow_cpu_worker_threads();
    Shard(worker_threads->num_threads - 1, worker_threads->workers,
          x_flat.size(), 20, task);
    keypair->Unref();
  }
};

REGISTER_KERNEL_BUILDER(Name("PaillierAdd").Device(DEVICE_CPU), PaillierAddOp);

REGISTER_OP("PaillierMulScalar")
    .Input("keypair: resource")
    .Input("x: string")
    .Input("y: T")
    .Attr("T: {int32, int64, string}")
    .Output("z: string")
    .SetShapeFn([](shape_inference::InferenceContext* c) {
      c->set_output(0, c->input(1));
      return Status::OK();
    })
    .Doc(R"doc(
This op computes z = x ^ y, which is equivalent to computing
z' = x' * y, where z', x' are unencrypted tensors.

keypair: Paillier Keypair used to compute.
x: an encrypted tensor.
y: an unencrypted tensor.
z: an encrypted tensor.
)doc");

template<typename T>
class PaillierMulScalarOp : public OpKernel {
 public:
  explicit PaillierMulScalarOp(OpKernelConstruction* context) : OpKernel(context) {}

  void Compute(OpKernelContext* context) override {
    PaillierKeypair* keypair = nullptr;
    const Tensor* x_tensor = nullptr;
    const Tensor* y_tensor = nullptr;
    Tensor* z_tensor = nullptr;
    OP_REQUIRES_OK(context, LookupResource(context, HandleFromInput(context, 0), &keypair));
    OP_REQUIRES_OK(context, context->input("x", &x_tensor));
    OP_REQUIRES_OK(context, context->input("y", &y_tensor));
    OP_REQUIRES_OK(context, context->allocate_output("z", x_tensor->shape(), &z_tensor));
    keypair->Ref();
    const auto& x_flat = x_tensor->flat<string>();
    const auto& y_flat = y_tensor->flat<T>();
    if (x_tensor->shape() != y_tensor->shape()) {
      OP_REQUIRES_OK(context, errors::InvalidArgument("x and y should be the same size."));
    }
    auto z_flat = z_tensor->flat<string>();
    auto task = [&keypair, &x_flat, &y_flat, &z_flat] (int64 start, int64 end) {
      for (auto i = start; i < end; ++i) {
        keypair->MulScalar(x_flat(i), y_flat(i), z_flat(i));
      }
    };

    auto worker_threads = context->device()->tensorflow_cpu_worker_threads();
    Shard(worker_threads->num_threads - 1, worker_threads->workers,
          x_flat.size(), 100, task);
    keypair->Unref();
  }
};

REGISTER_KERNEL_BUILDER(
    Name("PaillierMulScalar").Device(DEVICE_CPU).TypeConstraint<int32>("T"),
    PaillierMulScalarOp<int32>);
REGISTER_KERNEL_BUILDER(
    Name("PaillierMulScalar").Device(DEVICE_CPU).TypeConstraint<int64>("T"),
    PaillierMulScalarOp<int64>);
REGISTER_KERNEL_BUILDER(
    Name("PaillierMulScalar").Device(DEVICE_CPU).TypeConstraint<string>("T"),
    PaillierMulScalarOp<string>);

REGISTER_OP("PaillierMulExp2")
    .Input("keypair: resource")
    .Input("x: string")
    .Input("y: T")
    .Attr("T: {int32, int64}")
    .Output("z: string")
    .SetShapeFn([](shape_inference::InferenceContext* c) {
      c->set_output(0, c->input(1));
      return Status::OK();
    })
    .Doc(R"doc(
This op computes z = x ^ (2 ^ y), which is equivalent to computing
z' = x' << y, where z', x' are unencrypted tensors.

keypair: Paillier Keypair used to compute.
x: an encrypted tensor.
y: an unencrypted tensor.
z: an encrypted tensor.
)doc");

template<typename T>
class PaillierMulExp2Op : public OpKernel {
 public:
  explicit PaillierMulExp2Op(OpKernelConstruction* context) : OpKernel(context) {}

  void Compute(OpKernelContext* context) override {
    PaillierKeypair* keypair = nullptr;
    const Tensor* x_tensor = nullptr;
    const Tensor* y_tensor = nullptr;
    Tensor* z_tensor = nullptr;
    OP_REQUIRES_OK(context, LookupResource(context, HandleFromInput(context, 0), &keypair));
    OP_REQUIRES_OK(context, context->input("x", &x_tensor));
    OP_REQUIRES_OK(context, context->input("y", &y_tensor));
    OP_REQUIRES_OK(context, context->allocate_output("z", x_tensor->shape(), &z_tensor));
    keypair->Ref();
    const auto& x_flat = x_tensor->flat<string>();
    const auto& y_flat = y_tensor->flat<T>();
    if (x_tensor->shape() != y_tensor->shape()) {
      OP_REQUIRES_OK(context, errors::InvalidArgument("x and y should be the same size."));
    }
    auto z_flat = z_tensor->flat<string>();
    int error_code = 0;
    auto task = [&error_code, &keypair, &x_flat, &y_flat, &z_flat] (int64 start, int64 end) {
      for (auto i = start; i < end; ++i) {
        if (y_flat(i) < 0) {
          error_code = 1;
          break;
        }
        mpz_t op;
        mpz_init_set_si(op, 1);
        mpz_mul_2exp(op, op, y_flat(i));
        keypair->MulScalar(x_flat(i), op, z_flat(i));
        mpz_clear(op);
      }
    };

    auto worker_threads = context->device()->tensorflow_cpu_worker_threads();
    Shard(worker_threads->num_threads - 1, worker_threads->workers,
          x_flat.size(), 40, task);
    keypair->Unref();
    if (error_code) {
      OP_REQUIRES_OK(context, errors::InvalidArgument("y should be a positive tensor."));
    }
  }
};

REGISTER_KERNEL_BUILDER(
    Name("PaillierMulExp2").Device(DEVICE_CPU).TypeConstraint<int32>("T"),
    PaillierMulExp2Op<int32>);
REGISTER_KERNEL_BUILDER(
    Name("PaillierMulExp2").Device(DEVICE_CPU).TypeConstraint<int64>("T"),
    PaillierMulExp2Op<int64>);

REGISTER_OP("PaillierInvert")
    .Input("keypair: resource")
    .Input("x: string")
    .Output("y: string")
    .SetShapeFn([](shape_inference::InferenceContext* c) {
      c->set_output(0, c->input(1));
      return Status::OK();
    })
    .Doc(R"doc(
This op computes y = x^(-1) (mod n^2) where n is a public key in keypair.

keypair: Paillier Keypair used to compute.
x: a large integer tensor.
y: a large integer tensor.
)doc");

class PaillierInvertOp : public OpKernel {
 public:
  explicit PaillierInvertOp(OpKernelConstruction* context) : OpKernel(context) {}

  void Compute(OpKernelContext* context) override {
    PaillierKeypair* keypair = nullptr;
    const Tensor* x_tensor = nullptr;
    Tensor* y_tensor = nullptr;
    OP_REQUIRES_OK(context, LookupResource(context, HandleFromInput(context, 0), &keypair));
    OP_REQUIRES_OK(context, context->input("x", &x_tensor));
    OP_REQUIRES_OK(context, context->allocate_output("y", x_tensor->shape(), &y_tensor));
    auto x = x_tensor->flat<string>();
    auto y = y_tensor->flat<string>();
    keypair->Ref();

    auto task = [keypair, &x, &y] (int64 start, int64 end) {
      for (auto i = start; i < end; ++i) {
        keypair->Invert(x(i), y(i));
      }
    };

    auto worker_threads = context->device()->tensorflow_cpu_worker_threads();
    Shard(worker_threads->num_threads - 1, worker_threads->workers,
          x.size(), 500, task);
    keypair->Unref();
  }
};

REGISTER_KERNEL_BUILDER(Name("PaillierInvert").Device(DEVICE_CPU), PaillierInvertOp);

REGISTER_OP("GeneratePaillierKeypair")
    .Input("keypair: resource")
    .Attr("n_bytes: int = 512")
    .Attr("a_bytes: int = 256")
    .Attr("reps: int = 24")
    .Attr("group_size: int = 1")
    .Output("public_key: string")
    .Output("private_key: string")
    .SetShapeFn([](shape_inference::InferenceContext* c) {
      c->set_output(0, c->MakeShape({c->MakeDim(2)}));
      c->set_output(1, c->MakeShape({c->MakeDim(2)}));
      return Status::OK();
    })
    .Doc(R"doc(
Generate a Paillier keypair.

keypair: the keypair to be generated.
n_bytes: bytes of n.
reps: When this op perform probabilistic primality test,
      it will perform reps Miller-Rabin tests. Reasonable
      values of reps are between 15 and 50.
public_key: generated public key.
private_key: generated private key.
)doc");

class GeneratePaillierKeypairOp : public OpKernel {
 public:
  explicit GeneratePaillierKeypairOp(OpKernelConstruction* context) : OpKernel(context) {
    OP_REQUIRES_OK(context, context->GetAttr("n_bytes", &n_bytes_));
    OP_REQUIRES_OK(context, context->GetAttr("a_bytes", &a_bytes_));
    OP_REQUIRES_OK(context, context->GetAttr("reps", &reps_));
    OP_REQUIRES_OK(context, context->GetAttr("group_size", &group_size_));
  }

  void Compute(OpKernelContext* context) override {
    PaillierKeypair* keypair = nullptr;
    Tensor* public_key_tensor = nullptr;
    Tensor* private_key_tensor = nullptr;
    OP_REQUIRES_OK(context, LookupResource(context, HandleFromInput(context, 0), &keypair));
    OP_REQUIRES_OK(context, context->allocate_output("public_key", TensorShape({2}), &public_key_tensor));
    OP_REQUIRES_OK(context, context->allocate_output("private_key", TensorShape({2}), &private_key_tensor));
    auto public_key = public_key_tensor->flat<string>();
    auto private_key = private_key_tensor->flat<string>();
    keypair->Ref();
    time_t curr_time;
    time(&curr_time);
    mpz_t p, q, n, hs, tmp1, tmp2;
    gmp_randstate_t randstate;
    mpz_inits(p, q, n, hs, tmp1, tmp2, NULL);
    gmp_randinit_mt(randstate);
    gmp_randseed_ui(randstate, curr_time);

    auto find_prime = [this, &randstate] (mpz_t rop) {
      auto bits = n_bytes_ << 2;
      mpz_urandomb(rop, randstate, bits);
      mpz_setbit(rop, 0);
      mpz_setbit(rop, 1);
      mpz_setbit(rop, bits - 1);
      while (!mpz_probab_prime_p(rop, reps_)) {
        mpz_urandomb(rop, randstate, bits);
        mpz_setbit(rop, 0);
        mpz_setbit(rop, 1);
        mpz_setbit(rop, bits - 1);
      }
    };

    find_prime(p);
    find_prime(q);
    mpz_sub_ui(tmp1, p, 1);
    mpz_sub_ui(tmp2, q, 1);
    mpz_gcd(tmp1, tmp1, tmp2);
    while (mpz_cmp_ui(tmp1, 2)) {
      find_prime(p);
      find_prime(q);
      mpz_sub_ui(tmp1, p, 1);
      mpz_sub_ui(tmp2, q, 1);
      mpz_gcd(tmp1, tmp1, tmp2);
    }
    mpz_mul(n, p, q);
    mpz_urandomm(tmp1, randstate, n);
    mpz_gcd(tmp2, tmp1, n);
    while (mpz_cmp_ui(tmp2, 1)) {
      mpz_urandomm(tmp1, randstate, n);
      mpz_gcd(tmp2, tmp1, n);
    }
    mpz_mul(hs, tmp1, tmp1);
    mpz_neg(hs, hs);
    mpz_mod(hs, hs, n);
    mpz_mul(tmp1, n, n);
    mpz_powm(hs, hs, n, tmp1);
    char* ptr = new char[(n_bytes_ << 2) + 1];
    public_key(0) = string(mpz_get_str(ptr, 16, n));
    public_key(1) = string(mpz_get_str(ptr, 16, hs));
    private_key(0) = string(mpz_get_str(ptr, 16, p));
    private_key(1) = string(mpz_get_str(ptr, 16, q));
    delete[] ptr;
    auto code = keypair->SetPublicKey(public_key(0), n_bytes_, public_key(1), a_bytes_, group_size_);
    keypair->SetPrivateKey(private_key(0), private_key(1));

    mpz_clears(p, q, n, hs, tmp1, tmp2, NULL);
    gmp_randclear(randstate);
    keypair->Unref();
    if (code == -1) {
      OP_REQUIRES_OK(context, errors::ResourceExhausted("Memory usage exceeds a predefined threshold."));
    }
  }

 private:
  int n_bytes_;
  int a_bytes_;
  int reps_;
  int group_size_;
};

REGISTER_KERNEL_BUILDER(Name("GeneratePaillierKeypair").Device(DEVICE_CPU), GeneratePaillierKeypairOp);

REGISTER_OP("PaillierMatmul")
    .Input("keypair: resource")
    .Input("x_mantissa: string")
    .Input("x_exponent: int64")
    .Input("y_mantissa: int64")
    .Input("y_exponent: int64")
    .Output("z_mantissa: string")
    .Output("z_exponent: int64")
    .SetShapeFn([](shape_inference::InferenceContext* c) {
      auto shape = c->MakeShape({c->Dim(c->input(1), 0), c->Dim(c->input(3), 1)});
      c->set_output(0, shape);
      c->set_output(1, shape);
      return Status::OK();
    })
    .Doc(R"doc(
This op computes z = matmul(x, y) in ciphertext space.

keypair: Paillier Keypair used to compute.
x_mantissa: the mantissa of x.
x_exponent: the exponent of x.
y_mantissa: the mantissa of y.
y_exponent: the exponent of y.
z_mantissa: the mantissa of z.
z_exponent: the exponent of z.
)doc");

class PaillierMatmulOp : public OpKernel {
 public:
  explicit PaillierMatmulOp(OpKernelConstruction* context) : OpKernel(context) {}

  void Compute(OpKernelContext* context) override {
    PaillierKeypair* keypair = nullptr;
    const Tensor* x_mantissa_tensor = nullptr;
    const Tensor* x_exponent_tensor = nullptr;
    const Tensor* y_mantissa_tensor = nullptr;
    const Tensor* y_exponent_tensor = nullptr;
    Tensor* z_mantissa_tensor = nullptr;
    Tensor* z_exponent_tensor = nullptr;
    OP_REQUIRES_OK(context, LookupResource(context, HandleFromInput(context, 0), &keypair));
    OP_REQUIRES_OK(context, context->input("x_mantissa", &x_mantissa_tensor));
    OP_REQUIRES_OK(context, context->input("x_exponent", &x_exponent_tensor));
    OP_REQUIRES_OK(context, context->input("y_mantissa", &y_mantissa_tensor));
    OP_REQUIRES_OK(context, context->input("y_exponent", &y_exponent_tensor));
    if (x_mantissa_tensor->shape() != x_exponent_tensor->shape()) {
      OP_REQUIRES_OK(context, errors::InvalidArgument("x_mantissa and x_exponent should be the same size."));
    }
    if (y_mantissa_tensor->shape() != y_exponent_tensor->shape()) {
      OP_REQUIRES_OK(context, errors::InvalidArgument("y_mantissa and y_exponent should be the same size."));
    }
    auto x_rank = x_mantissa_tensor->shape().dims();
    auto y_rank = y_mantissa_tensor->shape().dims();
    if (x_rank != 2) {
      OP_REQUIRES_OK(context, errors::InvalidArgument("the rank of x should be two."));
    }
    if (y_rank != 2) {
      OP_REQUIRES_OK(context, errors::InvalidArgument("the rank of y should be two."));
    }
    auto u = x_mantissa_tensor->shape().dim_size(0);
    auto v = x_mantissa_tensor->shape().dim_size(1);
    auto w = y_mantissa_tensor->shape().dim_size(1);
    if (v != y_mantissa_tensor->shape().dim_size(0)) {
      OP_REQUIRES_OK(context, errors::InvalidArgument("the size of x's 1st dim should be equal to the size of y's 2nd dim."));
    }
    OP_REQUIRES_OK(context, context->allocate_output(0, TensorShape({u, w}), &z_mantissa_tensor));
    OP_REQUIRES_OK(context, context->allocate_output(1, TensorShape({u, w}), &z_exponent_tensor));
    keypair->Ref();
    auto x_mantissa = x_mantissa_tensor->flat<string>();
    auto x_exponent = x_exponent_tensor->flat<int64>();
    auto y_mantissa = y_mantissa_tensor->flat<int64>();
    auto y_exponent = y_exponent_tensor->flat<int64>();
    auto z_mantissa = z_mantissa_tensor->flat<string>();
    auto z_exponent = z_exponent_tensor->flat<int64>();
    auto N = y_mantissa.size();
    int64* yt_mantissa = new int64[N];
    int64* yt_exponent = new int64[N];
    for (auto i = 0; i < N; ++i) {
      yt_mantissa[i / w + i % w * v] = y_mantissa(i);
      yt_exponent[i / w + i % w * v] = y_exponent(i);
    }
    N = x_mantissa.size();
    mpz_t* x_mantissa_invert = new mpz_t[N];
    for (auto i = 0; i < N; ++i) {
      mpz_init_set_str(x_mantissa_invert[i], x_mantissa(i).c_str(), 16);
      keypair->Invert(x_mantissa_invert[i], x_mantissa_invert[i]);
    }

    auto task = [keypair, &x_exponent, yt_exponent, &z_exponent, &x_mantissa, x_mantissa_invert,
                 yt_mantissa, &z_mantissa, v, w] (int64 start, int64 end) {
      mpz_t addend_op, exp_op, sum_op;
      mpz_inits(addend_op, exp_op, sum_op, NULL);
      for (auto i = start; i < end; ++i) {
        auto sx = i / w * v;
        auto sy = i % w * v;
        auto min = 0x7FFFFFFFFFFFFFFFLL;
        for (auto j = 0; j < v; ++j) {
          auto exp = x_exponent(sx + j) + yt_exponent[sy + j];
          if (exp < min) {
            min = exp;
          }
        }
        for (auto j = 0; j < v; ++j) {
          auto exp = x_exponent(sx + j) + yt_exponent[sy + j] - min;
          if (yt_mantissa[sy + j] >= 0) {
            keypair->MulScalar(x_mantissa(sx + j), yt_mantissa[sy + j], addend_op); 
          } else {
            mpz_set_sll(addend_op, -yt_mantissa[sy + j]);
            keypair->MulScalar(x_mantissa_invert[sx + j], addend_op, addend_op);
          }
          mpz_set_si(exp_op, 1);
          mpz_mul_2exp(exp_op, exp_op, exp);
          keypair->MulScalar(addend_op, exp_op, addend_op);
          if (!j) {
            mpz_set(sum_op, addend_op);
          }
          else {
            keypair->Add(addend_op, sum_op, sum_op);
          }
        }
        z_exponent(i) = min;
        keypair->MpzGetStr(z_mantissa(i), 16, sum_op);
      }
      mpz_clears(addend_op, exp_op, sum_op, NULL);
    };

    auto worker_threads = context->device()->tensorflow_cpu_worker_threads();
    Shard(worker_threads->num_threads - 1, worker_threads->workers,
          u * w, v * 10000, task);

    for (auto i = 0; i < N; ++i) {
      mpz_clear(x_mantissa_invert[i]);
    }
    delete[] yt_mantissa;
    delete[] yt_exponent;
    delete[] x_mantissa_invert;
    keypair->Unref();
  }
};

REGISTER_KERNEL_BUILDER(Name("PaillierMatmul").Device(DEVICE_CPU), PaillierMatmulOp);

} // efl
} // tensorflow

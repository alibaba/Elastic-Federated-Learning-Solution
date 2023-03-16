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
#include <math.h>
#include <gmp.h>
#include "tensorflow/core/framework/op.h"
#include "tensorflow/core/lib/core/errors.h"
#include "tensorflow/core/framework/op_kernel.h"
#include "tensorflow/core/framework/shape_inference.h"
#include "tensorflow/core/framework/common_shape_fns.h"
#include "tensorflow/core/util/work_sharder.h"

namespace tensorflow {
namespace efl {

class GmpInvertOp : public OpKernel {
 public:
  explicit GmpInvertOp(OpKernelConstruction* ctx)
      : OpKernel(ctx) {}

  void Compute(OpKernelContext* ctx) override {
    const Tensor* x_tensor;
    const Tensor* y_tensor;
    OP_REQUIRES_OK(ctx, ctx->input("x", &x_tensor));
    OP_REQUIRES_OK(ctx, ctx->input("y", &y_tensor));
    const auto& x_flat = x_tensor->flat<string>();
    const auto& y_flat = y_tensor->flat<string>();
    Tensor* result_tensor = nullptr;
    OP_REQUIRES_OK(ctx, ctx->allocate_output("result",
	x_tensor->shape(), &result_tensor));
    auto result_flat = result_tensor->flat<string>();
    auto RunTask = [this, &x_flat, &y_flat, &result_flat](int64 start, int64 end) {
      typedef decltype(x_flat.size()) Index;
      for (Index i = start; i < end; ++i) {
	mpz_t m_x, m_y, m_r;
	mpz_inits(m_x, m_y, m_r, NULL);
	mpz_set_str(m_x, x_flat(i).c_str(), 10);
	mpz_set_str(m_y, y_flat(i).c_str(), 10);
	mpz_invert(m_r, m_x, m_y);
	string r = std::string(mpz_get_str(NULL, 10, m_r));
	result_flat(i) = r;
	mpz_clears(m_x, m_y, m_r, NULL);
      }
    };
    auto worker_threads = ctx->device()->tensorflow_cpu_worker_threads();
    const int64 element_cost = 100;
    Shard(worker_threads->num_threads - 1, worker_threads->workers,
          x_flat.size(), element_cost, RunTask);
  }
};

REGISTER_OP("GmpInvert")
    .Input("x: string")
    .Input("y: string")
    .Output("result: string")
    .SetShapeFn([](shape_inference::InferenceContext* c) {
      c->set_output(0, c->input(0));
      return Status::OK();
    });

REGISTER_KERNEL_BUILDER(
    Name("GmpInvert").Device(DEVICE_CPU),
    GmpInvertOp);

class GmpModOp : public OpKernel {
 public:
  explicit GmpModOp(OpKernelConstruction* ctx)
      : OpKernel(ctx) {}

  void Compute(OpKernelContext* ctx) override {
    const Tensor* x_tensor;
    const Tensor* y_tensor;
    OP_REQUIRES_OK(ctx, ctx->input("x", &x_tensor));
    OP_REQUIRES_OK(ctx, ctx->input("y", &y_tensor));
    const auto& x_flat = x_tensor->flat<string>();
    const auto& y_flat = y_tensor->flat<string>();
    Tensor* result_tensor = nullptr;
    OP_REQUIRES_OK(ctx, ctx->allocate_output("result",
	x_tensor->shape(), &result_tensor));
    auto result_flat = result_tensor->flat<string>();
    auto RunTask = [this, &x_flat, &y_flat, &result_flat](int64 start, int64 end) {
      typedef decltype(x_flat.size()) Index;
      for (Index i = start; i < end; ++i) {
	mpz_t m_x, m_y, m_r;
	mpz_inits(m_x, m_y, m_r, NULL);
	mpz_set_str(m_x, x_flat(i).c_str(), 10);
	mpz_set_str(m_y, y_flat(i).c_str(), 10);
	mpz_mod(m_r, m_x, m_y);
	string r = std::string(mpz_get_str(NULL, 10, m_r));
	result_flat(i) = r;
	mpz_clears(m_x, m_y, m_r, NULL);
      }
    };
    auto worker_threads = ctx->device()->tensorflow_cpu_worker_threads();
    const int64 element_cost = 100;
    Shard(worker_threads->num_threads - 1, worker_threads->workers,
          x_flat.size(), element_cost, RunTask);
  }
};

REGISTER_OP("GmpMod")
    .Input("x: string")
    .Input("y: string")
    .Output("result: string")
    .SetShapeFn([](shape_inference::InferenceContext* c) {
      c->set_output(0, c->input(0));
      return Status::OK();
    });

REGISTER_KERNEL_BUILDER(
    Name("GmpMod").Device(DEVICE_CPU),
    GmpModOp);

class GmpSubOp : public OpKernel {
 public:
  explicit GmpSubOp(OpKernelConstruction* ctx)
      : OpKernel(ctx) {}

  void Compute(OpKernelContext* ctx) override {
    const Tensor* x_tensor;
    const Tensor* y_tensor;
    OP_REQUIRES_OK(ctx, ctx->input("x", &x_tensor));
    OP_REQUIRES_OK(ctx, ctx->input("y", &y_tensor));
    const auto& x_flat = x_tensor->flat<string>();
    const auto& y_flat = y_tensor->flat<string>();
    Tensor* result_tensor = nullptr;
    OP_REQUIRES_OK(ctx, ctx->allocate_output("result",
	x_tensor->shape(), &result_tensor));
    auto result_flat = result_tensor->flat<string>();
    auto RunTask = [this, &x_flat, &y_flat, &result_flat](int64 start, int64 end) {
      typedef decltype(x_flat.size()) Index;
      for (Index i = start; i < end; ++i) {
	mpz_t m_x, m_y, m_r;
	mpz_inits(m_x, m_y, m_r, NULL);
	mpz_set_str(m_x, x_flat(i).c_str(), 10);
	mpz_set_str(m_y, y_flat(i).c_str(), 10);
	mpz_sub(m_r, m_x, m_y);
        string r = std::string(mpz_get_str(NULL, 10, m_r));
	result_flat(i) = r;
	mpz_clears(m_x, m_y, m_r, NULL);
      }
    };
    auto worker_threads = ctx->device()->tensorflow_cpu_worker_threads();
    const int64 element_cost = 100;
    Shard(worker_threads->num_threads - 1, worker_threads->workers,
          x_flat.size(), element_cost, RunTask);
  }
};

REGISTER_OP("GmpSub")
    .Input("x: string")
    .Input("y: string")
    .Output("result: string")
    .SetShapeFn([](shape_inference::InferenceContext* c) {
      c->set_output(0, c->input(0));
      return Status::OK();
    });

REGISTER_KERNEL_BUILDER(
    Name("GmpSub").Device(DEVICE_CPU),
    GmpSubOp);

class GmpAddOp : public OpKernel {
 public:
  explicit GmpAddOp(OpKernelConstruction* ctx)
      : OpKernel(ctx) {}

  void Compute(OpKernelContext* ctx) override {
    const Tensor* x_tensor;
    const Tensor* y_tensor;
    OP_REQUIRES_OK(ctx, ctx->input("x", &x_tensor));
    OP_REQUIRES_OK(ctx, ctx->input("y", &y_tensor));
    const auto& x_flat = x_tensor->flat<string>();
    const auto& y_flat = y_tensor->flat<string>();
    Tensor* result_tensor = nullptr;
    OP_REQUIRES_OK(ctx, ctx->allocate_output("result",
	x_tensor->shape(), &result_tensor));
    auto result_flat = result_tensor->flat<string>();
    auto RunTask = [this, &x_flat, &y_flat, &result_flat](int64 start, int64 end) {
      typedef decltype(x_flat.size()) Index;
      for (Index i = start; i < end; ++i) {
	mpz_t m_x, m_y, m_r;
	mpz_inits(m_x, m_y, m_r, NULL);
	mpz_set_str(m_x, x_flat(i).c_str(), 10);
	mpz_set_str(m_y, y_flat(i).c_str(), 10);
	mpz_add(m_r, m_x, m_y);
	string r = std::string(mpz_get_str(NULL, 10, m_r));
	result_flat(i) = r;
	mpz_clears(m_x, m_y, m_r, NULL);
      }
    };
    auto worker_threads = ctx->device()->tensorflow_cpu_worker_threads();
    const int64 element_cost = 100;
    Shard(worker_threads->num_threads - 1, worker_threads->workers,
          x_flat.size(), element_cost, RunTask);
  }
};

REGISTER_OP("GmpAdd")
    .Input("x: string")
    .Input("y: string")
    .Output("result: string")
    .SetShapeFn([](shape_inference::InferenceContext* c) {
      c->set_output(0, c->input(0));
      return Status::OK();
    });

REGISTER_KERNEL_BUILDER(
    Name("GmpAdd").Device(DEVICE_CPU),
    GmpAddOp);

class GmpMulOp : public OpKernel {
 public:
  explicit GmpMulOp(OpKernelConstruction* ctx)
      : OpKernel(ctx) {}

  void Compute(OpKernelContext* ctx) override {
    const Tensor* x_tensor;
    const Tensor* y_tensor;
    OP_REQUIRES_OK(ctx, ctx->input("x", &x_tensor));
    OP_REQUIRES_OK(ctx, ctx->input("y", &y_tensor));
    const auto& x_flat = x_tensor->flat<string>();
    const auto& y_flat = y_tensor->flat<string>();
    Tensor* result_tensor = nullptr;
    OP_REQUIRES_OK(ctx, ctx->allocate_output("result",
	x_tensor->shape(), &result_tensor));
    auto result_flat = result_tensor->flat<string>();
    auto RunTask = [this, &x_flat, &y_flat, &result_flat](int64 start, int64 end) {
      typedef decltype(x_flat.size()) Index;
      for (Index i = start; i < end; ++i) {
	mpz_t m_x, m_y, m_r;
	mpz_inits(m_x, m_y, m_r, NULL);
	mpz_set_str(m_x, x_flat(i).c_str(), 10);
	mpz_set_str(m_y, y_flat(i).c_str(), 10);
	mpz_mul(m_r, m_x, m_y);
	string r = std::string(mpz_get_str(NULL, 10, m_r));
	result_flat(i) = r;
	mpz_clears(m_x, m_y, m_r, NULL);
      }
    };
    auto worker_threads = ctx->device()->tensorflow_cpu_worker_threads();
    const int64 element_cost = 100;
    Shard(worker_threads->num_threads - 1, worker_threads->workers,
          x_flat.size(), element_cost, RunTask);
  }
};

REGISTER_OP("GmpMul")
    .Input("x: string")
    .Input("y: string")
    .Output("result: string")
    .SetShapeFn([](shape_inference::InferenceContext* c) {
      c->set_output(0, c->input(0));
      return Status::OK();
    });

REGISTER_KERNEL_BUILDER(
    Name("GmpMul").Device(DEVICE_CPU),
    GmpMulOp);

class GmpPowOp : public OpKernel {
 public:
  explicit GmpPowOp(OpKernelConstruction* ctx)
      : OpKernel(ctx) {}

  void Compute(OpKernelContext* ctx) override {
    const Tensor* x_tensor;
    const Tensor* y_tensor;
    OP_REQUIRES_OK(ctx, ctx->input("x", &x_tensor));
    OP_REQUIRES_OK(ctx, ctx->input("y", &y_tensor));
    const auto& x_flat = x_tensor->flat<string>();
    const auto& y_flat = y_tensor->flat<int64>();
    Tensor* result_tensor = nullptr;
    OP_REQUIRES_OK(ctx, ctx->allocate_output("result",
	x_tensor->shape(), &result_tensor));
    auto result_flat = result_tensor->flat<string>();
    auto RunTask = [this, &x_flat, &y_flat, &result_flat](int64 start, int64 end) {
      typedef decltype(x_flat.size()) Index;
      for (Index i = start; i < end; ++i) {
	mpz_t m_x, m_r;
	mpz_inits(m_x, m_r, NULL);
	mpz_set_str(m_x, x_flat(i).c_str(), 10);
	mpz_pow_ui(m_r, m_x, y_flat(i));
	string r = std::string(mpz_get_str(NULL, 10, m_r));
	result_flat(i) = r;
	mpz_clears(m_x, m_r, NULL);
      }
    };
    auto worker_threads = ctx->device()->tensorflow_cpu_worker_threads();
    const int64 element_cost = 100;
    Shard(worker_threads->num_threads - 1, worker_threads->workers,
          x_flat.size(), element_cost, RunTask);
  }
};

REGISTER_OP("GmpPow")
    .Input("x: string")
    .Input("y: int64")
    .Output("result: string")
    .SetShapeFn([](shape_inference::InferenceContext* c) {
      c->set_output(0, c->input(0));
      return Status::OK();
    });

REGISTER_KERNEL_BUILDER(
    Name("GmpPow").Device(DEVICE_CPU),
    GmpPowOp);

class GmpDivOp : public OpKernel {
 public:
  explicit GmpDivOp(OpKernelConstruction* ctx)
      : OpKernel(ctx) {}

  void Compute(OpKernelContext* ctx) override {
    const Tensor* x_tensor;
    const Tensor* y_tensor;
    OP_REQUIRES_OK(ctx, ctx->input("x", &x_tensor));
    OP_REQUIRES_OK(ctx, ctx->input("y", &y_tensor));
    const auto& x_flat = x_tensor->flat<string>();
    const auto& y_flat = y_tensor->flat<string>();
    Tensor* result_tensor = nullptr;
    OP_REQUIRES_OK(ctx, ctx->allocate_output("result",
	x_tensor->shape(), &result_tensor));
    auto result_flat = result_tensor->flat<string>();
    auto RunTask = [this, &x_flat, &y_flat, &result_flat](int64 start, int64 end) {
      typedef decltype(x_flat.size()) Index;
      for (Index i = start; i < end; ++i) {
	mpz_t m_x, m_y, m_r;
	mpz_inits(m_x, m_y, m_r, NULL);
	mpz_set_str(m_x, x_flat(i).c_str(), 10);
	mpz_set_str(m_y, y_flat(i).c_str(), 10);
	mpz_div(m_r, m_x, m_y);
	string r = std::string(mpz_get_str(NULL, 10, m_r));
	result_flat(i) = r;
	mpz_clears(m_x, m_y, m_r, NULL);
      }
    };
    auto worker_threads = ctx->device()->tensorflow_cpu_worker_threads();
    const int64 element_cost = 100;
    Shard(worker_threads->num_threads - 1, worker_threads->workers,
          x_flat.size(), element_cost, RunTask);
  }
};

REGISTER_OP("GmpDiv")
    .Input("x: string")
    .Input("y: string")
    .Output("result: string")
    .SetShapeFn([](shape_inference::InferenceContext* c) {
      c->set_output(0, c->input(0));
      return Status::OK();
    });

REGISTER_KERNEL_BUILDER(
    Name("GmpDiv").Device(DEVICE_CPU),
    GmpDivOp);

class GmpCmpOp : public OpKernel {
 public:
  explicit GmpCmpOp(OpKernelConstruction* ctx)
      : OpKernel(ctx) {}

  void Compute(OpKernelContext* ctx) override {
    const Tensor* x_tensor;
    const Tensor* y_tensor;
    OP_REQUIRES_OK(ctx, ctx->input("x", &x_tensor));
    OP_REQUIRES_OK(ctx, ctx->input("y", &y_tensor));
    const auto& x_flat = x_tensor->flat<string>();
    const auto& y_flat = y_tensor->flat<string>();
    Tensor* result_tensor = nullptr;
    OP_REQUIRES_OK(ctx, ctx->allocate_output("result",
	x_tensor->shape(), &result_tensor));
    auto result_flat = result_tensor->flat<int32>();
    auto RunTask = [this, &x_flat, &y_flat, &result_flat](int64 start, int64 end) {
      typedef decltype(x_flat.size()) Index;
      for (Index i = start; i < end; ++i) {
	mpz_t m_x, m_y;
	mpz_inits(m_x, m_y, NULL);
	mpz_set_str(m_x, x_flat(i).c_str(), 10);
	mpz_set_str(m_y, y_flat(i).c_str(), 10);
	result_flat(i) = mpz_cmp(m_x, m_y);
	mpz_clears(m_x, m_y, NULL);
      }
    };
    auto worker_threads = ctx->device()->tensorflow_cpu_worker_threads();
    const int64 element_cost = 100;
    Shard(worker_threads->num_threads - 1, worker_threads->workers,
          x_flat.size(), element_cost, RunTask);
  }
};

REGISTER_OP("GmpCmp")
    .Input("x: string")
    .Input("y: string")
    .Output("result: int32")
    .SetShapeFn([](shape_inference::InferenceContext* c) {
      c->set_output(0, c->input(0));
      return Status::OK();
    });

REGISTER_KERNEL_BUILDER(
    Name("GmpCmp").Device(DEVICE_CPU),
    GmpCmpOp);

class GmpPowModOp : public OpKernel {
 public:
  explicit GmpPowModOp(OpKernelConstruction* ctx)
      : OpKernel(ctx) {}

  void Compute(OpKernelContext* ctx) override {
    const Tensor* x_tensor;
    const Tensor* y_tensor;
    const Tensor* z_tensor;
    OP_REQUIRES_OK(ctx, ctx->input("x", &x_tensor));
    OP_REQUIRES_OK(ctx, ctx->input("y", &y_tensor));
    OP_REQUIRES_OK(ctx, ctx->input("z", &z_tensor));
    const auto& x_flat = x_tensor->flat<string>();
    const auto& y_flat = y_tensor->flat<string>();
    const auto& z_flat = z_tensor->flat<string>();
    Tensor* result_tensor = nullptr;
    OP_REQUIRES_OK(ctx, ctx->allocate_output("result",
	x_tensor->shape(), &result_tensor));
    auto result_flat = result_tensor->flat<string>();
    auto RunTask = [this, &x_flat, &y_flat, &z_flat, &result_flat](int64 start, int64 end) {
      typedef decltype(x_flat.size()) Index;
      for (Index i = start; i < end; ++i) {
	mpz_t m_x, m_y, m_z, m_r;
	mpz_inits(m_x, m_y, m_z, m_r, NULL);
	mpz_set_str(m_x, x_flat(i).c_str(), 10);
	mpz_set_str(m_y, y_flat(i).c_str(), 10);
	mpz_set_str(m_z, z_flat(i).c_str(), 10);
	mpz_powm(m_r, m_x, m_y, m_z);
	string r = std::string(mpz_get_str(NULL, 10, m_r));
	result_flat(i) = r;
	mpz_clears(m_x, m_y, m_z, m_r, NULL);
      }
    };
    auto worker_threads = ctx->device()->tensorflow_cpu_worker_threads();
    const int64 element_cost = 100;
    Shard(worker_threads->num_threads - 1, worker_threads->workers,
          x_flat.size(), element_cost, RunTask);
  }
};

REGISTER_OP("GmpPowMod")
    .Input("x: string")
    .Input("y: string")
    .Input("z: string")
    .Output("result: string")
    .SetShapeFn([](shape_inference::InferenceContext* c) {
      c->set_output(0, c->input(0));
      return Status::OK();
    });

REGISTER_KERNEL_BUILDER(
    Name("GmpPowMod").Device(DEVICE_CPU),
    GmpPowModOp);

} // namespace tensorflow
} // namespace efl

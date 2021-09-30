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
#include "tensorflow/core/framework/op.h"
#include "tensorflow/core/lib/core/errors.h"
#include "tensorflow/core/framework/op_kernel.h"
#include "tensorflow/core/framework/shape_inference.h"
#include "tensorflow/core/framework/common_shape_fns.h"
#include "tensorflow/core/util/work_sharder.h"

namespace tensorflow {
namespace efl {

class FrexpOp : public OpKernel {
 public:
  explicit FrexpOp(OpKernelConstruction* ctx)
      : OpKernel(ctx) {}

  void Compute(OpKernelContext* ctx) override {
    const Tensor* input_tensor;
    OP_REQUIRES_OK(ctx, ctx->input("inputs", &input_tensor));
    const auto& input_flat = input_tensor->flat<float>();
    Tensor* result_tensor = nullptr;
    Tensor* exponent_tensor = nullptr;
    OP_REQUIRES_OK(ctx, ctx->allocate_output("result",
	input_tensor->shape(), &result_tensor));
    OP_REQUIRES_OK(ctx, ctx->allocate_output("exponent",
	input_tensor->shape(), &exponent_tensor));
    auto result_flat = result_tensor->flat<float>();
    auto exponent_flat = exponent_tensor->flat<float>();
    auto RunTask = [this, &input_flat, &result_flat, &exponent_flat](int64 start, int64 end) {
      typedef decltype(input_flat.size()) Index;
      for (Index i = start; i < end; ++i) {
	int exp;
	result_flat(i) = frexp(input_flat(i), &exp);
	exponent_flat(i) = exp;
      }
    };
    auto worker_threads = ctx->device()->tensorflow_cpu_worker_threads();
    const int64 element_cost = 100;
    Shard(worker_threads->num_threads - 1, worker_threads->workers,
          input_flat.size(), element_cost, RunTask);
  }
};

REGISTER_OP("Frexp")
    .Input("inputs: float32")
    .Output("result: float32")
    .Output("exponent: float32")
    .SetShapeFn([](shape_inference::InferenceContext* c) {
      c->set_output(0, c->input(0));
      c->set_output(1, c->input(0));
      return Status::OK();
    });

REGISTER_KERNEL_BUILDER(
    Name("Frexp").Device(DEVICE_CPU),
    FrexpOp);

} // namespace tensorflow
} // namespace efl

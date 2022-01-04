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
#include <gmp.h>
#include "tensorflow/core/framework/op_kernel.h"
#include "tensorflow/core/framework/register_types.h"
#include "tensorflow/core/framework/shape_inference.h"
#include "tensorflow/core/util/work_sharder.h"

#include "gmp_utils.h"

namespace tensorflow {
namespace efl {

REGISTER_OP("ConvertToFixedPoint")
    .Input("t: T")
    .Attr("T: {int8, int16, int32, int64, float, double}")
    .Output("mantissa: int64")
    .Output("exponent: int64")
    .Attr("decrease_precision: bool = false")
    .SetShapeFn([](shape_inference::InferenceContext* c) {
      c->set_output(0, c->input(0));
      c->set_output(1, c->input(0));
      return Status::OK();
    })
    .Doc(R"doc(
Convert integer or float-point tensor to fixed-point tensor.

t: the tensor to be converted.
t = mantissa * 2 ^ exponent
)doc");

template<typename T>
class Convert2FixedPointOp : public OpKernel {
 public:
  explicit Convert2FixedPointOp(OpKernelConstruction* context)
      : OpKernel(context) {
    OP_REQUIRES_OK(context, context->GetAttr("decrease_precision", &float16_));
  }

  void Compute(OpKernelContext* context) override {}

 private:
  static void Int2FixedPoint(OpKernelContext* context) {
    const Tensor* input_tensor = nullptr;
    Tensor* mantissa_tensor = nullptr;
    Tensor* exponent_tensor = nullptr;
    OP_REQUIRES_OK(context, context->input("t", &input_tensor));
    OP_REQUIRES_OK(context, context->allocate_output(0, input_tensor->shape(), &mantissa_tensor));
    OP_REQUIRES_OK(context, context->allocate_output(1, input_tensor->shape(), &exponent_tensor));
    auto input = input_tensor->flat<T>();
    auto mantissa = mantissa_tensor->flat<int64>();
    auto exponent = exponent_tensor->flat<int64>();

    const auto N = input.size();
    for (auto i = 0; i < N; i++) {
      mantissa(i) = input(i);
      exponent(i) = 0;
    }
  }

  bool float16_;
};

template<>
void Convert2FixedPointOp<int8>::Compute(OpKernelContext* context) {
  Int2FixedPoint(context);
}

template<>
void Convert2FixedPointOp<int16>::Compute(OpKernelContext* context) {
  Int2FixedPoint(context);
}

template<>
void Convert2FixedPointOp<int32>::Compute(OpKernelContext* context) {
  Int2FixedPoint(context);
}

template<>
void Convert2FixedPointOp<int64>::Compute(OpKernelContext* context) {
  Int2FixedPoint(context);
}

template<>
void Convert2FixedPointOp<float>::Compute(OpKernelContext* context) {
  const Tensor* input_tensor = nullptr;
  Tensor* mantissa_tensor = nullptr;
  Tensor* exponent_tensor = nullptr;
  OP_REQUIRES_OK(context, context->input("t", &input_tensor));
  OP_REQUIRES_OK(context, context->allocate_output(0, input_tensor->shape(), &mantissa_tensor));
  OP_REQUIRES_OK(context, context->allocate_output(1, input_tensor->shape(), &exponent_tensor));
  auto input = input_tensor->flat<float>();
  auto mantissa = mantissa_tensor->flat<int64>();
  auto exponent = exponent_tensor->flat<int64>();
  
  auto task = [&input, &mantissa, &exponent, context, this] (int64 start, int64 end) {
    for (auto i = start; i < end; i++) {
      auto bits = *(uint32*)&input(i);
      auto sign_exponent = bits >> 23;
      auto sign = sign_exponent >> 8;
      auto exp = ((int)sign_exponent & 0xFF) - 127 - 23;
      int mant;
      if (exp == 0xFF) {
        OP_REQUIRES_OK(context, errors::InvalidArgument("inf value cannot be converted to a fixed-point value."));
      } else {
        mant = (int)bits & 0x7FFFFF;
        if (exp) {
          mant |= 0x800000;
        }
      }
      if (float16_) {
        mant >>= 13;
        exp += 13;
      }

      float f = mant & -mant;
      auto r = (*(unsigned int*)&f >> 23) - 127;
      mant >>= r;
      exp += r;

      if (sign) {
        mantissa(i) = -mant;
      } else {
        mantissa(i) = mant;
      }
      exponent(i) = exp;
    }
  };

  auto worker_threads = context->device()->tensorflow_cpu_worker_threads();
  Shard(worker_threads->num_threads - 1, worker_threads->workers, input.size(), 20, task);
}

template<>
void Convert2FixedPointOp<double>::Compute(OpKernelContext* context) {
  const Tensor* input_tensor = nullptr;
  Tensor* mantissa_tensor = nullptr;
  Tensor* exponent_tensor = nullptr;
  OP_REQUIRES_OK(context, context->input("t", &input_tensor));
  OP_REQUIRES_OK(context, context->allocate_output(0, input_tensor->shape(), &mantissa_tensor));
  OP_REQUIRES_OK(context, context->allocate_output(1, input_tensor->shape(), &exponent_tensor));
  auto input = input_tensor->flat<double>();
  auto mantissa = mantissa_tensor->flat<int64>();
  auto exponent = exponent_tensor->flat<int64>();

  auto task = [&input, &mantissa, &exponent, context, this] (int64 start, int64 end) {
    for (auto i = start; i < end; i++) {
      auto bits = *(uint64*)&input(i);
      auto sign_exponent = bits >> 52;
      auto sign = sign_exponent >> 11;
      auto exp = ((long long)sign_exponent & 0x7FFLL) - 1023 - 52;
      long long mant;
      if (exp == 0x7FFLL) {
        OP_REQUIRES_OK(context, errors::InvalidArgument("inf value cannot be converted to a fixed-point value."));
      } else {
        mant = (long long)bits & 0xFFFFFFFFFFFFFLL;
        if (exp) {
          mant |= 0x10000000000000LL;
        }
      }
      if (float16_) {
        mant >>= 42;
        exp += 42;
      }

      double d = mant & -mant;
      auto r = (*(unsigned long long*)&d >> 52) - 1023;
      mant >>= r;
      exp += r;

      if (sign) {
        mantissa(i) = -mant;
      } else {
        mantissa(i) = mant;
      }
      exponent(i) = exp;
    }
  };

  auto worker_threads = context->device()->tensorflow_cpu_worker_threads();
  Shard(worker_threads->num_threads - 1, worker_threads->workers, input.size(), 20, task);
}

#define REGISTER_KERNELS(type)                                                 \
  REGISTER_KERNEL_BUILDER(                                                     \
    Name("ConvertToFixedPoint").Device(DEVICE_CPU).TypeConstraint<type>("T"),  \
    Convert2FixedPointOp<type>)

TF_CALL_ALL_TYPES(REGISTER_KERNELS);

REGISTER_OP("FixedPointToFloatPoint")
    .Input("mantissa: T")
    .Attr("T: {string, int64}")
    .Input("exponent: int64")
    .Output("y: dtype")
    .Attr("dtype: {float, double}")
    .SetShapeFn([](shape_inference::InferenceContext* c) {
      c->set_output(0, c->input(0));
      return Status::OK();
    })
    .Doc(R"doc(
Convert a fixed-point value to a float-point value.
y = mantissa * 2 ^ exponent
)doc");

template<typename Tin, typename Tout>
class FixedPointToFloatPointOp : public OpKernel {
 public:
  explicit FixedPointToFloatPointOp(OpKernelConstruction* context) : OpKernel(context) {}

  void Compute(OpKernelContext* context) override {
    const Tensor* mantissa_tensor = nullptr;
    const Tensor* exponent_tensor = nullptr;
    Tensor* y_tensor = nullptr;
    OP_REQUIRES_OK(context, context->input("mantissa", &mantissa_tensor));
    OP_REQUIRES_OK(context, context->input("exponent", &exponent_tensor));
    OP_REQUIRES_OK(context, context->allocate_output(0, mantissa_tensor->shape(), &y_tensor));
    auto mantissa = mantissa_tensor->flat<Tin>();
    auto exponent = exponent_tensor->flat<int64>();
    if (mantissa.size() != exponent.size()) {
      OP_REQUIRES_OK(context, errors::InvalidArgument("mantissa and exponent should be the same size."));
    }
    auto y = y_tensor->flat<Tout>();

    auto task = [this, &mantissa, &exponent, &y] (int64 start, int64 end) {
      mpf_t op;
      mpf_init(op);
      for(auto i = start; i < end; i++) {
        Input2Mpf(op, mantissa(i));
        if (exponent(i) > 0) {
          mpf_mul_2exp(op, op, exponent(i));
        } else if (exponent(i) < 0) {
          mpf_div_2exp(op, op, -exponent(i));
        }
        y(i) = mpf_get_d(op);
      }
      mpf_clear(op);
    };

    auto worker_threads = context->device()->tensorflow_cpu_worker_threads();
    Shard(worker_threads->num_threads - 1, worker_threads->workers, mantissa.size(), 100, task);
  }

 private:
  void Input2Mpf(mpf_t rop, string inputs) {
    mpf_set_str(rop, inputs.c_str(), 16);
  }

  void Input2Mpf(mpf_t rop, int64 inputs) {
    mpz_t op;
    mpz_init(op);
    mpz_set_sll(op, inputs);
    mpf_set_z(rop, op);
    mpz_clear(op);
  }
};

REGISTER_KERNEL_BUILDER(Name("FixedPointToFloatPoint")
                            .Device(DEVICE_CPU)
                            .TypeConstraint<string>("T")
                            .TypeConstraint<float>("dtype"),
                        FixedPointToFloatPointOp<string, float>);
REGISTER_KERNEL_BUILDER(Name("FixedPointToFloatPoint")
                            .Device(DEVICE_CPU)
                            .TypeConstraint<string>("T")
                            .TypeConstraint<double>("dtype"),
                        FixedPointToFloatPointOp<string, double>);
REGISTER_KERNEL_BUILDER(Name("FixedPointToFloatPoint")
                            .Device(DEVICE_CPU)
                            .TypeConstraint<int64>("T")
                            .TypeConstraint<float>("dtype"),
                        FixedPointToFloatPointOp<int64, float>);
REGISTER_KERNEL_BUILDER(Name("FixedPointToFloatPoint")
                            .Device(DEVICE_CPU)
                            .TypeConstraint<int64>("T")
                            .TypeConstraint<double>("dtype"),
                        FixedPointToFloatPointOp<int64, double>);

} // efl
} // tensorflow

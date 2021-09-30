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

#include <limits>

#include "tensorflow/core/framework/op.h"
#include "tensorflow/core/framework/op_kernel.h"
#include "tensorflow/core/framework/shape_inference.h"
#include "tensorflow/core/lib/core/errors.h"
#include "tensorflow/core/framework/resource_var.h"
#include "tensorflow/core/platform/env.h"

using namespace tensorflow;  // NOLINT

namespace efl {

struct Stage {
  std::vector<string*> result;
  std::vector<int64*> order;
  std::vector<int64*> status;
};

Status GetStage(
    Tensor* name, Tensor* result, Tensor* order, Tensor* status, int64 worker_num, 
    int64 stage_idx, const string& stage_name, Stage* stage) {
  TensorShape name_shape = name->shape();
  if (name_shape.dims() != 1) {
    return errors::InvalidArgument("name shape is not right.");
  }
  if (name->dtype() != DataType::DT_STRING) {
    return errors::InvalidArgument("name dtype is not right.");
  }
  int64 stage_size = name_shape.dim_size(0);
  if (result->shape() != TensorShape({stage_size, worker_num})) {
    return errors::InvalidArgument("result shape is not right.");
  }
  if (result->dtype() != DataType::DT_STRING) {
    return errors::InvalidArgument("result dtype is not right.");
  }
  if (order->shape() != TensorShape({stage_size, worker_num})) {
    return errors::InvalidArgument("order shape is not right.");
  }
  if (order->dtype() != DataType::DT_INT64) {
    return errors::InvalidArgument("order dtype is not right.");
  }
  if (status->shape() != TensorShape({stage_size, worker_num})) {
    return errors::InvalidArgument("status shape is not right.");
  }
  if (status->dtype() != DataType::DT_INT64) {
    return errors::InvalidArgument("status dtype is not right.");
  }
  if (stage_idx > stage_size) {
    return errors::InvalidArgument("stage idx is to big.");
  }
  if (stage_idx == stage_size) {
    if (stage_size != 0 && status->matrix<int64>()(stage_size - 1, 0) != 2) {
      return errors::InvalidArgument("stage is mismatched.");
    }
    Tensor new_name(
        DataType::DT_STRING, TensorShape({stage_size + 1}));
    Tensor new_result(
        DataType::DT_STRING, TensorShape({stage_size + 1, worker_num}));
    Tensor new_order(
        DataType::DT_INT64, TensorShape({stage_size + 1, worker_num}));
    Tensor new_status(
        DataType::DT_INT64, TensorShape({stage_size + 1, worker_num}));
    auto name_flat = name->flat<string>();
    auto new_name_flat = new_name.flat<string>();
    auto result_flat = result->matrix<string>();
    auto new_result_flat = new_result.matrix<string>();
    auto order_flat = order->matrix<int64>();
    auto new_order_flat = new_order.matrix<int64>();
    auto status_flat = status->matrix<int64>();
    auto new_status_flat = new_status.matrix<int64>();
    for (int i = 0; i < stage_size; i++) {
      new_name_flat(i) = name_flat(i);
      for (int j = 0; j < worker_num; j++) {
        new_result_flat(i, j) = result_flat(i, j);
        new_order_flat(i, j) = order_flat(i, j);
        new_status_flat(i, j) = status_flat(i, j);
      }
    }
    new_name_flat(stage_size) = stage_name;
    for (int i = 0; i < worker_num; i++) {
      new_result_flat(stage_size, i) = "";
      new_order_flat(stage_size, i) = -1;
      new_status_flat(stage_size, i) = 0;
    }
    *name = new_name;
    *result = new_result;
    *order = new_order;
    *status = new_status;
  }
  auto name_flat = name->flat<string>();
  auto result_flat = result->matrix<string>();
  auto order_flat = order->matrix<int64>();
  auto status_flat = status->matrix<int64>();
  if (name_flat(stage_idx) != stage_name) {
    return errors::InvalidArgument("stage name mistached.");
  }
  stage->result.clear();
  stage->status.clear();
  stage->order.clear();
  for (int i = 0; i < worker_num; i++) {
    stage->result.push_back(&result_flat(stage_idx, i));
    stage->order.push_back(&order_flat(stage_idx, i));
    stage->status.push_back(&status_flat(stage_idx, i));
  }
  return Status::OK();
}

class StageStatus : public OpKernel {
 public:
  explicit StageStatus(OpKernelConstruction* context) : OpKernel(context) {
    OP_REQUIRES_OK(context, context->GetAttr("worker_num", &worker_num_));
    OP_REQUIRES_OK(context, context->GetAttr("worker_id", &worker_id_));
  }

  void Compute(OpKernelContext* ctx) override {
    Var* name_var = nullptr;
    Var* result_var = nullptr;
    Var* order_var = nullptr;
    Var* status_var = nullptr;
    OP_REQUIRES_OK(ctx, LookupResource(
          ctx, HandleFromInput(ctx, 0), &name_var));
    core::ScopedUnref name_unref(name_var);
    OP_REQUIRES_OK(ctx, LookupResource(
          ctx, HandleFromInput(ctx, 1), &result_var));
    core::ScopedUnref result_unref(result_var);
    OP_REQUIRES_OK(ctx, LookupResource(
          ctx, HandleFromInput(ctx, 2), &order_var));
    core::ScopedUnref order_unref(order_var);
    OP_REQUIRES_OK(ctx, LookupResource(
          ctx, HandleFromInput(ctx, 3), &status_var));
    core::ScopedUnref status_unref(status_var);
    int64 stage_idx = ctx->input(4).scalar<int64>()();
    string stage_name = ctx->input(5).scalar<string>()();
    float finish_ratio = ctx->input(6).scalar<float>()();

    mutex_lock name_lock(*name_var->mu());
    mutex_lock result_lock(*result_var->mu());
    mutex_lock order_lock(*order_var->mu());
    mutex_lock status_lock(*status_var->mu());
    Stage stage;
    OP_REQUIRES_OK(ctx, GetStage(
          name_var->tensor(), result_var->tensor(), order_var->tensor(),
          status_var->tensor(), worker_num_, stage_idx, stage_name, &stage));
    OP_REQUIRES(ctx, stage.status.size() > static_cast<size_t>(worker_id_),
        errors::InvalidArgument("worker index overflow."));
    OP_REQUIRES(ctx, stage.status.size() == static_cast<size_t>(worker_num_),
        errors::InvalidArgument("worker num is mismatched."));

    if (finish_ratio < 1 && 
        *stage.status[worker_id_] != 2 &&
        IsChiefFinished(stage.order)) {
      RewriteStageResultByFinishRatio(
          stage_name, finish_ratio, &stage);
    }

    Tensor *status_out, *result_out, *order_out;
    OP_REQUIRES_OK(
        ctx, ctx->allocate_output(0, {}, &status_out));
    OP_REQUIRES_OK(
        ctx, ctx->allocate_output(1, {worker_num_}, &result_out));
    OP_REQUIRES_OK(
        ctx, ctx->allocate_output(2, {worker_num_}, &order_out));
    int64 status = *stage.status[worker_id_];
    status_out->scalar<int64>()() = status;
    auto result_out_flat = result_out->flat<string>();
    auto order_out_flat = order_out->flat<int64>();
    for (int64 i = 0; i < worker_num_; i++) {
      result_out_flat(i) = *stage.result[i];
      order_out_flat(i) = *stage.order[i];
    }
  }

  inline bool IsChiefFinished(const std::vector<int64*>& order) {
    for (auto& it: order) {
      if (*it == 0) {
        return true;
      }
    }

    return false;
  }

 private:
  inline void RewriteStageResultByFinishRatio(
      const std::string& stage_name, float finish_ratio, Stage* stage) {
    auto& status = stage->status;
    auto& order = stage->order;
    int finish_num = 0;
    while (*order[finish_num] != -1) {
      finish_num++;
    }

    if ((float)finish_num / worker_num_ >= finish_ratio) {
      fprintf(stderr, "stage[%s] exceed finish ratio[%f], current stage finish\n", 
              stage_name.c_str(), finish_ratio);
      for (size_t i = 0; i < status.size(); ++i) {
        *(status[i]) = 2;
      }
    }
  }

 private:
  int64 worker_num_;
  int64 worker_id_;
};

class StageUpdate : public OpKernel {
 public:
  explicit StageUpdate(OpKernelConstruction* context) : OpKernel(context) {
    OP_REQUIRES_OK(context, context->GetAttr("worker_num", &worker_num_));
    OP_REQUIRES_OK(context, context->GetAttr("worker_id", &worker_id_));
  }

  void Compute(OpKernelContext* ctx) override {
    Var* name_var = nullptr;
    Var* result_var = nullptr;
    Var* order_var = nullptr;
    Var* status_var = nullptr;

    OP_REQUIRES_OK(ctx, LookupResource(
          ctx, HandleFromInput(ctx, 0), &name_var));
    core::ScopedUnref name_unref(name_var);
    OP_REQUIRES_OK(ctx, LookupResource(
          ctx, HandleFromInput(ctx, 1), &result_var));
    core::ScopedUnref result_unref(result_var);
    OP_REQUIRES_OK(ctx, LookupResource(
          ctx, HandleFromInput(ctx, 2), &order_var));
    core::ScopedUnref order_unref(order_var);
    OP_REQUIRES_OK(ctx, LookupResource(
          ctx, HandleFromInput(ctx, 3), &status_var));
    core::ScopedUnref status_unref(status_var);

    mutex_lock name_lock(*name_var->mu());
    mutex_lock result_lock(*result_var->mu());
    mutex_lock order_lock(*order_var->mu());
    mutex_lock status_lock(*status_var->mu());

    int64 stage_idx = ctx->input(4).scalar<int64>()();
    string stage_name = ctx->input(5).scalar<string>()();
    string stage_result = ctx->input(6).scalar<string>()();

    Stage stage;
    OP_REQUIRES_OK(ctx, GetStage(
          name_var->tensor(), result_var->tensor(), order_var->tensor(),
          status_var->tensor(), worker_num_, stage_idx, stage_name, &stage));
    OP_REQUIRES(ctx, stage.status.size() > static_cast<size_t>(worker_id_),
        errors::InvalidArgument("worker index overflow."));
    OP_REQUIRES(ctx, stage.status.size() == static_cast<size_t>(worker_num_),
        errors::InvalidArgument("worker num is mismatched."));
    OP_REQUIRES(ctx, *stage.status[worker_id_] != 1,
        errors::InvalidArgument("stage is already updated."));
    int order = -1;
    for (int i = 0; i < worker_num_; i++) {
      if (*stage.order[i] == -1) {
        order = i;
        break;
      }
    }

    OP_REQUIRES(ctx, order != -1,
        errors::InvalidArgument("stage order is full."));
    *stage.order[order] = worker_id_;
    *stage.result[worker_id_] = stage_result;
    if (*stage.status[worker_id_] == 2) {
      return;
    }

    *stage.status[worker_id_] = 1;
    if (order == worker_num_ - 1) {
      for (int i = 0; i < worker_num_; i++) {
        *stage.status[i] = 2;
      }
    }
  }

 private:
  int64 worker_num_;
  int64 worker_id_;
};

REGISTER_OP("StageStatus")
    .Input("name_var: resource")
    .Input("result_var: resource")
    .Input("order_var: resource")
    .Input("status_var: resource")
    .Input("stage_idx: int64")
    .Input("stage_name: string")
    .Input("finish_ratio: float")
    .Attr("worker_id: int")
    .Attr("worker_num: int")
    .Output("status: int64")
    .Output("result: string")
    .Output("order: int64");

REGISTER_OP("StageUpdate")
    .Input("name_var: resource")
    .Input("result_var: resource")
    .Input("order_var: resource")
    .Input("status_var: resource")
    .Input("stage_idx: int64")
    .Input("stage_name: string")
    .Input("stage_result: string")
    .Attr("worker_id: int")
    .Attr("worker_num: int");

REGISTER_KERNEL_BUILDER(
    Name("StageStatus").Device(tensorflow::DEVICE_CPU), StageStatus);

REGISTER_KERNEL_BUILDER(
    Name("StageUpdate").Device(tensorflow::DEVICE_CPU), StageUpdate);

}  // namespace efl


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

#include <chrono>
#include <deque>
#include <mutex>
#include <vector>

#include "tensorflow/core/framework/dataset_stateful_op_whitelist.h"
#include "tensorflow/core/framework/resource_mgr.h"
#include "tensorflow/core/framework/shape_inference.h"
#include "tensorflow/core/lib/core/threadpool.h"

namespace tensorflow {
namespace efl {

using shape_inference::InferenceContext;
const char EndFileDefaultName[] = "__DATA_IO_END_FILE_NAME__";

class WorkQueue : public ResourceBase {
 public:
  WorkQueue(const string& name, const bool& set_end_file) : name_(name), set_end_file_(set_end_file), is_closed_(false) {}

  ~WorkQueue() { Close(); }

  string DebugString() const override {
    return "WorkQueue";
  }

  int64 MemoryUsed() const override {
    return static_cast<int64>(queue_.size() * DataTypeSize(DT_STRING));
  }

  Status Put(const Tensor& inputs) {
    const int64 num_puts = inputs.shape().dim_size(0);

    std::unique_lock<std::mutex> lock(mu_);
    if (TF_PREDICT_FALSE(is_closed_)) {
      lock.unlock();
      take_cv_.notify_all();
      LOG(WARNING) << "Work queue " << name_ << " reinitialized.";

      return Status::OK();
    }

    for (int64 i = 0; i < num_puts; ++i) {
      queue_.push_back(inputs.flat<string>()(i));
    }

    lock.unlock();
    take_cv_.notify_all();

    return Status::OK();
  }

  Status Take(Tensor* output) {
    std::unique_lock<std::mutex> lock(mu_);

    take_cv_.wait(lock, [this]() { return !queue_.empty() || is_closed_; });

    if (TF_PREDICT_FALSE(queue_.empty() && is_closed_)) {
      return Status(errors::OutOfRange(
          strings::StrCat("All works in work queue ", name_, " are taken.")));
    }

    output->scalar<string>().setConstant(std::move(queue_.front()));
    queue_.pop_front();

    return Status::OK();
  }

  Status GetSize(Tensor* size) {
    std::unique_lock<std::mutex> lock(mu_);
    size->scalar<int64>().setConstant(static_cast<int64>(queue_.size()));
    return Status::OK();
  }

  Status Restore(const Tensor& restorable) {
    const int64 num_works = restorable.shape().dim_size(0);

    std::unique_lock<std::mutex> lock(mu_);

    queue_.clear();
    for (int64 i = 0; i < num_works; ++i) {
      queue_.push_back(restorable.flat<string>()(i));
    }
    if (set_end_file_) {
      queue_.push_back(EndFileDefaultName);
    }

    lock.unlock();
    take_cv_.notify_all();
    return Status::OK();
  }

  Status Save(OpKernelContext* ctx, Tensor** saveable) {
    std::unique_lock<std::mutex> lock(mu_);

    int queue_real_size = set_end_file_ ? queue_.size() - 1 : queue_.size();
    queue_real_size = std::max(0, queue_real_size);
    TF_RETURN_IF_ERROR(ctx->allocate_output(
        0, TensorShape({static_cast<int64>(queue_real_size)}), saveable));
    for (size_t i = 0; i < queue_real_size; ++i) {
      (*saveable)->flat<string>()(i) = queue_[i];
    }

    return Status::OK();
  }

  Status Close() {
    std::unique_lock<std::mutex> lock(mu_);

    if (is_closed_) {
      return Status::OK();
    }

    if (set_end_file_) {
      queue_.push_back(EndFileDefaultName);
    }

    is_closed_ = true;

    lock.unlock();
    take_cv_.notify_all();
    return Status::OK();
  }

  void Schedule(int64 num_threads, std::function<void()> fn) {
    std::unique_lock<std::mutex> lock(mu_);
    if (threads_) {
      lock.unlock();
      threads_->Schedule(fn);
      return;
    }

    threads_.reset(
        new thread::ThreadPool(Env::Default(), ThreadOptions(),
                               strings::StrCat("work_queue_threads_", name_),
                               num_threads, false /* low_latency_hint */));

    lock.unlock();
    threads_->Schedule(fn);
  }

 private:
  std::deque<string> queue_;
  string name_;
  bool set_end_file_;
  bool is_closed_;
  std::mutex mu_;
  std::condition_variable take_cv_;
  std::shared_ptr<thread::ThreadPool> threads_;
};

REGISTER_RESOURCE_HANDLE_OP(WorkQueue);

REGISTER_RESOURCE_HANDLE_KERNEL(WorkQueue);

REGISTER_OP("WorkQueueIsInitialized")
    .Output("is_initialized: bool")
    .Input("handle: resource")
    .SetShapeFn(tensorflow::shape_inference::ScalarShape)
    .Doc(R"doc(
Checks whether a work queue has been initialized.

is_initialized: True if the work queue is initialized.
handle: Handle of a work queue.
)doc");

REGISTER_KERNEL_BUILDER(Name("WorkQueueIsInitialized").Device(DEVICE_CPU),
                        IsResourceInitialized<WorkQueue>);

REGISTER_OP("WorkQueueCreate")
    .Input("handle: resource")
    .Attr("shared_name: string")
    .Attr("set_end_file: bool=false")
    .SetShapeFn(tensorflow::shape_inference::NoOutputs)
    .Doc(R"doc(
Creates a work queue and returns a handle to it.

handle: Handle of a work queue.
shared_name: Name of the work queue.
set_end_file: Set a end flag at end of queue.
)doc");

class WorkQueueCreateOp : public OpKernel {
 public:
  explicit WorkQueueCreateOp(OpKernelConstruction* ctx) : OpKernel(ctx) {
    OP_REQUIRES_OK(ctx, ctx->GetAttr("shared_name", &shared_name_));
    OP_REQUIRES_OK(ctx, ctx->GetAttr("set_end_file", &set_end_file_));
  }

  void Compute(OpKernelContext* ctx) override {
    WorkQueue* work_queue = new WorkQueue(shared_name_, set_end_file_);
    Status s = CreateResource(ctx, HandleFromInput(ctx, 0), work_queue);
    if (!s.ok() && s.code() != error::ALREADY_EXISTS) {
      OP_REQUIRES(ctx, false, s);
    }
  }

 private:
  string shared_name_;
  bool set_end_file_;
};

REGISTER_KERNEL_BUILDER(Name("WorkQueueCreate").Device(DEVICE_CPU),
                        WorkQueueCreateOp);

REGISTER_OP("WorkQueueClose")
    .Input("handle: resource")
    .SetShapeFn(shape_inference::NoOutputs)
    .SetIsStateful()
    .Doc(R"doc(
Closes a work queue.

handle: Handle of a work queue.
)doc");

class WorkQueueCloseOp : public OpKernel {
 public:
  explicit WorkQueueCloseOp(OpKernelConstruction* ctx) : OpKernel(ctx) {}

  void Compute(OpKernelContext* ctx) override {
    WorkQueue* work_queue;
    OP_REQUIRES_OK(ctx,
                   LookupResource(ctx, HandleFromInput(ctx, 0), &work_queue));
    OP_REQUIRES_OK(ctx, work_queue->Close());
  }
};

REGISTER_KERNEL_BUILDER(Name("WorkQueueClose").Device(DEVICE_CPU),
                        WorkQueueCloseOp);

REGISTER_OP("WorkQueueRestore")
    .Input("handle: resource")
    .Input("works: string")
    .SetShapeFn(shape_inference::NoOutputs)
    .SetIsStateful()
    .Doc(R"doc(
Recovers a work queue from saved tensor.

handle: Handle of a work queue.
works: A tensor containing works.
)doc");

class WorkQueueRestoreOp : public OpKernel {
 public:
  explicit WorkQueueRestoreOp(OpKernelConstruction* ctx) : OpKernel(ctx) {}

  void Compute(OpKernelContext* ctx) override {
    WorkQueue* work_queue;
    OP_REQUIRES_OK(ctx,
                   LookupResource(ctx, HandleFromInput(ctx, 0), &work_queue));
    const Tensor* works;
    OP_REQUIRES_OK(ctx, ctx->input("works", &works));
    OP_REQUIRES_OK(ctx, work_queue->Restore(*works));
  }
};

REGISTER_KERNEL_BUILDER(Name("WorkQueueRestore").Device(DEVICE_CPU),
                        WorkQueueRestoreOp);

REGISTER_OP("WorkQueueSave")
    .Output("works: string")
    .Input("handle: resource")
    .SetShapeFn(shape_inference::ScalarShape)
    .SetIsStateful()
    .Doc(R"doc(
Saves a work queue to tensor.

works: A tensor containing works.
handle: Handle of a work queue.
)doc");

class WorkQueueSaveOp : public OpKernel {
 public:
  explicit WorkQueueSaveOp(OpKernelConstruction* ctx) : OpKernel(ctx) {}

  void Compute(OpKernelContext* ctx) override {
    WorkQueue* work_queue;
    OP_REQUIRES_OK(ctx,
                   LookupResource(ctx, HandleFromInput(ctx, 0), &work_queue));
    Tensor* works;
    OP_REQUIRES_OK(ctx, work_queue->Save(ctx, &works));
  }
};

REGISTER_KERNEL_BUILDER(Name("WorkQueueSave").Device(DEVICE_CPU),
                        WorkQueueSaveOp);

REGISTER_OP("WorkQueueSize")
    .Output("size: int64")
    .Input("handle: resource")
    .SetShapeFn(shape_inference::ScalarShape)
    .SetIsStateful()
    .Doc(R"doc(
Gets size of a work queue.

size: A scalar tensor.
handle: Handle of a work queue.
)doc");

class WorkQueueSizeOp : public OpKernel {
 public:
  explicit WorkQueueSizeOp(OpKernelConstruction* ctx) : OpKernel(ctx) {}

  void Compute(OpKernelContext* ctx) override {
    WorkQueue* work_queue;
    OP_REQUIRES_OK(ctx,
                   LookupResource(ctx, HandleFromInput(ctx, 0), &work_queue));
    Tensor* size;
    OP_REQUIRES_OK(ctx, ctx->allocate_output(0, TensorShape({}), &size));
    OP_REQUIRES_OK(ctx, work_queue->GetSize(size));
  }
};

REGISTER_KERNEL_BUILDER(Name("WorkQueueSize").Device(DEVICE_CPU),
                        WorkQueueSizeOp);

REGISTER_OP("WorkQueuePut")
    .Input("handle: resource")
    .Input("works: string")
    .SetShapeFn(shape_inference::NoOutputs)
    .SetIsStateful()
    .Doc(R"doc(
Puts works to a work queue.

handle: Handle of a work queue.
works: A tensor containing works.
)doc");

class WorkQueuePutOp : public OpKernel {
 public:
  explicit WorkQueuePutOp(OpKernelConstruction* ctx) : OpKernel(ctx) {}

  void Compute(OpKernelContext* ctx) override {
    WorkQueue* work_queue;
    OP_REQUIRES_OK(ctx,
                   LookupResource(ctx, HandleFromInput(ctx, 0), &work_queue));
    const Tensor* works;
    OP_REQUIRES_OK(ctx, ctx->input("works", &works));
    OP_REQUIRES_OK(ctx, work_queue->Put(*works));
  }
};

REGISTER_KERNEL_BUILDER(Name("WorkQueuePut").Device(DEVICE_CPU),
                        WorkQueuePutOp);

REGISTER_OP("WorkQueueTake")
    .Input("handle: resource")
    .Output("work: string")
    .Attr("num_clients: int >= 1 = 1")
    .SetShapeFn(shape_inference::ScalarShape)
    .SetIsStateful()
    .Doc(R"doc(
Take a work from the work queue.

handle: Handle of a work queue.
work: A tensor of taken work.
num_clients:  Number of threads for taking works.
)doc");

class WorkQueueTakeOp : public AsyncOpKernel {
 public:
  explicit WorkQueueTakeOp(OpKernelConstruction* ctx) : AsyncOpKernel(ctx) {
    OP_REQUIRES_OK(ctx, ctx->GetAttr("num_clients", &num_clients_));
  }

  void ComputeAsync(OpKernelContext* ctx,
                    AsyncOpKernel::DoneCallback done) override {
    WorkQueue* work_queue;
    OP_REQUIRES_OK(ctx,
                   LookupResource(ctx, HandleFromInput(ctx, 0), &work_queue));
    core::ScopedUnref scoped_list(work_queue);
    work_queue->Schedule(num_clients_, [this, ctx, done, work_queue]() {
      Tensor* work;
      OP_REQUIRES_OK_ASYNC(ctx, ctx->allocate_output(0, TensorShape({}), &work),
                           done);
      OP_REQUIRES_OK_ASYNC(ctx, work_queue->Take(work), done);
      done();
    });
  }

 private:
  int64 num_clients_;
};

REGISTER_KERNEL_BUILDER(Name("WorkQueueTake").Device(DEVICE_CPU),
                        WorkQueueTakeOp);

WHITELIST_STATEFUL_OP_FOR_DATASET_FUNCTIONS("QueueDequeueV2");

}  // namespace efl
}  // namespace tensorflow

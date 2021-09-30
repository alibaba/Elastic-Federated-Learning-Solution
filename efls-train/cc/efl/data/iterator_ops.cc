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

#include "tensorflow/core/common_runtime/graph_runner.h"
#include "tensorflow/core/common_runtime/renamed_device.h"
#include "tensorflow/core/common_runtime/threadpool_device.h"
#include "tensorflow/core/framework/partial_tensor_shape.h"
#include "tensorflow/core/framework/resource_op_kernel.h"
#include "tensorflow/core/framework/stats_aggregator.h"
#include "tensorflow/core/framework/tensor.h"
#include "tensorflow/core/framework/variant_op_registry.h"
#include "tensorflow/core/graph/graph_constructor.h"
#include "tensorflow/core/lib/core/threadpool.h"
#include "tensorflow/core/lib/gtl/cleanup.h"
#include "tensorflow/core/lib/random/random.h"
#include "tensorflow/core/lib/strings/strcat.h"
#include "tensorflow/core/lib/strings/stringprintf.h"
#include "tensorflow/core/framework/dataset.h"
#include "tensorflow/core/framework/op_kernel.h"
#include "tensorflow/core/common_runtime/function.h"
#include "tensorflow/core/kernels/data/iterator_ops.h"

namespace tensorflow {
namespace efl {

const char kIteratorVariantTypeName[] = "tensorflow::Iterator";
constexpr char kDelimiter[] = "@@";

class VariantTensorDataHandler : public IteratorStateReader {
 public:
  explicit VariantTensorDataHandler(VariantTensorData* data)
      : data_(data) {
    string metadata;
    data_->get_metadata(&metadata);
    auto keys = str_util::Split(metadata, kDelimiter, str_util::SkipEmpty());
    for (size_t i = 0; i < keys.size(); ++i) {
      map_[keys[i]] = i;
    }
  }

  Status ReadScalar(StringPiece key, int64* val) override {
    return ReadScalarInternal(key, val);
  }

  Status ReadScalar(StringPiece key, string* val) override {
    return ReadScalarInternal(key, val);
  }

  Status ReadTensor(StringPiece key, Tensor* val) override {
    return ReadTensorInternal(key, val);
  }

  bool Contains(StringPiece key) override {
    return map_.find(string(key)) != map_.end();
  }

  Status ReadScalarWithPattern(StringPiece key, string* val) {
    return ReadScalarWithPatternInternal(key, val);
  }

  Status ReadScalarWithPattern(StringPiece key, int64* val) {
    return ReadScalarWithPatternInternal(key, val);
  }

  Status SetScalarWithPattern(StringPiece key, int64 val) {
    return SetScalarWithPatternInternal(key, val);
  }

  Status SetScalarWithPattern(StringPiece key, string val) {
    return SetScalarWithPatternInternal(key, val);
  }

 private:
  template <typename T>
  Status ReadScalarInternal(StringPiece key, T* val) {
    if (map_.find(string(key)) == map_.end()) {
      return errors::NotFound(key);
    }
    *val = data_->tensors(map_[string(key)]).scalar<T>()();
    return Status::OK();
  }

  template <typename T>
  Status ReadScalarWithPatternInternal(StringPiece key, T* val) {
    int find_times = 0;
    for (auto& iter: map_) {
      if (iter.first.find(string(key)) != string::npos) {
        *val = data_->tensors(iter.second).scalar<T>()();
        ++find_times;
      }
    }
    if (find_times == 0) {
      return errors::NotFound(key);
    } else if (find_times == 1) {
      return Status::OK();
    } else {
      return errors::Internal("Find more than one key pattern.");
    }
  }

  template <typename T>
  Status SetScalarWithPatternInternal(StringPiece key, T val) {
    int find_times = 0;
    for (auto& iter: map_) {
      if (iter.first.find(string(key)) != string::npos) {
        data_->tensors_[iter.second].scalar<T>()() = val;
        ++find_times;
      }
    }
    if (find_times == 0) {
      return errors::NotFound(key);
    } else if (find_times == 1) {
      return Status::OK();
    } else {
      return errors::Internal("Find more than one key pattern.");
    }
  }

  Status ReadTensorInternal(StringPiece key, Tensor* val) {
    if (map_.find(string(key)) == map_.end()) {
      return errors::NotFound(key);
    }
    *val = data_->tensors(map_[string(key)]);
    return Status::OK();
  }

  std::map<string, size_t> map_;
  VariantTensorData* data_;  // Not owned.
};


class IteratorStateVariant {
 public:
  IteratorStateVariant() : data_(nullptr) {}
  IteratorStateVariant(const IteratorStateVariant& other) : data_(nullptr) {
    if (other.data_) {
      Decode(*other.data_);
    }
  }
  IteratorStateVariant& operator=(IteratorStateVariant&& other) = default;
  IteratorStateVariant& operator=(const IteratorStateVariant& other) = delete;

  Status InitializeFromIterator(OpKernelContext* ctx,
                                data::IteratorResource* iterator_resource) {
    SerializationContext serialization_ctx({});
    data_ = absl::make_unique<VariantTensorData>();
    data_->set_type_name(TypeName());
    data::VariantTensorDataWriter writer(data_.get());
    TF_RETURN_IF_ERROR(iterator_resource->Save(&serialization_ctx, &writer));
    TF_RETURN_IF_ERROR(writer.Flush());
    return Status::OK();
  }

  string TypeName() const { return kIteratorVariantTypeName; }
  void Encode(VariantTensorData* data) const { *data = *data_; }
  bool Decode(VariantTensorData data) {
    if (data.type_name() != TypeName()) {
      return false;
    }
    std::unique_ptr<VariantTensorData> tensor_data =
        absl::make_unique<VariantTensorData>();
    std::swap(*tensor_data, data);
    std::unique_ptr<VariantTensorDataHandler> handler =
        absl::make_unique<VariantTensorDataHandler>(tensor_data.get());
    std::unique_ptr<data::VariantTensorDataReader> reader =
        absl::make_unique<data::VariantTensorDataReader>(tensor_data.get());
    data_ = std::move(tensor_data);
    handler_ = std::move(handler);
    reader_ = std::move(reader);
    return true;
  }
  VariantTensorDataHandler* get_handler() { return handler_.get(); }
  IteratorStateReader* get_reader() { return reader_.get(); }
  string DebugString() const {
    if (data_) {
      return strings::StrCat("IteratorStateVariant<", data_->DebugString(),
                             ">");
    } else {
      return strings::StrCat("IteratorStateVariant<empty>");
    }
  }

 private:
  std::unique_ptr<VariantTensorDataHandler> handler_;
  std::unique_ptr<IteratorStateReader> reader_;
  std::unique_ptr<VariantTensorData> data_;
};


class GetSampleIndexFromIterStringOp : public OpKernel {
 public:
  explicit GetSampleIndexFromIterStringOp(OpKernelConstruction* ctx)
      : OpKernel(ctx) {}

  void Compute(OpKernelContext* ctx) override {
    string in = ctx->input(0).scalar<string>()();
    Variant variant = IteratorStateVariant(); // Default constructed.
    variant.Decode(std::move(in));
    auto* wrapper = variant.get<IteratorStateVariant>();
    OP_REQUIRES(ctx, wrapper != nullptr,
                errors::InvalidArgument(
                    "DeserializeIteratorFromStringOp: Unable to parse variant "
                    "from string."));
    VariantTensorDataHandler* handler = wrapper->get_handler();
    Tensor* index;
    OP_REQUIRES_OK(ctx, ctx->allocate_output(0, TensorShape({}), &index));
    OP_REQUIRES_OK(ctx, handler->ReadScalarWithPattern("current_sample_index", &index->scalar<int64>()()));
  }
};

class GetBlockIdFromIterStringOp : public OpKernel {
 public:
  explicit GetBlockIdFromIterStringOp(OpKernelConstruction* ctx)
      : OpKernel(ctx) {}

  void Compute(OpKernelContext* ctx) override {
    string in = ctx->input(0).scalar<string>()();
    Variant variant = IteratorStateVariant(); // Default constructed.
    variant.Decode(std::move(in));
    auto* wrapper = variant.get<IteratorStateVariant>();
    OP_REQUIRES(ctx, wrapper != nullptr,
                errors::InvalidArgument(
                    "DeserializeIteratorFromStringOp: Unable to parse variant "
                    "from string."));
    VariantTensorDataHandler* handler = wrapper->get_handler();
    Tensor* block_id;
    OP_REQUIRES_OK(ctx, ctx->allocate_output(0, TensorShape({}), &block_id));
    OP_REQUIRES_OK(ctx, handler->ReadScalarWithPattern("current_block_name", &block_id->scalar<string>()()));
  }
};

class SetSampleIndexFromIterStringOp : public OpKernel {
 public:
  explicit SetSampleIndexFromIterStringOp(OpKernelConstruction* ctx)
      : OpKernel(ctx) {}

  void Compute(OpKernelContext* ctx) override {
    string in = ctx->input(0).scalar<string>()();
    int64 sample_index = ctx->input(1).scalar<int64>()();
    Variant variant = IteratorStateVariant(); // Default constructed.
    variant.Decode(std::move(in));
    auto* wrapper = variant.get<IteratorStateVariant>();
    OP_REQUIRES(ctx, wrapper != nullptr,
                errors::InvalidArgument(
                    "DeserializeIteratorFromStringOp: Unable to parse variant "
                    "from string."));
    VariantTensorDataHandler* handler = wrapper->get_handler();
    OP_REQUIRES_OK(ctx, handler->SetScalarWithPattern("current_sample_index", sample_index));
    Tensor* out_t;
    OP_REQUIRES_OK(ctx, ctx->allocate_output(0, TensorShape({}), &out_t));
    variant.Encode(&out_t->scalar<string>()());
    if (out_t->scalar<string>()().length() > (256 * 1024 * 1024)) {
      LOG(WARNING) << "Iterator state is large than 256MB, consider reduce the "
                      "number of IO threads.";
    }
  }
};

class SerializeIteratorToStringOp : public OpKernel {
 public:
  explicit SerializeIteratorToStringOp(OpKernelConstruction* ctx)
      : OpKernel(ctx) {}

  void Compute(OpKernelContext* ctx) override {
    const Tensor& resource_handle_t = ctx->input(0);
    OP_REQUIRES(ctx, TensorShapeUtils::IsScalar(resource_handle_t.shape()),
                errors::InvalidArgument("resource_handle must be a scalar"));

    // Validate that the handle corresponds to a real resource, and
    // that it is an IteratorResource.
    data::IteratorResource* iterator_resource;
    OP_REQUIRES_OK(
        ctx, LookupResource(ctx, HandleFromInput(ctx, 0), &iterator_resource));
    core::ScopedUnref unref_iterator(iterator_resource);
    Tensor* out_t;
    OP_REQUIRES_OK(ctx, ctx->allocate_output(0, TensorShape({}), &out_t));
    IteratorStateVariant v;
    OP_REQUIRES_OK(ctx, v.InitializeFromIterator(ctx, iterator_resource));
    Variant variant = v;
    variant.Encode(&out_t->scalar<string>()());
    if (out_t->scalar<string>()().length() > (256 * 1024 * 1024)) {
      LOG(WARNING) << "Iterator state is large than 256MB, consider reduce the "
                      "number of IO threads.";
    }
  }
};

class DeserializeIteratorFromStringOp : public OpKernel {
 public:
  explicit DeserializeIteratorFromStringOp(OpKernelConstruction* ctx)
      : OpKernel(ctx) {}

  void Compute(OpKernelContext* ctx) override {
    // Validate that the handle corresponds to a real resource, and
    // that it is an IteratorResource.
    data::IteratorResource* iterator_resource;
    OP_REQUIRES_OK(
        ctx, LookupResource(ctx, HandleFromInput(ctx, 0), &iterator_resource));
    core::ScopedUnref unref_iterator(iterator_resource);
    string in = ctx->input(1).scalar<string>()();
    Variant variant = IteratorStateVariant(); // Default constructed.
    variant.Decode(std::move(in));
    auto* wrapper = variant.get<IteratorStateVariant>();
    OP_REQUIRES(ctx, wrapper != nullptr,
                errors::InvalidArgument(
                    "DeserializeIteratorFromStringOp: Unable to parse variant "
                    "from string."));
    OP_REQUIRES_OK(ctx, iterator_resource->Restore(ctx, wrapper->get_reader()));
  }
};

REGISTER_OP("GetSampleIndexFromIterString")
    .Input("serialized: string")
    .Output("sample_index: int64")
    .SetShapeFn(shape_inference::ScalarShape);

REGISTER_KERNEL_BUILDER(
    Name("GetSampleIndexFromIterString").Device(DEVICE_CPU),
    GetSampleIndexFromIterStringOp);

REGISTER_OP("GetBlockIdFromIterString")
    .Input("serialized: string")
    .Output("block_id: string")
    .SetShapeFn(shape_inference::ScalarShape);

REGISTER_KERNEL_BUILDER(
    Name("GetBlockIdFromIterString").Device(DEVICE_CPU),
    GetBlockIdFromIterStringOp);

REGISTER_OP("SetSampleIndexFromIterString")
    .Input("serialized: string")
    .Input("sample_index: int64")
    .Output("serialize: string")
    .SetShapeFn(shape_inference::ScalarShape);

REGISTER_KERNEL_BUILDER(
    Name("SetSampleIndexFromIterString").Device(DEVICE_CPU),
    SetSampleIndexFromIterStringOp);

REGISTER_OP("SerializeIteratorToString")
    .Input("resource_handle: resource")
    .Output("serialized: string")
    .SetShapeFn(shape_inference::ScalarShape);

REGISTER_KERNEL_BUILDER(
    Name("SerializeIteratorToString").Device(DEVICE_CPU),
    SerializeIteratorToStringOp);

REGISTER_OP("DeserializeIteratorFromString")
    .Input("resource_handle: resource")
    .Input("serialized: string")
    .SetShapeFn(shape_inference::NoOutputs);

REGISTER_KERNEL_BUILDER(
    Name("DeserializeIteratorFromString").Device(DEVICE_CPU),
    DeserializeIteratorFromStringOp);
}  // namespace efl
}  // namespace tensorflow

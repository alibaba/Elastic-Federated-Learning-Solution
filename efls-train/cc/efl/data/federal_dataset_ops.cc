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

#include <memory>
#include <unordered_set>
#include <vector>
#include <atomic>

#include "tensorflow/core/framework/dataset.h"
#include "tensorflow/core/framework/tensor.h"
#include "tensorflow/core/lib/io/record_reader.h"
#include "tensorflow/core/lib/io/zlib_compression_options.h"
#include "tensorflow/core/lib/io/zlib_inputstream.h"
#include "tensorflow/core/framework/common_shape_fns.h"
#include "tensorflow/core/framework/shape_inference.h"

namespace tensorflow {
namespace efl {

class FederalDatasetOp : public DatasetOpKernel {
 public:
  explicit FederalDatasetOp(OpKernelConstruction* ctx)
      : DatasetOpKernel(ctx) {}

  void MakeDataset(OpKernelContext* ctx, DatasetBase** output) override {
    const Tensor* filenames_tensor;
    OP_REQUIRES_OK(ctx, ctx->input("filenames", &filenames_tensor));
    OP_REQUIRES(
        ctx, filenames_tensor->dims() <= 1,
        errors::InvalidArgument("`filenames` must be a scalar or a vector."));

    std::vector<string> filenames;
    filenames.reserve(filenames_tensor->NumElements());
    for (int i = 0; i < filenames_tensor->NumElements(); ++i) {
      filenames.push_back(filenames_tensor->flat<string>()(i));
    }

    const Tensor* blocks_tensor;
    OP_REQUIRES_OK(ctx, ctx->input("blocks", &blocks_tensor));
    OP_REQUIRES(
        ctx, blocks_tensor->dims() <= 1,
        errors::InvalidArgument("`block ids` must be a scalar or a vector."));
    OP_REQUIRES(
        ctx, blocks_tensor->NumElements() == filenames_tensor->NumElements(),
        errors::InvalidArgument("`blocks` and `filenames` must have same size."));
    std::vector<string> blocks;
    blocks.reserve(blocks_tensor->NumElements());
    for (int i = 0; i < blocks_tensor->NumElements(); ++i) {
      blocks.push_back(blocks_tensor->flat<string>()(i));
    }

    string compression_type;
    OP_REQUIRES_OK(ctx, data::ParseScalarArgument<string>(ctx, "compression_type",
                                                    &compression_type));

    int64 buffer_size = -1;
    OP_REQUIRES_OK(
        ctx, data::ParseScalarArgument<int64>(ctx, "buffer_size", &buffer_size));
    OP_REQUIRES(ctx, buffer_size >= 0,
                errors::InvalidArgument(
                    "`buffer_size` must be >= 0 (0 == no buffering)"));
    int64 sample_index = -1;
    OP_REQUIRES_OK(
        ctx, data::ParseScalarArgument<int64>(ctx, "sample_index", &sample_index));
    OP_REQUIRES(ctx, sample_index >= 0,
                errors::InvalidArgument(
                    "`sample_index` must be >= 0"));

    *output =
        new Dataset(ctx, std::move(filenames), std::move(blocks), compression_type, buffer_size, sample_index);
  }

 private:
  class Dataset : public DatasetBase {
   public:
    explicit Dataset(OpKernelContext* ctx, std::vector<string> filenames,
                     std::vector<string> blocks,
                     const string& compression_type, int64 buffer_size,
                     int64 sample_index)
        : DatasetBase(DatasetContext(ctx)),
          filenames_(std::move(filenames)),
          blocks_(std::move(blocks)),
          compression_type_(compression_type),
          sample_index_(sample_index),
          options_(io::RecordReaderOptions::CreateRecordReaderOptions(
              compression_type)) {
      if (buffer_size > 0) {
        options_.buffer_size = buffer_size;
      }
    }

    std::unique_ptr<IteratorBase> MakeIteratorInternal(
        const string& prefix) const override {
      return std::unique_ptr<IteratorBase>(
          new Iterator({this, strings::StrCat(prefix, "::FederalRecord")}));
    }

    const DataTypeVector& output_dtypes() const override {
      static DataTypeVector* dtypes = new DataTypeVector({DT_STRING});
      return *dtypes;
    }

    const std::vector<PartialTensorShape>& output_shapes() const override {
      static std::vector<PartialTensorShape>* shapes =
          new std::vector<PartialTensorShape>({{}});
      return *shapes;
    }

    string DebugString() const override { return "FederalDatasetOp::Dataset"; }

   protected:
    Status AsGraphDefInternal(SerializationContext* ctx,
                              DatasetGraphDefBuilder* b,
                              Node** output) const override {
      Node* filenames = nullptr;
      TF_RETURN_IF_ERROR(b->AddVector(filenames_, &filenames));
      Node* blocks = nullptr;
      TF_RETURN_IF_ERROR(b->AddVector(blocks_, &blocks));
      Node* compression_type = nullptr;
      TF_RETURN_IF_ERROR(b->AddScalar(compression_type_, &compression_type));
      Node* buffer_size = nullptr;
      TF_RETURN_IF_ERROR(b->AddScalar(options_.buffer_size, &buffer_size));
      Node* sample_index = nullptr;
      TF_RETURN_IF_ERROR(b->AddScalar(sample_index_, &sample_index));
      TF_RETURN_IF_ERROR(b->AddDataset(
          this, {filenames, blocks, sample_index, compression_type, buffer_size}, output));
      return Status::OK();
    }

   private:
    class Iterator : public DatasetIterator<Dataset> {
     public:
      explicit Iterator(const Params& params)
          : DatasetIterator<Dataset>(params) {}

      Status GetNextInternal(IteratorContext* ctx,
                             std::vector<Tensor>* out_tensors,
                             bool* end_of_sequence) override {
        mutex_lock l(mu_);
        do {
          // We are currently processing a file, so try to read the next record.
          if (reader_) {
            Tensor result_tensor(ctx->allocator({}), DT_STRING, {});
            Status s = reader_->ReadRecord(&result_tensor.scalar<string>()());
            if (s.ok()) {
              out_tensors->emplace_back(std::move(result_tensor));
              ++current_sample_index_;
              *end_of_sequence = false;
              return Status::OK();
            } else if (!errors::IsOutOfRange(s)) {
              return s;
            }

            // We have reached the end of the current file, so maybe
            // move on to next file.
            ResetStreamsLocked();
            ++current_file_index_;
            current_sample_index_ = 0;
          }

          // Iteration ends when there are no more files to process.
          if (current_file_index_ == dataset()->filenames_.size()) {
            *end_of_sequence = true;
            return Status::OK();
          }

          TF_RETURN_IF_ERROR(SetupStreamsLocked(ctx->env()));
          if (first_read_) {
            current_sample_index_ = size_t(dataset()->sample_index_);
            SeekSampleIndex(current_sample_index_);
            first_read_ = false;
          }
        } while (true);
      }

     protected:
      Status SaveInternal(IteratorStateWriter* writer) override {
        mutex_lock l(mu_);
        TF_RETURN_IF_ERROR(writer->WriteScalar(full_name("current_file_index"),
                                               current_file_index_));

        TF_RETURN_IF_ERROR(
            writer->WriteScalar(full_name("current_sample_index"),
                                current_sample_index_));
        TF_RETURN_IF_ERROR(
            writer->WriteScalar(full_name("first_read"),
                                first_read_));
         TF_RETURN_IF_ERROR(
            writer->WriteScalar(full_name("current_block_name"),
                                current_block_name_));
        return Status::OK();
      }

      Status RestoreInternal(IteratorContext* ctx,
                             IteratorStateReader* reader) override {
        mutex_lock l(mu_);
        ResetStreamsLocked();
        int64 current_file_index;
        TF_RETURN_IF_ERROR(reader->ReadScalar(full_name("current_file_index"),
                                              &current_file_index));
        current_file_index_ = size_t(current_file_index);
        int64 current_sample_index;
        TF_RETURN_IF_ERROR(reader->ReadScalar(full_name("current_sample_index"),
                                              &current_sample_index));
        current_sample_index_ = size_t(current_sample_index);
        int64 first_read;
        TF_RETURN_IF_ERROR(reader->ReadScalar(full_name("first_read"),
                                              &first_read));
        first_read_ = bool(first_read);
        TF_RETURN_IF_ERROR(reader->ReadScalar(full_name("current_block_name"),
                                              &current_block_name_));
        TF_RETURN_IF_ERROR(SetupStreamsLocked(ctx->env()));
        TF_RETURN_IF_ERROR(SeekSampleIndex(current_sample_index_));
        return Status::OK();
      }

     private:
      // Sets up reader streams to read from the file at `current_file_index_`.
      Status SetupStreamsLocked(Env* env) EXCLUSIVE_LOCKS_REQUIRED(mu_) {
        if (current_file_index_ >= dataset()->filenames_.size()) {
          return errors::InvalidArgument(
              "current_file_index_:", current_file_index_,
              " >= filenames_.size():", dataset()->filenames_.size());
        }

        // Actually move on to next file.
        const string& next_filename =
            dataset()->filenames_[current_file_index_];
        current_block_name_ = dataset()->blocks_[current_file_index_];
        TF_RETURN_IF_ERROR(env->NewRandomAccessFile(next_filename, &file_));
        reader_.reset(
            new io::SequentialRecordReader(file_.get(), dataset()->options_));
        return Status::OK();
      }

      // Resets all reader streams.
      void ResetStreamsLocked() EXCLUSIVE_LOCKS_REQUIRED(mu_) {
        reader_.reset();
        file_.reset();
      }

      Status SeekSampleIndex(size_t sample_index) EXCLUSIVE_LOCKS_REQUIRED(mu_) {
        while(sample_index != 0) {
          if (reader_) {
            string tmp_result;
            Status s = reader_->ReadRecord(&tmp_result);
            if (s.ok()) {
              --sample_index;
            } else {
              return s;
            }
          } else {
            return errors::OutOfRange(
                "SeekSampleIndex error, not enough sample in file.");
          }
        }
        return Status::OK();
      }

      mutex mu_;
      size_t current_file_index_ GUARDED_BY(mu_) = 0;
      size_t current_sample_index_ GUARDED_BY(mu_) = 0;
      bool first_read_ GUARDED_BY(mu_) = true;
      string current_block_name_ GUARDED_BY(mu_) = "";

      // `reader_` will borrow the object that `file_` points to, so
      // we must destroy `reader_` before `file_`.
      std::unique_ptr<RandomAccessFile> file_ GUARDED_BY(mu_);
      std::unique_ptr<io::SequentialRecordReader> reader_ GUARDED_BY(mu_);
    };

    const std::vector<string> filenames_;
    const std::vector<string> blocks_;
    const string compression_type_;
    int64 sample_index_;
    io::RecordReaderOptions options_;
  };

 private:
};

REGISTER_OP("FederalDataset")
    .Input("filenames: string")
    .Input("blocks: string")
    .Input("sample_index: int64")
    .Input("compression_type: string")
    .Input("buffer_size: int64")
    .Output("handle: variant")
    .SetIsStateful()
    .SetShapeFn(shape_inference::ScalarShape);


REGISTER_KERNEL_BUILDER(Name("FederalDataset").Device(DEVICE_CPU),
                        FederalDatasetOp);

}  // namespace efl
}  // namespace tensorflow

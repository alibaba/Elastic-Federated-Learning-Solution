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

#include "tensorflow/core/framework/dataset_stateful_op_whitelist.h"
#include "tensorflow/core/framework/resource_mgr.h"
#include "tensorflow/core/util/env_var.h"

#include "communication_client.h"
#include "grpc_utils.h"
#include "monitor.h"

using tensorflow::core::ScopedUnref;

namespace tensorflow {
namespace efl {

class Communicator : public ResourceBase {
 public:
  Communicator(const string& listen_address,
               const string& peer_address,
               const long long scanning_interval_milliseconds,
               const long long default_timeout_milliseconds,
               const Tensor& name_list,
               const Tensor& dataset_name_list) 
      : listen_address_(listen_address),
        peer_address_(peer_address),
        monitor_(scanning_interval_milliseconds, default_timeout_milliseconds) {
    auto list = name_list.flat<string>();
    const auto N = list.size();
    for (auto i = 0; i < N; i++) {
      call_map_[list(i)] = nullptr;
    }
    auto dataset_list = dataset_name_list.flat<string>();
    const auto M = dataset_list.size();
    for (auto i = 0; i < M; i++) {
      reader_state_call_data_[dataset_list(i)] = nullptr;
    }
    status_ = CREATED;
    monitor_.Start();
  }

  ~Communicator() {
    monitor_.Shutdown();
  }

  string DebugString() const override {
    return "Communicator <" + listen_address_ + ", " + peer_address_ + ">";
  }
 
  void RequestConnection(OpKernelContext* context,
                         AsyncOpKernel::DoneCallback done,
                         const int client_thread_num,
                         const int server_thread_num) {
    if (status_ != CREATED && status_ != CONNECTING) {
      OP_REQUIRES_OK_ASYNC(context, errors::FailedPrecondition("Already Connected."), done);
      return;
    }
    auto callback = [context, done, this] (ClientImpl::ConnectionAsyncClientCall* call) {
      ScopedUnref scoped_unref(this);
      OP_REQUIRES_OK_ASYNC(context, Grpc2TfStatus(call->GetStatus()), done);
      status_ = CONNECTED;
      done();
      LOG(INFO) << "Connect with Peer.";
    };

    Connect(context, done, client_thread_num, server_thread_num);
    client_->RequestConnection(callback);
  }

  void SendTensor(OpKernelContext* context,
                  AsyncOpKernel::DoneCallback done,
                  const Tensor* tensor,
                  const string& tensor_name,
                  const uint64 step) {
    if (status_ != CONNECTED) {
      OP_REQUIRES_OK_ASYNC(context, errors::FailedPrecondition("Haven't connected with peer worker."), done);
    }

    auto timeout_callback = [context, done, tensor_name, step, this] () {
      auto msg = "Send Tensor " + tensor_name + ", step " + std::to_string(step) + " Timeout.";
      OP_REQUIRES_OK_ASYNC(context, errors::DeadlineExceeded(msg), done);
    };
    auto key = monitor_.Register(timeout_callback);

    auto callback = [context, done, key, this] (ClientImpl::SendMessageAsyncClientCall* call) {
      ScopedUnref scoped_unref(this);
      if (!monitor_.Unregister(key)) {
        return;
      }
      OP_REQUIRES_OK_ASYNC(context, Grpc2TfStatus(call->GetStatus()), done);
      auto reply = call->GetReply();
      if (reply.code() != 0) {
        Status st(reply.code(), reply.msg());
        OP_REQUIRES_OK_ASYNC(context, st, done);
      } else {
        done();
      }
    };
    LOG(INFO) << "Send Tensor <name: " + tensor_name + ", step: " + std::to_string(step) + "> " + tensor->DebugString() + ".";
    // must print LOG before send.
    client_->SendTensor(tensor, tensor_name, step, callback);
  }

  void RequestReaderState(OpKernelContext* context,
                          AsyncOpKernel::DoneCallback done,
                          const string& name,
                          Tensor* block_name,
                          Tensor* sample_index) {
    if (status_ != CONNECTED) {
      OP_REQUIRES_OK_ASYNC(context, errors::FailedPrecondition("Haven't connected with peer worker."), done);
      return;
    }

    auto timeout_callback = [context, done, this] () {
      auto msg = "Request Reader State Timeout.";
      OP_REQUIRES_OK_ASYNC(context, errors::DeadlineExceeded(msg), done);
    };
    auto key = monitor_.Register(timeout_callback);

    auto callback = 
        [context, done, name, block_name, sample_index, key, this] (ClientImpl::ReaderStateAsyncClientCall* call) {
      ScopedUnref scoped_unref(this);
      if (!monitor_.Unregister(key)) {
        return;
      }
      OP_REQUIRES_OK_ASYNC(context, Grpc2TfStatus(call->GetStatus()), done);
      auto reply = call->GetReply();
      if (reply.code() != 0) {
        Status st(reply.code(), reply.msg());
        OP_REQUIRES_OK_ASYNC(context, st, done);
      } else {
        block_name->scalar<string>()() = reply.block_id();
        sample_index->scalar<int64>()() = reply.offset();
        LOG(INFO) << "Receive ReaderState <name = " + name + ", block_id = " + reply.block_id() + ", offset = " + std::to_string(reply.offset()) + ">.";
        done();
      }
    };
    client_->RequestReaderState(name, callback);
  }

  void RequestCkptVersion(OpKernelContext* context,
                          AsyncOpKernel::DoneCallback done,
                          Tensor* ckpt_version) {
    if (status_ != CONNECTED) {
      OP_REQUIRES_OK_ASYNC(context, errors::FailedPrecondition("Haven't connected with peer worker."), done);
      return;
    }

    auto timeout_callback = [context, done, this] () {
      auto msg = "Request Ckpt Version Timeout.";
      OP_REQUIRES_OK_ASYNC(context, errors::DeadlineExceeded(msg), done);
    };
    auto key = monitor_.Register(timeout_callback);

    auto callback = [context, done, ckpt_version, key, this] (ClientImpl::CheckpointVersionAsyncClientCall* call) {
      ScopedUnref scoped_unref(this);
      if (!monitor_.Unregister(key)) {
        return;
      }
      OP_REQUIRES_OK_ASYNC(context, Grpc2TfStatus(call->GetStatus()), done);
      auto reply = call->GetReply();
      if (reply.code() != 0) {
        Status st(reply.code(), reply.msg());
        OP_REQUIRES_OK_ASYNC(context, st, done);
      } else {
        ckpt_version->scalar<string>()() = reply.version();
        LOG(INFO) << "Receive CkptVersion <version = " + reply.version() + ">.";
        done();
      }
    };
    client_->RequestCheckpointVersion(callback);
  }

  void ResponseConnection(OpKernelContext* context,
                          AsyncOpKernel::DoneCallback done,
                          const int client_thread_num,
                          const int server_thread_num) {
    if (status_ != CREATED && status_ != CONNECTING) {
      OP_REQUIRES_OK_ASYNC(context, errors::FailedPrecondition("Already Connected."), done);
      return;
    }

    auto timeout_callback = [context, done, this] () {
      auto msg = "Wait for Connection Timeout.";
      OP_REQUIRES_OK_ASYNC(context, errors::DeadlineExceeded(msg), done);
    };
    auto key = monitor_.Register(timeout_callback);

    auto callback = [done, key, this] (ServerImpl::ConnectionCallData* call) {
      ScopedUnref scoped_unref(this);
      if (!monitor_.Unregister(key)) {
        return;
      }
      LOG(INFO) << "Connect with Peer.";
      call->OnFinish();
      done();
    };

    Connect(context, done, client_thread_num, server_thread_num);
    status_ = CONNECTED;
    mutex_lock m_lock(connect_mutex_);
    if (connect_call_data_) {
      callback(connect_call_data_);
      connect_call_data_ = nullptr;
    } else {
      connect_cb_ = callback;
    }
  }

  void ReceiveTensor(OpKernelContext* context,
                     AsyncOpKernel::DoneCallback done,
                     const string& tensor_name,
                     const uint64 step) {
    if (status_ != CONNECTED) {
      OP_REQUIRES_OK_ASYNC(context, errors::FailedPrecondition("Haven't connected with peer worker."), done);
      return;
    }

    auto timeout_callback = [context, done, tensor_name, step, this] () {
      auto msg = "Receive Tensor " + tensor_name + ", step " + std::to_string(step) + " Timeout.";
      OP_REQUIRES_OK_ASYNC(context, errors::DeadlineExceeded(msg), done);
    };
    auto key = monitor_.Register(timeout_callback);

    auto callback = [context, done, key, this] (ServerImpl::SendMessageCallData* call) {
      ScopedUnref scoped_unref(this);
      if (!monitor_.Unregister(key)) {
        return;
      }
      Tensor tensor;
      auto request = call->GetRequest();
      if (!tensor.FromProto(request->tensor())) {
        auto st = errors::Unknown("Tensor named " + request->name() + " deserialize error.");
        call->SetResponseStatus(st);
        call->OnFinish();
        OP_REQUIRES_OK_ASYNC(context, st, done);
      } else {
        Tensor* output = nullptr;
        auto st = context->allocate_output(0, tensor.shape(), &output);
        if (!st.ok()) {
          call->OnFinish();
          OP_REQUIRES_OK_ASYNC(context, st, done);
        } else {
          call->SetResponseStatus(st);
          *output = std::move(tensor);
          LOG(INFO) << "Receive tensor <name: " + request->name() + ", step: " + std::to_string(request->step()) + "> " + output->DebugString() +  ".";
          call->OnFinish();
          done();
        }
      }
    };

    mutex_lock m_lock(call_map_mutex_);
    auto call_iterator = call_map_.find(tensor_name);
    if (call_iterator != call_map_.end()) {
      auto call = call_iterator->second;
      if (call == nullptr) {
        callback_map_[tensor_name + "_" + std::to_string(step)] = callback;
      } else if (step == call->GetRequest()->step()) {
        call_iterator->second = nullptr;
        callback(call);
      } else {
        auto st = errors::DataLoss("Tensor named " + tensor_name + " expects step " + std::to_string(step) + ", but given step " + std::to_string(call->GetRequest()->step()) + ".");
        call->SetResponseStatus(st);
        call->OnFinish();
        OP_REQUIRES_OK_ASYNC(context, st, done);
      }
    } else {
      auto st = errors::InvalidArgument("Tensor named " + tensor_name + " not registed.");
      OP_REQUIRES_OK_ASYNC(context, st, done);
    }
  }

  void ResponseReaderState(OpKernelContext* context,
                           AsyncOpKernel::DoneCallback done,
                           const string& name,
                           const string& block_id,
                           const int64 offset) {
    if (status_ != CONNECTED) {
      OP_REQUIRES_OK_ASYNC(context, errors::FailedPrecondition("Haven't connected with peer worker."), done);
      return;
    }

    auto timeout_callback = [context, done, block_id, offset, this] () {
      auto msg = "Response Reader State "+ block_id + ", offset " + std::to_string(offset) + " Timeout.";
      OP_REQUIRES_OK_ASYNC(context, errors::DeadlineExceeded(msg), done);
    };
    auto key = monitor_.Register(timeout_callback);

    auto callback = [context, done, name, block_id, offset, key, this] (ServerImpl::ReaderStateCallData* call) {
      ScopedUnref scoped_unref(this);
      if (!monitor_.Unregister(key)) {
        return;
      }
      auto response = call->GetReply();
      response->set_block_id(block_id);
      response->set_offset(offset);
      call->SetResponseStatus(Status::OK());
      call->OnFinish();
      done();
      LOG(INFO) << "Send ReaderState <name = " + name + ", block_id = " + block_id + ", offset = " + std::to_string(offset) + ">.";
    };
    mutex_lock m_lock(reader_state_mutex_);
    auto iter = reader_state_call_data_.find(name);
    if (iter != reader_state_call_data_.end()) {
      auto call = iter->second;
      if (call == nullptr) {
        reader_state_cb_[name] = callback;
      } else {
        iter->second = nullptr;
        callback(call);
      }
    } else {
      auto st = errors::InvalidArgument("Dataset named " + name + "not registed.");
      OP_REQUIRES_OK_ASYNC(context, st, done);
    }
  }

  void TerminateReaderState(OpKernelContext* context,
                            AsyncOpKernel::DoneCallback done,
                            const string& name) {
    if (status_ != CONNECTED) {
      OP_REQUIRES_OK_ASYNC(context, errors::FailedPrecondition("Haven't connected with peer worker."), done);
      return;
    }

    auto timeout_callback = [context, done, this] () {
      auto msg = "Terminate Reader State Timeout.";
      OP_REQUIRES_OK_ASYNC(context, errors::DeadlineExceeded(msg), done);
    };
    auto key = monitor_.Register(timeout_callback);

    auto callback = [context, done, key, this] (ServerImpl::ReaderStateCallData* call) {
      ScopedUnref scoped_unref(this);
      if (!monitor_.Unregister(key)) {
        return;
      }
      auto st = errors::OutOfRange("Reader State from remote out of range.");
      call->SetResponseStatus(st);
      call->OnFinish();
      OP_REQUIRES_OK_ASYNC(context, st, done);
    };

    mutex_lock m_lock(reader_state_mutex_);
    auto iter = reader_state_call_data_.find(name);
    if (iter != reader_state_call_data_.end()) {
      auto call = iter->second;
      if (call == nullptr) {
        reader_state_cb_[name] = callback;
      } else {
        iter->second = nullptr;
        callback(call);
      }
    } else {
      auto st = errors::InvalidArgument("Dataset named " + name + "not registed.");
      OP_REQUIRES_OK_ASYNC(context, st, done);
    }
  }

  void ResponseCkptVersion(OpKernelContext* context,
                           AsyncOpKernel::DoneCallback done,
                           const string& ckpt_version) {
    if (status_ != CONNECTED) {
      OP_REQUIRES_OK_ASYNC(context, errors::FailedPrecondition("Haven't connected with peer worker."), done);
      return;
    }

    auto timeout_callback = [context, done, ckpt_version, this] () {
      auto msg = "Response Ckpt Version " + ckpt_version + " Timeout.";
      OP_REQUIRES_OK_ASYNC(context, errors::DeadlineExceeded(msg), done);
    };
    auto key = monitor_.Register(timeout_callback);

    auto callback = [context, done, key, ckpt_version, this] (ServerImpl::CheckpointVersionCallData* call) {
      ScopedUnref scoped_unref(this);
      if (!monitor_.Unregister(key)) {
        return;
      }
      auto response = call->GetReply();
      response->set_version(ckpt_version);
      call->SetResponseStatus(Status::OK());
      call->OnFinish();
      done();
      LOG(INFO) << "Send CkptVersion <version = " + ckpt_version + ">.";
    };
    mutex_lock m_lock(ckpt_version_mutex_);
    if (ckpt_version_call_data_) {
      callback(ckpt_version_call_data_);
      ckpt_version_call_data_ = nullptr;
    } else {
      ckpt_version_cb_ = callback;
    }
  }

  Status Close() {
    if (status_ == CONNECTED) {
      if (client_->Shutdown() & server_->Shutdown()) { // No use &&.
        status_ = CLOSED;
        return Status::OK();
      } else {
        return errors::FailedPrecondition("Shutdown failed. Server or Client is not running.");
      }
    } else {
      return errors::FailedPrecondition("Already Closed.");
    }
  }

 private:
  void Connect(OpKernelContext* context,
               AsyncOpKernel::DoneCallback done,
               const int client_thread_num,
               const int server_thread_num) {
    if (status_ == CONNECTING || status_ == CREATED) {
      if (status_ == CREATED) {
        string peer_certs_filename;
        string ssl_target_name_override;
        int64 max_send_message_size;
        int64 max_receive_message_size;

        OP_REQUIRES_OK_ASYNC(context,
            ReadStringFromEnvVar("EFL_PEER_CERTS_FILENAME", "", &peer_certs_filename),
            done);
        OP_REQUIRES_OK_ASYNC(context,
            ReadStringFromEnvVar("EFL_SSL_TARGET_NAME_OVERRIDE", "", &ssl_target_name_override),
            done);
        OP_REQUIRES_OK_ASYNC(context,
            ReadInt64FromEnvVar("EFL_CLIENT_MAX_SEND_MESSAGE_SIZE", 1 << 30, &max_send_message_size),
            done);
        OP_REQUIRES_OK_ASYNC(context,
            ReadInt64FromEnvVar("EFL_CLIENT_MAX_RECEIVE_MESSAGE_SIZE", 1 << 30, &max_receive_message_size),
            done);

        client_channel_args_.SetMaxSendMessageSize(max_send_message_size);
        client_channel_args_.SetMaxReceiveMessageSize(max_receive_message_size);
        if (!ssl_target_name_override.empty()) {
          client_channel_args_.SetSslTargetNameOverride(ssl_target_name_override);
        }

        if (!peer_certs_filename.empty()) {
          string peer_certs;
          OP_REQUIRES_OK_ASYNC(context, ReadFileToString(Env::Default(), peer_certs_filename, &peer_certs), done);
          grpc::SslCredentialsOptions options;
          options.pem_root_certs = peer_certs;
          client_channel_creds_ = grpc::SslCredentials(options);
        } else {
          client_channel_creds_ = grpc::InsecureChannelCredentials();
        }
      } else {
        client_->Shutdown();
        client_.reset();
      }
      auto channel = grpc::CreateCustomChannel(peer_address_, client_channel_creds_, client_channel_args_);
      client_ = std::unique_ptr<ClientImpl>(new ClientImpl(channel));
      client_->Run(client_thread_num);
      while (!client_->IsRunning()) {
        std::this_thread::sleep_for(std::chrono::milliseconds(100));
      }
    }

    if (status_ != CREATED) {
      return;
    }

    server_ = std::unique_ptr<ServerImpl>(new ServerImpl());
    server_->server_infos.Add("call_map", Any(&call_map_));
    server_->server_infos.Add("call_map_mutex", Any(&call_map_mutex_));
    server_->server_infos.Add("callback_map", Any(&callback_map_));
    server_->server_infos.Add("reader_state_mutex", Any(&reader_state_mutex_));
    server_->server_infos.Add("reader_state_cb", Any(&reader_state_cb_));
    server_->server_infos.Add("reader_state_call_data", Any(&reader_state_call_data_));
    server_->server_infos.Add("ckpt_version_mutex", Any(&ckpt_version_mutex_));
    server_->server_infos.Add("ckpt_version_cb", Any(&ckpt_version_cb_));
    server_->server_infos.Add("ckpt_version_call_data", Any(&ckpt_version_call_data_));
    server_->server_infos.Add("connection_mutex", Any(&connect_mutex_));
    server_->server_infos.Add("connection_cb", Any(&connect_cb_));
    server_->server_infos.Add("connection_call_data", Any(&connect_call_data_));
    server_->Run(context, done, listen_address_, server_thread_num);
    while (!server_->IsRunning()) {
      std::this_thread::sleep_for(std::chrono::milliseconds(100));
    }
    status_ = CONNECTING;
  }

  enum CommunicatorStatus { CREATED, CONNECTING, CONNECTED, CLOSED };
  CommunicatorStatus status_;
  const string listen_address_;
  const string peer_address_;
  Monitor monitor_;
  std::unique_ptr<ServerImpl> server_;
  std::unique_ptr<ClientImpl> client_;
  std::unordered_map<string, ServerImpl::SendMessageCallData*> call_map_;
  std::unordered_map<string, std::function<void(ServerImpl::SendMessageCallData*)>> callback_map_;
  std::unordered_map<string, ServerImpl::ReaderStateCallData*> reader_state_call_data_;
  std::unordered_map<string, std::function<void(ServerImpl::ReaderStateCallData*)>> reader_state_cb_;
  ServerImpl::CheckpointVersionCallData* ckpt_version_call_data_ = nullptr;
  std::function<void(ServerImpl::CheckpointVersionCallData*)> ckpt_version_cb_;
  ServerImpl::ConnectionCallData* connect_call_data_ = nullptr;
  std::function<void(ServerImpl::ConnectionCallData*)> connect_cb_;
  mutex call_map_mutex_;
  mutex reader_state_mutex_;
  mutex ckpt_version_mutex_;
  mutex connect_mutex_;
  grpc::ChannelArguments client_channel_args_;
  std::shared_ptr<grpc::ChannelCredentials> client_channel_creds_;
};

REGISTER_RESOURCE_HANDLE_OP(Communicator);
REGISTER_RESOURCE_HANDLE_KERNEL(Communicator);

REGISTER_OP("CreateCommunicator")
    .Input("communicator: resource")
    .Input("name_list: string")
    .Input("dataset_list: string")
    .Attr("listen_address: string")
    .Attr("peer_address: string")
    .Attr("scanning_interval_milliseconds: int = 30000")
    .Attr("default_timeout_milliseconds: int = 600000")
    .SetShapeFn(shape_inference::NoOutputs)
    .Doc(R"doc(
Create a communicator to communicate with the peer worker.

communicator: The communicator to be created.
name_list: Contains the names of the tensors that receive from peer worker.
listen_address: The address to be listened.
peer_address: The peer_worker's address.
scanning_interval_milliseconds: Monitor will scan ops to check timeout every once in a while.
default_timeout_milliseconds: If an op's running duration is beyond this threshold, it will throw an error.
)doc");

class CreateCommunicatorOp : public OpKernel {
 public:
  explicit CreateCommunicatorOp(OpKernelConstruction* context) : OpKernel(context) {
    OP_REQUIRES_OK(context, context->GetAttr("listen_address", &listen_address_));
    OP_REQUIRES_OK(context, context->GetAttr("peer_address", &peer_address_));
    OP_REQUIRES_OK(context, context->GetAttr("scanning_interval_milliseconds", &scanning_interval_milliseconds_));
    OP_REQUIRES_OK(context, context->GetAttr("default_timeout_milliseconds", &default_timeout_milliseconds_));
  }

  void Compute(OpKernelContext* context) override {
    auto communicator = new Communicator(listen_address_,
                                         peer_address_,
                                         scanning_interval_milliseconds_,
                                         default_timeout_milliseconds_,
                                         context->input(1),
                                         context->input(2));
    auto s = CreateResource(context, HandleFromInput(context, 0), communicator);
    if (!s.ok() && s.code() != error::ALREADY_EXISTS) {
      OP_REQUIRES(context, false, s);
    }
    LOG(INFO) << "Create a Communicator between " << listen_address_ << " and " << peer_address_ << ".";
  }

 private:
  string listen_address_;
  string peer_address_;
  long long scanning_interval_milliseconds_;
  long long default_timeout_milliseconds_;
};

REGISTER_KERNEL_BUILDER(Name("CreateCommunicator").Device(DEVICE_CPU), CreateCommunicatorOp);

REGISTER_OP("RequestConnection")
    .Input("communicator: resource")
    .Attr("client_thread_num: int = 1")
    .Attr("server_thread_num: int = 1")
    .SetShapeFn(shape_inference::NoOutputs)
    .Doc(R"doc(
Create a connection between the peer workers.

communicator: Create a connection based on the commnicator.
client_thread_num: the number of client threads.
server_thread_num: the number of server threads.
)doc");

class RequestConnectionOp : public AsyncOpKernel {
 public:
  explicit RequestConnectionOp(OpKernelConstruction* context) : AsyncOpKernel(context) {
    OP_REQUIRES_OK(context, context->GetAttr("client_thread_num", &client_thread_num_));
    OP_REQUIRES_OK(context, context->GetAttr("server_thread_num", &server_thread_num_));
  }

  void ComputeAsync(OpKernelContext* context, DoneCallback done) override {
    Communicator* communicator = nullptr;
    OP_REQUIRES_OK(context, LookupResource(context, HandleFromInput(context, 0), &communicator));
    communicator->Ref();
    communicator->RequestConnection(context, done, client_thread_num_, server_thread_num_);
  }

 private:
  int client_thread_num_;
  int server_thread_num_;
};

REGISTER_KERNEL_BUILDER(Name("RequestConnection").Device(DEVICE_CPU), RequestConnectionOp);

REGISTER_OP("ResponseConnection")
    .Input("communicator: resource")
    .Attr("client_thread_num: int = 1")
    .Attr("server_thread_num: int = 1")
    .SetShapeFn(shape_inference::NoOutputs)
    .Doc(R"doc(
Create a connection between the peer workers.

communicator: Create a connection based on the commnicator.
client_thread_num: the number of client threads.
server_thread_num: the number of server threads.
)doc");

class ResponseConnectionOp : public AsyncOpKernel {
 public:
  explicit ResponseConnectionOp(OpKernelConstruction* context) : AsyncOpKernel(context) {
    OP_REQUIRES_OK(context, context->GetAttr("client_thread_num", &client_thread_num_));
    OP_REQUIRES_OK(context, context->GetAttr("server_thread_num", &server_thread_num_));
  }

  void ComputeAsync(OpKernelContext* context, DoneCallback done) override {
    Communicator* communicator = nullptr;
    OP_REQUIRES_OK(context, LookupResource(context, HandleFromInput(context, 0), &communicator));
    communicator->Ref();
    communicator->ResponseConnection(context, done, client_thread_num_, server_thread_num_);
  }

 private:
  int client_thread_num_;
  int server_thread_num_;
};

REGISTER_KERNEL_BUILDER(Name("ResponseConnection").Device(DEVICE_CPU), ResponseConnectionOp);

REGISTER_OP("CloseConnection")
    .Input("communicator: resource")
    .SetShapeFn(shape_inference::NoOutputs)
    .Doc(R"doc(
Close the connection between the peer workers.

communicator: Create a connection based on the commnicator.
)doc");

class CloseConnectionOp : public OpKernel {
 public:
  explicit CloseConnectionOp(OpKernelConstruction* context) : OpKernel(context) {}

  void Compute(OpKernelContext* context) override {
    Communicator* communicator = nullptr;
    OP_REQUIRES_OK(context, LookupResource(context, HandleFromInput(context, 0), &communicator));
    OP_REQUIRES_OK(context, communicator->Close());
    LOG(INFO) << "Close a Connection through " << communicator->DebugString() << ".";
  }
};

REGISTER_KERNEL_BUILDER(Name("CloseConnection").Device(DEVICE_CPU), CloseConnectionOp);

REGISTER_OP("SendTensor")
    .Input("communicator: resource")
    .Input("tensor: tensor_type")
    .Input("step: int64")
    .Attr("tensor_name: string")
    .Attr("tensor_type: type")
    .SetShapeFn(shape_inference::NoOutputs)
    .Doc(R"doc(
Sends the named tensor to peer worker by communicator.

communicator: Peer works communicate by this.
tensor: The tensor to send.
step: The tensor's update steps.
tensor_name: The name of the tensor to send.
)doc");

class SendTensorOp : public AsyncOpKernel {
 public:
  explicit SendTensorOp(OpKernelConstruction* context) : AsyncOpKernel(context) {
    OP_REQUIRES_OK(context, context->GetAttr("tensor_name", &tensor_name_));
  }

  void ComputeAsync(OpKernelContext* context, DoneCallback done) override {
    Communicator* communicator = nullptr;
    OP_REQUIRES_OK_ASYNC(context, LookupResource(context, HandleFromInput(context, 0), &communicator), done);
    const Tensor* tensor = nullptr;
    OP_REQUIRES_OK_ASYNC(context, context->input("tensor", &tensor), done);
    const Tensor* step_tensor = nullptr;
    OP_REQUIRES_OK_ASYNC(context, context->input("step", &step_tensor), done);
    auto step = static_cast<uint64>(step_tensor->flat<int64>()(0));
    communicator->Ref();
    communicator->SendTensor(context, done, tensor, tensor_name_, step);
  }
 private:
  string tensor_name_;
};

REGISTER_KERNEL_BUILDER(Name("SendTensor").Device(DEVICE_CPU), SendTensorOp);

REGISTER_OP("ReceiveTensor")
    .Input("communicator: resource")
    .Attr("tensor_name: string")
    .Input("step: int64")
    .Output("tensor: tensor_type")
    .Attr("tensor_type: type")
    .SetShapeFn(shape_inference::UnknownShape)
    .Doc(R"doc(
Receive the tensor given its name and step from the peer worker.

communicator: Peer works communicate by this.
tensor_name: the name of the tensor to receive.
step: the number of update steps of the tensor to receive.
tensor: the tensor to receive.
tensor_type: the type of the tensor.
)doc");

class ReceiveTensorOp : public AsyncOpKernel {
 public:
  explicit ReceiveTensorOp(OpKernelConstruction* context) : AsyncOpKernel(context) {
    OP_REQUIRES_OK(context, context->GetAttr("tensor_name", &tensor_name_));
  }

  void ComputeAsync(OpKernelContext* context, DoneCallback done) override {
    Communicator* communicator = nullptr;
    OP_REQUIRES_OK_ASYNC(context, LookupResource(context, HandleFromInput(context, 0), &communicator), done);
    const Tensor* step_tensor = nullptr;
    OP_REQUIRES_OK_ASYNC(context, context->input("step", &step_tensor), done);
    auto step = static_cast<uint64>(step_tensor->flat<int64>()(0));
    communicator->Ref();
    LOG(INFO) << "recv " + tensor_name_;
    communicator->ReceiveTensor(context, done, tensor_name_, step);
  }

 private:
  string tensor_name_;
};

REGISTER_KERNEL_BUILDER(Name("ReceiveTensor").Device(DEVICE_CPU), ReceiveTensorOp);

REGISTER_OP("RecvReaderState")
    .Input("communicator: resource")
    .Attr("dataset_name: string")
    .Output("block_name: string")
    .Output("sample_index: int64")
    .SetShapeFn(shape_inference::ScalarShape);

class RecvReaderStateOp : public AsyncOpKernel {
 public:
  explicit RecvReaderStateOp(OpKernelConstruction* context) : AsyncOpKernel(context) {
    OP_REQUIRES_OK(context, context->GetAttr("dataset_name", &dataset_name_));
  }

  void ComputeAsync(OpKernelContext* context, DoneCallback done) override {
    Communicator* communicator = nullptr;
    OP_REQUIRES_OK_ASYNC(context, LookupResource(context, HandleFromInput(context, 0), &communicator), done);
    Tensor* block_name;
    OP_REQUIRES_OK(context, context->allocate_output(0, TensorShape({}), &block_name));
    Tensor* sample_index;
    OP_REQUIRES_OK(context, context->allocate_output(1, TensorShape({}), &sample_index));
    communicator->Ref();
    communicator->RequestReaderState(context, done, dataset_name_, block_name, sample_index);
  }

 private:
  string dataset_name_;
};

REGISTER_KERNEL_BUILDER(Name("RecvReaderState").Device(DEVICE_CPU), RecvReaderStateOp);

REGISTER_OP("SendReaderState")
    .Input("communicator: resource")
    .Input("block_name: string")
    .Input("sample_index: int64")
    .Attr("dataset_name: string")
    .SetShapeFn(shape_inference::NoOutputs);

class SendReaderStateOp : public AsyncOpKernel {
 public:
  explicit SendReaderStateOp(OpKernelConstruction* context) : AsyncOpKernel(context) {
    OP_REQUIRES_OK(context, context->GetAttr("dataset_name", &dataset_name_));
  }

  void ComputeAsync(OpKernelContext* context, DoneCallback done) override {
    Communicator* communicator = nullptr;
    OP_REQUIRES_OK_ASYNC(context, LookupResource(context, HandleFromInput(context, 0), &communicator), done);
    auto block_name = context->input(1).scalar<string>()();
    auto sample_index = context->input(2).scalar<int64>()();
    communicator->Ref();
    communicator->ResponseReaderState(context, done, dataset_name_, block_name, sample_index);
  }

 private:
  string dataset_name_;
};

REGISTER_KERNEL_BUILDER(Name("SendReaderState").Device(DEVICE_CPU), SendReaderStateOp);
WHITELIST_STATEFUL_OP_FOR_DATASET_FUNCTIONS("SendReaderState");

REGISTER_OP("TerminateReader")
    .Input("communicator: resource")
    .Attr("dataset_name: string")
    .SetShapeFn(shape_inference::NoOutputs);

class TerminateReaderOp : public AsyncOpKernel {
 public:
  explicit TerminateReaderOp(OpKernelConstruction* context) : AsyncOpKernel(context) {
    OP_REQUIRES_OK(context, context->GetAttr("dataset_name", &dataset_name_));
  }

  void ComputeAsync(OpKernelContext* context, DoneCallback done) override {
    Communicator* communicator = nullptr;
    OP_REQUIRES_OK_ASYNC(context, LookupResource(context, HandleFromInput(context, 0), &communicator), done);
    communicator->Ref();
    communicator->TerminateReaderState(context, done, dataset_name_);
  }

 private:
  string dataset_name_;
};

REGISTER_KERNEL_BUILDER(Name("TerminateReader").Device(DEVICE_CPU), TerminateReaderOp);
WHITELIST_STATEFUL_OP_FOR_DATASET_FUNCTIONS("TerminateReader");

REGISTER_OP("RecvCkptVersion")
    .Input("communicator: resource")
    .Output("version: string")
    .SetShapeFn(shape_inference::ScalarShape);

class RecvCkptVersionOp : public AsyncOpKernel {
 public:
  explicit RecvCkptVersionOp(OpKernelConstruction* context) : AsyncOpKernel(context) {}

  void ComputeAsync(OpKernelContext* context, DoneCallback done) override {
    Communicator* communicator = nullptr;
    OP_REQUIRES_OK_ASYNC(context, LookupResource(context, HandleFromInput(context, 0), &communicator), done);
    Tensor* version;
    OP_REQUIRES_OK(context, context->allocate_output(0, TensorShape({}), &version));
    communicator->Ref();
    communicator->RequestCkptVersion(context, done, version);
  }
};

REGISTER_KERNEL_BUILDER(Name("RecvCkptVersion").Device(DEVICE_CPU), RecvCkptVersionOp);

REGISTER_OP("SendCkptVersion")
    .Input("communicator: resource")
    .Input("version: string")
    .SetShapeFn(shape_inference::NoOutputs);

class SendCkptVersionOp : public AsyncOpKernel {
 public:
  explicit SendCkptVersionOp(OpKernelConstruction* context) : AsyncOpKernel(context) {}

  void ComputeAsync(OpKernelContext* context, DoneCallback done) override {
    Communicator* communicator = nullptr;
    OP_REQUIRES_OK_ASYNC(context, LookupResource(context, HandleFromInput(context, 0), &communicator), done);
    auto version = context->input(1).scalar<string>()();
    communicator->Ref();
    communicator->ResponseCkptVersion(context, done, version);
  }
};

REGISTER_KERNEL_BUILDER(Name("SendCkptVersion").Device(DEVICE_CPU), SendCkptVersionOp);

} // efl
} // tensorflow

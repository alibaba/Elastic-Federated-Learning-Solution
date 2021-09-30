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

#include "communication_client.h"

namespace tensorflow {
namespace efl {

ClientImpl::ClientImpl(std::shared_ptr<Channel> channel)
    : stub_(TrainerService::NewStub(channel)) {}

void ClientImpl::Run(int thread_num) {
  for (auto i = 0; i < thread_num; ++i) {
    threads_.push_back(std::unique_ptr<std::thread>(
        new std::thread(&ClientImpl::AsyncCompleteRpc, this)));
  }
}

ClientImpl::~ClientImpl() {
  Shutdown();
}

bool ClientImpl::IsRunning() {
  return is_running_;
}

void ClientImpl::SendTensor(const Tensor* tensor, const string& name, const uint64 step,
                            std::function<void(SendMessageAsyncClientCall*)> callback) {
  // Create a TensorProto.
  auto tensor_proto = new TensorProto();
  tensor->AsProtoField(tensor_proto);
  tensor->AsProtoTensorContent(tensor_proto);

  // Create a MessageRequest.
  MessageRequest request;
  request.set_allocated_tensor(tensor_proto);
  request.set_name(name);
  request.set_step(step);
  //Create a Call.
  auto call = new SendMessageAsyncClientCall(callback);
  // Prepare message.
  call->response_reader_ = stub_->PrepareAsyncSendMessage(&call->context_, request, &cq_);
  // Start the Call.
  call->response_reader_->StartCall();
  // Finish the Call.
  call->response_reader_->Finish(&call->reply_, &call->status_, reinterpret_cast<void*>(call));
}

void ClientImpl::RequestReaderState(const string& name, std::function<void(ReaderStateAsyncClientCall*)> callback) {
  GetReaderStateRequest request;
  request.set_name(name);
  auto call = new ReaderStateAsyncClientCall(callback);
  call->response_reader_ = stub_->PrepareAsyncGetReaderState(&call->context_, request, &cq_);
  call->response_reader_->StartCall();
  call->response_reader_->Finish(&call->reply_, &call->status_, reinterpret_cast<void*>(call));
}

void ClientImpl::RequestCheckpointVersion(std::function<void(CheckpointVersionAsyncClientCall*)> callback) {
  GetCheckpointVersionRequest request;
  auto call = new CheckpointVersionAsyncClientCall(callback);
  call->response_reader_ = stub_->PrepareAsyncGetCheckpointVersion(&call->context_, request, &cq_);
  call->response_reader_->StartCall();
  call->response_reader_->Finish(&call->reply_, &call->status_, reinterpret_cast<void*>(call));
}

void ClientImpl::RequestConnection(std::function<void(ConnectionAsyncClientCall*)> callback) {
  ConnectionRequest request;
  auto call = new ConnectionAsyncClientCall(callback);
  call->response_reader_ = stub_->PrepareAsyncConnect(&call->context_, request, &cq_);
  call->response_reader_->StartCall();
  call->response_reader_->Finish(&call->reply_, &call->status_, reinterpret_cast<void*>(call));
}

void ClientImpl::AsyncCompleteRpc() {
  void* got_tag = nullptr;
  bool ok = false;
  is_running_ = true;
  while (cq_.Next(&got_tag, &ok)) {
    if (!ok) {
      break;
    }
    // Get Response.
    switch (*reinterpret_cast<MessageType*>(reinterpret_cast<char*>(got_tag) + sizeof(void**))) {
      case SendMessage: {
        auto call = reinterpret_cast<SendMessageAsyncClientCall*>(got_tag);
        call->OnComplete();
        delete call;
        break;
      }
      case ReaderState: {
        auto call = reinterpret_cast<ReaderStateAsyncClientCall*>(got_tag);
        call->OnComplete();
        delete call;
        break;
      }
      case CheckpointVersion: {
        auto call = reinterpret_cast<CheckpointVersionAsyncClientCall*>(got_tag);
        call->OnComplete();
        delete call;
        break;
      }
      case Connection: {
        auto call = reinterpret_cast<ConnectionAsyncClientCall*>(got_tag);
        call->OnComplete();
        delete call;
        break;
      }
    }
  }
}

bool ClientImpl::Shutdown() {
  if (is_running_) {
    cq_.Shutdown();
    for (auto& thread : threads_) {
      thread->join();
    }
    is_running_ = false;
    return true;
  } else {
    return false;
  }
}

template<typename T_RESPONSE>
ClientImpl::AsyncClientCall<T_RESPONSE>::AsyncClientCall(MessageType type)
  : type_(type) {}

ClientImpl::SendMessageAsyncClientCall::SendMessageAsyncClientCall(std::function<void(SendMessageAsyncClientCall*)> callback)
  : AsyncClientCall(SendMessage),
    callback_(callback) {}

ClientImpl::ReaderStateAsyncClientCall::ReaderStateAsyncClientCall(std::function<void(ReaderStateAsyncClientCall*)> callback)
  : AsyncClientCall(ReaderState),
    callback_(callback) {}

ClientImpl::CheckpointVersionAsyncClientCall::CheckpointVersionAsyncClientCall(std::function<void(CheckpointVersionAsyncClientCall*)> callback)
  : AsyncClientCall(CheckpointVersion),
    callback_(callback) {}

ClientImpl::ConnectionAsyncClientCall::ConnectionAsyncClientCall(std::function<void(ConnectionAsyncClientCall*)> callback)
  : AsyncClientCall(Connection),
    callback_(callback) {}


void ClientImpl::SendMessageAsyncClientCall::OnComplete() {
  callback_(this);
}

void ClientImpl::ReaderStateAsyncClientCall::OnComplete() {
  callback_(this);
}

void ClientImpl::CheckpointVersionAsyncClientCall::OnComplete() {
  callback_(this);
}

void ClientImpl::ConnectionAsyncClientCall::OnComplete() {
  callback_(this);
}

}  // efl
}  // tensorflow

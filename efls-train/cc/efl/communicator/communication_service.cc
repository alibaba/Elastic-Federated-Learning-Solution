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

#include <thread>

#include "tensorflow/core/lib/core/errors.h"
#include "tensorflow/core/platform/mutex.h"
#include "tensorflow/core/util/env_var.h"

#include "communication_service.h"

using grpc::ServerBuilder;

namespace tensorflow {
namespace efl {

ServerImpl::~ServerImpl() {
  Shutdown();
}

bool ServerImpl::IsRunning() {
  return is_running_;
}

bool ServerImpl::Shutdown() {
  if (is_running_) {
    server_->Shutdown();
    cq_->Shutdown();
    for (auto& thread : threads_) {
      thread->join();
    }
    is_running_ = false;
    return true;
  } else {
    return false;
  }
}

// Run the Server.
void ServerImpl::Run(OpKernelContext* context,
                     AsyncOpKernel::DoneCallback done,
                     const string& listen_address,
                     int num_thread) {
  // Build Server.
  int64 max_send_message_size;
  int64 max_receive_message_size;
  string my_certs_filename;
  string my_key_filename;
  string peer_certs_filename;
  std::shared_ptr<grpc::ServerCredentials> creds;

  OP_REQUIRES_OK_ASYNC(context,
      ReadInt64FromEnvVar("EFL_SERVER_MAX_SEND_MESSAGE_SIZE", 1 << 30, &max_send_message_size),
      done);
  OP_REQUIRES_OK_ASYNC(context,
      ReadInt64FromEnvVar("EFL_SERVER_MAX_RECEIVE_MESSAGE_SIZE", 1 << 30, &max_receive_message_size),
      done);
  OP_REQUIRES_OK_ASYNC(context, ReadStringFromEnvVar("EFL_MY_CERTS_FILENAME", "", &my_certs_filename), done);
  OP_REQUIRES_OK_ASYNC(context, ReadStringFromEnvVar("EFL_MY_KEY_FILENAME", "", &my_key_filename), done);
  OP_REQUIRES_OK_ASYNC(context, ReadStringFromEnvVar("EFL_PEER_CERTS_FILENAME", "", &peer_certs_filename), done);

  if (!my_certs_filename.empty() && 
      !my_key_filename.empty()) {
    string my_certs;
    string my_key;
    OP_REQUIRES_OK_ASYNC(context, ReadFileToString(Env::Default(), my_certs_filename, &my_certs), done);
    OP_REQUIRES_OK_ASYNC(context, ReadFileToString(Env::Default(), my_key_filename, &my_key), done);
    grpc::SslServerCredentialsOptions::PemKeyCertPair pkcp = {my_key.c_str(), my_certs.c_str()};
    grpc::SslServerCredentialsOptions ssl_opts(GRPC_SSL_REQUEST_CLIENT_CERTIFICATE_BUT_DONT_VERIFY);
    if (!peer_certs_filename.empty()) {
      string peer_certs;
      OP_REQUIRES_OK_ASYNC(context, ReadFileToString(Env::Default(), peer_certs_filename, &peer_certs), done);
      ssl_opts.pem_root_certs = peer_certs;
    }
    ssl_opts.pem_key_cert_pairs.push_back(pkcp);
    creds = grpc::SslServerCredentials(ssl_opts);
  } else {
    creds = grpc::InsecureServerCredentials();
  }

  ServerBuilder builder;
  builder.SetMaxSendMessageSize(max_send_message_size);
  builder.SetMaxReceiveMessageSize(max_receive_message_size);
  builder.AddListeningPort(listen_address, creds);
  builder.RegisterService(&service_);
  cq_ = builder.AddCompletionQueue();
  // Start Server.
  server_ = builder.BuildAndStart();
  for (auto i = 0; i < num_thread; ++i) {
    threads_.push_back(std::unique_ptr<std::thread>(
        new std::thread(&ServerImpl::HandleRpcs, this)));
  }
}

void ServerImpl::HandleRpcs() {
  // You need to add some CallData in CompletionQueue. The more frequent the request, the larger the number of CallData.
  for (auto i = 0; i < 100; i++) {
    new SendMessageCallData(&service_, cq_.get(), &server_infos);
  }
  new ReaderStateCallData(&service_, cq_.get(), &server_infos);
  new CheckpointVersionCallData(&service_, cq_.get(), &server_infos);
  new ConnectionCallData(&service_, cq_.get(), &server_infos);

  void* tag;
  bool ok;
  is_running_ = true;
  while (cq_->Next(&tag, &ok)) {
    if (!ok) {
      break;
    }
    switch (*reinterpret_cast<MessageType*>(reinterpret_cast<char*>(tag) + sizeof(void**))) { // get type from tag.
      case SendMessage:
        reinterpret_cast<SendMessageCallData*>(tag)->Proceed();
        break;
      case ReaderState:
        reinterpret_cast<ReaderStateCallData*>(tag)->Proceed();
        break;
      case CheckpointVersion:
        reinterpret_cast<CheckpointVersionCallData*>(tag)->Proceed();
        break;
      case Connection:
        reinterpret_cast<ConnectionCallData*>(tag)->Proceed();
        break;
    }
  }
}

template<typename T_REQUEST, typename T_RESPONSE>
ServerImpl::CallData<T_REQUEST, T_RESPONSE>::CallData(
    TrainerService::AsyncService* service,
    ServerCompletionQueue* cq,
    AnyMap* any_map,
    const MessageType type)
    : type_(type),
      service_(service),
      cq_(cq),
      responder_(&ctx_),
      status_(CREATE) {
  server_call_infos_ = any_map;
}

ServerImpl::SendMessageCallData::SendMessageCallData(
    TrainerService::AsyncService* service,
    ServerCompletionQueue* cq,
    AnyMap* any_map)
    : CallData(service, cq, any_map, SendMessage) {
  Proceed();
}

ServerImpl::ReaderStateCallData::ReaderStateCallData(
    TrainerService::AsyncService* service,
    ServerCompletionQueue* cq,
    AnyMap* any_map)
    : CallData(service, cq, any_map, ReaderState) {
  Proceed();
}

ServerImpl::CheckpointVersionCallData::CheckpointVersionCallData(
    TrainerService::AsyncService* service,
    ServerCompletionQueue* cq,
    AnyMap* any_map)
    : CallData(service, cq, any_map, CheckpointVersion) {
  Proceed();
}

ServerImpl::ConnectionCallData::ConnectionCallData(
    TrainerService::AsyncService* service,
    ServerCompletionQueue* cq,
    AnyMap* any_map)
    : CallData(service, cq, any_map, Connection) {
  Proceed();
}

void ServerImpl::SendMessageCallData::SetCallback(std::function<void(SendMessageCallData*)> callback) {
  callback_ = callback;
}

void ServerImpl::ReaderStateCallData::SetCallback(std::function<void(ReaderStateCallData*)> callback) {
  callback_ = callback;
}

void ServerImpl::CheckpointVersionCallData::SetCallback(std::function<void(CheckpointVersionCallData*)> callback) {
  callback_ = callback;
}

void ServerImpl::ConnectionCallData::SetCallback(std::function<void(ConnectionCallData*)> callback) {
  callback_ = callback;
}

void ServerImpl::SendMessageCallData::OnComplete() {
  callback_(this);
}

void ServerImpl::ReaderStateCallData::OnComplete() {
  callback_(this);
}

void ServerImpl::CheckpointVersionCallData::OnComplete() {
  callback_(this);
}

void ServerImpl::ConnectionCallData::OnComplete() {
  callback_(this);
}

void ServerImpl::SendMessageCallData::Proceed() {
  if (status_ == CREATE) {
    status_ = PROCESS;
    service_->RequestSendMessage(&ctx_, &request_, &responder_, cq_, cq_, this);
  } else if (status_ == PROCESS) {
    // Consume a CallData and Produce a New CallData.
    new SendMessageCallData(service_, cq_, server_call_infos_);
    // Process Flow.
    auto mu = server_call_infos_->Get("call_map_mutex").Cast<mutex*>();
    auto callback_map = 
      server_call_infos_->Get("callback_map").Cast<std::unordered_map<string, std::function<void(SendMessageCallData*)>>*>();
    auto call_map = 
      server_call_infos_->Get("call_map").Cast<std::unordered_map<string, SendMessageCallData*>*>();
    mutex_lock m_lock(*mu);
    auto callback_iter = callback_map->find(request_.name() + "_" + std::to_string(request_.step()));
    if (callback_iter != callback_map->end()) {
      SetCallback(callback_iter->second);
      callback_map->erase(callback_iter);
      OnComplete();
    } else {
      auto call_map_iter = call_map->find(request_.name());
      if (call_map_iter != call_map->end()) {
        call_map_iter->second = this;
      } else {
        auto st = errors::NotFound("Tensor named " + request_.name() + " not registed.");
        SetResponseStatus(st);
        OnFinish();
      }
    }
  } else {
    delete this;
  }
}

void ServerImpl::ReaderStateCallData::Proceed() {
  if (status_ == CREATE) {
    status_ = PROCESS;
    service_->RequestGetReaderState(&ctx_, &request_, &responder_, cq_, cq_, this);
  } else if (status_ == PROCESS) {
    new ReaderStateCallData(service_, cq_, server_call_infos_);
    // Process Flow.
    auto mu = 
      server_call_infos_->Get("reader_state_mutex").Cast<mutex*>();
    auto callback = 
      server_call_infos_->Get("reader_state_cb").Cast<std::unordered_map<string, std::function<void(ReaderStateCallData*)>>*>();
    auto reader_state_call_data = 
      server_call_infos_->Get("reader_state_call_data").Cast<std::unordered_map<string, ReaderStateCallData*>*>();
    mutex_lock m_lock(*mu);
    auto iter = callback->find(request_.name());
    if (iter != callback->end()) {
      SetCallback(iter->second);
      callback->erase(iter);
      OnComplete();
    } else {
      auto call_data_iter = reader_state_call_data->find(request_.name());
      if (call_data_iter != reader_state_call_data->end()) {
        call_data_iter->second = this;
      } else {
        auto st = errors::NotFound("Dataset named " + request_.name() + "not registed.");
        SetResponseStatus(st);
        OnFinish();
      }
    }
  } else {
    delete this;
  }
}

void ServerImpl::CheckpointVersionCallData::Proceed() {
  if (status_ == CREATE) {
    status_ = PROCESS;
    service_->RequestGetCheckpointVersion(&ctx_, &request_, &responder_, cq_, cq_, this);
  } else if (status_ == PROCESS) {
    new CheckpointVersionCallData(service_, cq_, server_call_infos_);
    // Process Flow.
    auto mu =
      server_call_infos_->Get("ckpt_version_mutex").Cast<mutex*>();
    auto callback = 
      server_call_infos_->Get("ckpt_version_cb").Cast<std::function<void(CheckpointVersionCallData*)>*>();
    auto ckpt_version_call_data = 
      server_call_infos_->Get("ckpt_version_call_data").Cast<CheckpointVersionCallData**>();
    mutex_lock m_lock(*mu);
    if (*callback) {
      SetCallback(*callback);
      *callback = std::function<void(CheckpointVersionCallData*)>();
      OnComplete();
    } else {
      *ckpt_version_call_data = this;
    }
  } else {
    delete this;
  }
}

void ServerImpl::ConnectionCallData::Proceed() {
  if (status_ == CREATE) {
    status_ = PROCESS;
    service_->RequestConnect(&ctx_, &request_, &responder_, cq_, cq_, this);
  } else if (status_ == PROCESS) {
    new ConnectionCallData(service_, cq_, server_call_infos_);
    // Process Flow.
    auto mu =
      server_call_infos_->Get("connection_mutex").Cast<mutex*>();
    auto callback = 
      server_call_infos_->Get("connection_cb").Cast<std::function<void(ConnectionCallData*)>*>();
    auto connection_call_data = 
      server_call_infos_->Get("connection_call_data").Cast<ConnectionCallData**>();
    mutex_lock m_lock(*mu);
    if (*callback) {
      SetCallback(*callback);
      *callback = std::function<void(ConnectionCallData*)>();
      OnComplete();
    } else {
      *connection_call_data = this;
    }
  } else {
    delete this;
  }
}

}  // efl
}  // tensorflow

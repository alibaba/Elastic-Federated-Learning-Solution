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

#ifndef EFL_COMMUNICATION_CLIENT_H_
#define EFL_COMMUNICATION_CLIENT_H_

#include "tensorflow/core/framework/tensor.h"

#include "communication_service.h"

namespace tensorflow {
namespace efl {

// The implementation of client who sends requests to server.
class ClientImpl {
 public:
  // class for keeping state and data information.
  template<typename T_RESPONSE>
  class AsyncClientCall {
   public:
    explicit AsyncClientCall(MessageType type);
    virtual ~AsyncClientCall() = default;

    grpc::Status GetStatus() {
      return status_;
    }

    T_RESPONSE GetReply() {
      return reply_;
    }

    virtual void OnComplete() = 0;

   protected:
    const MessageType type_; // The type of this Call.
    T_RESPONSE reply_;
    ClientContext context_;
    grpc::Status status_;
    std::unique_ptr<ClientAsyncResponseReader<T_RESPONSE>> response_reader_;
    friend class ClientImpl;
  };

  class SendMessageAsyncClientCall final : public AsyncClientCall<MessageResponse> {
   public:
    SendMessageAsyncClientCall(std::function<void(SendMessageAsyncClientCall*)> callback);
    void OnComplete() override;
   private:
    std::function<void(SendMessageAsyncClientCall*)> callback_;
  };

  class ReaderStateAsyncClientCall final : public AsyncClientCall<GetReaderStateResponse> {
   public:
    ReaderStateAsyncClientCall(std::function<void(ReaderStateAsyncClientCall*)> callback);
    void OnComplete() override;
   private:
    std::function<void(ReaderStateAsyncClientCall*)> callback_;
  };

  class CheckpointVersionAsyncClientCall final : public AsyncClientCall<GetCheckpointVersionResponse> {
   public:
    CheckpointVersionAsyncClientCall(std::function<void(CheckpointVersionAsyncClientCall*)> callback);
    void OnComplete() override;
   private:
    std::function<void(CheckpointVersionAsyncClientCall*)> callback_;
  };

  class ConnectionAsyncClientCall final : public AsyncClientCall<ConnectionResponse> {
   public:
    ConnectionAsyncClientCall(std::function<void(ConnectionAsyncClientCall*)> callback);
    void OnComplete() override;
   private:
    std::function<void(ConnectionAsyncClientCall*)> callback_;
  };

  ClientImpl(std::shared_ptr<Channel> channel);
  ~ClientImpl();
  void Run(int thread_num);
  bool IsRunning();
  // Send a Tensor to server.
  void SendTensor(const Tensor* tensor, const string& name, const uint64 step,
                  std::function<void(SendMessageAsyncClientCall*)> callback);
  void RequestReaderState(const string& name, std::function<void(ReaderStateAsyncClientCall*)> callback);
  void RequestCheckpointVersion(std::function<void(CheckpointVersionAsyncClientCall*)> callback);
  void RequestConnection(std::function<void(ConnectionAsyncClientCall*)> callback);
  // Loop that receives responses from server.
  void AsyncCompleteRpc();
  bool Shutdown();

 private:
  std::unique_ptr<TrainerService::Stub> stub_;
  CompletionQueue cq_;
  volatile bool is_running_ = false;
  std::vector<std::unique_ptr<std::thread>> threads_;
};

} // efl
} // tensorflow

#endif // EFL_COMMUNICATION_CLIENT_H_

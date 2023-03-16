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

#ifndef EFL_COMMUNICATION_SERVICE_H_
#define EFL_COMMUNICATION_SERVICE_H_

#include <thread>
#include <grpcpp/grpcpp.h>

#include "tensorflow/core/framework/op_kernel.h"
#include "tensorflow/core/lib/core/status.h"

#include "protos/trainer_service.grpc.pb.h"

#include "any.h"

using grpc::Channel;
using grpc::ClientAsyncResponseReader;
using grpc::ClientContext;
using grpc::CompletionQueue;
using grpc::Server;
using grpc::ServerAsyncResponseWriter;
using grpc::ServerCompletionQueue;
using grpc::ServerContext;

using efl::TrainerService;
using efl::MessageRequest;
using efl::MessageResponse;
using efl::GetReaderStateRequest;
using efl::GetReaderStateResponse;
using efl::GetCheckpointVersionRequest;
using efl::GetCheckpointVersionResponse;
using efl::ConnectionRequest;
using efl::ConnectionResponse;

namespace tensorflow {
namespace efl {

// Type of Message.
enum MessageType { Connection, SendMessage, ReaderState, CheckpointVersion };

class ServerImpl {
 public:
  ~ServerImpl();
  // Run the Server.
  void Run(OpKernelContext* context, AsyncOpKernel::DoneCallback done, const string& listen_address, int num_thread);
  bool Shutdown();
  bool IsRunning();
  AnyMap server_infos;

  // Class encompasing the state and logic needed to serve a request.
  template<typename T_REQUEST, typename T_RESPONSE>
  class CallData {
   public:
    CallData(TrainerService::AsyncService* service, ServerCompletionQueue* cq, AnyMap* any_map, const MessageType type);
    virtual ~CallData() = default;

    T_RESPONSE* GetReply() { return &reply_; };
    T_REQUEST* GetRequest() { return &request_; };

    void OnFinish() {
      status_ = FINISH;
      responder_.Finish(reply_, grpc::Status::OK, this);
    };

    void SetResponseStatus(Status st) {
      reply_.set_code(st.code());
      reply_.set_msg(st.error_message());
    }

    virtual void Proceed() = 0;
    virtual void OnComplete() = 0;

   protected:
    const MessageType type_; // The type of this call.
    enum CallStatus { CREATE, PROCESS, FINISH }; // Status of this call.
    TrainerService::AsyncService* service_;
    ServerCompletionQueue* cq_;
    ServerContext ctx_;
    T_REQUEST request_;
    T_RESPONSE reply_;
    ServerAsyncResponseWriter<T_RESPONSE> responder_;
    CallStatus status_;
    AnyMap* server_call_infos_;

    friend class ServerImpl;
  };
  
  class SendMessageCallData final : public CallData<MessageRequest, MessageResponse> {
   public:
    SendMessageCallData(TrainerService::AsyncService* service, ServerCompletionQueue* cq, AnyMap* any_map);
    void SetCallback(std::function<void(SendMessageCallData*)> callback);
    void OnComplete() override;
    void Proceed() override;
   private:
    std::function<void(SendMessageCallData*)> callback_;
  };

  class ReaderStateCallData final : public CallData<GetReaderStateRequest, GetReaderStateResponse> {
   public:
    ReaderStateCallData(TrainerService::AsyncService* service, ServerCompletionQueue* cq, AnyMap* any_map);
    void SetCallback(std::function<void(ReaderStateCallData*)> callback);
    void OnComplete() override;
    void Proceed() override;
   private:
    std::function<void(ReaderStateCallData*)> callback_;
  };

  class CheckpointVersionCallData final : public CallData<GetCheckpointVersionRequest, GetCheckpointVersionResponse> {
   public:
    CheckpointVersionCallData(TrainerService::AsyncService* service, ServerCompletionQueue* cq, AnyMap* any_map);
    void SetCallback(std::function<void(CheckpointVersionCallData*)> callback);
    void OnComplete() override;
    void Proceed() override;
   private:
    std::function<void(CheckpointVersionCallData*)> callback_;
  };

  class ConnectionCallData final : public CallData<ConnectionRequest, ConnectionResponse> {
   public:
    ConnectionCallData(TrainerService::AsyncService* service, ServerCompletionQueue* cq, AnyMap* any_map);
    void SetCallback(std::function<void(ConnectionCallData*)> callback);
    void OnComplete() override;
    void Proceed() override;
   private:
    std::function<void(ConnectionCallData*)> callback_;
  };

 private:
  // Main Loop of Server.
  void HandleRpcs();
  std::unique_ptr<ServerCompletionQueue> cq_;
  TrainerService::AsyncService service_;
  std::unique_ptr<Server> server_;
  volatile bool is_running_ = false;
  std::vector<std::unique_ptr<std::thread>> threads_;
};

} // efl
} // tensorflow

#endif // EFL_COMMUNICATION_SERVICE_H_

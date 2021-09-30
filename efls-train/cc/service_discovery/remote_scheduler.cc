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

#include "cc/service_discovery/remote_scheduler.h"

#include <grpcpp/grpcpp.h>
#include <tensorflow/core/lib/core/errors.h>

#include "protos/cluster_service.grpc.pb.h"

namespace efl {

using namespace tensorflow;

namespace {
class GrpcRemoteScheduler : public SchedulerInterface {
 public:
  explicit GrpcRemoteScheduler(const std::string& addr);
  Status RegisterNode(const std::string& job, 
                      int64_t id,
                      const std::string& addr, 
                      int64_t my_version,
                      int64_t* version) override;
  Status GetCluster(ClusterDef* result) override;

 private:
  std::shared_ptr<grpc::Channel> channel_;
  std::unique_ptr<ClusterService::Stub> stub_;
};

GrpcRemoteScheduler::GrpcRemoteScheduler(const std::string& addr)
    : channel_(grpc::CreateChannel(addr, grpc::InsecureChannelCredentials())),
      stub_(ClusterService::NewStub(channel_)) {}

constexpr char kStreamRemovedMessage[] = "Stream removed";
bool IsStreamRemovedError(const ::grpc::Status& s) {
  return !s.ok() && s.error_code() == ::grpc::StatusCode::UNKNOWN &&
         s.error_message() == kStreamRemovedMessage;
}

Status Grpc2TfStatus(grpc::Status s) {
  if (s.ok()) {
    return Status::OK();
  } else {
    if (IsStreamRemovedError(s)) {
      return Status(tensorflow::error::UNAVAILABLE, s.error_message());
    }
    return Status(static_cast<tensorflow::error::Code>(s.error_code()),
                  s.error_message());
  }
}

Status GrpcRemoteScheduler::RegisterNode(
    const std::string& job, 
    int64_t id,
    const std::string& addr, 
    int64_t my_version,
    int64_t* version) {
  RegisterNodeRequest req;
  RegisterNodeResponse resp;
  req.set_task_name(job);
  req.set_task_index(id);
  req.set_addr(addr);
  req.set_version(my_version);
  grpc::ClientContext ctx;
  grpc::Status s = stub_->RegisterNode(&ctx, req, &resp);
  if (!s.ok()) {
    return Grpc2TfStatus(s);
  }

  if (resp.code() == 0) {
    *version = resp.version();
    return Status::OK();
  } else {
    Status st(resp.code(), resp.error_msg());
    return st;
  }
}

Status GrpcRemoteScheduler::GetCluster(ClusterDef* result) {
  GetClusterRequest req;
  GetClusterResponse resp;
  grpc::ClientContext ctx;
  grpc::Status s = stub_->GetCluster(&ctx, req, &resp);
  if (!s.ok()) {
    return Grpc2TfStatus(s);
  }

  if (resp.code() == 0) {
    result->MergeFrom(resp.cluster());
    return Status::OK();
  } else {
    Status st(resp.code(), resp.error_msg());
    return st;
  }
}

}  // namespace


SchedulerInterface* CreateRemoteScheduler(const string& addr) {
  return new GrpcRemoteScheduler(addr);
}

}  // namespace efl


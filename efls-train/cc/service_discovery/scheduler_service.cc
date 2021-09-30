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

#include "cc/service_discovery/scheduler_service.h"

#include <memory>
#include <grpcpp/grpcpp.h>
#include <tensorflow/core/lib/core/errors.h>

#include "cc/service_discovery/scheduler.h"
#include "cc/service_discovery/remote_kv.h"
#include "protos/cluster_service.grpc.pb.h"

namespace efl {

namespace {

using namespace tensorflow;

class SchedulerServiceImpl : public ClusterService::Service {
 public:
  explicit SchedulerServiceImpl(Scheduler* scheduler) : scheduler_(scheduler) {}
  grpc::Status RegisterNode(
      grpc::ServerContext* context,
      const RegisterNodeRequest* request,
      RegisterNodeResponse* reply) override {
    (void)context;
    int64_t new_ver;
    Status st = scheduler_->RegisterNode(
        request->task_name(), 
        request->task_index(), 
        request->addr(),
        request->version(), 
        &new_ver);
    if (st.ok()) {
      reply->set_code(st.code());
      reply->set_version(new_ver);
    } else {
      reply->set_code(st.code());
      reply->set_error_msg(st.error_message());
    }

    return grpc::Status::OK;
  }

  grpc::Status GetCluster(
      grpc::ServerContext* context,
      const GetClusterRequest* request,
      GetClusterResponse* reply) override {
    (void)context;
    (void)request;
    ClusterDef def;
    Status st = scheduler_->GetCluster(&def);
    if (st.ok()) {
      reply->set_code(st.code());
      reply->mutable_cluster()->MergeFrom(def);
    } else {
      reply->set_code(st.code());
      reply->set_error_msg(st.error_message());
    }

    return grpc::Status::OK;
  }

 private:
  Scheduler* scheduler_;
};

class GrpcSchedulerService : public SchedulerService {
 public:
  explicit GrpcSchedulerService(
      const ClusterDef& def, const std::string& ip, 
      int port, const std::string& addr)
    : def_(def), ip_(ip), port_(port), addr_(addr) {}
  Status Start() override;
  void Join() override;
 private:
  ClusterDef def_;
  std::string ip_;
  int port_;
  std::string addr_;
  std::unique_ptr<Scheduler> scheduler_;
  std::unique_ptr<SchedulerServiceImpl> service_;
  std::unique_ptr<grpc::Server> grpc_server_;
};

Status GrpcSchedulerService::Start() {
  scheduler_.reset(new Scheduler(def_));
  service_.reset(new SchedulerServiceImpl(scheduler_.get()));
  grpc::ServerBuilder builder;
  builder.AddListeningPort(
      "0.0.0.0:" + std::to_string(port_),
      grpc::InsecureServerCredentials(), &port_);
  builder.RegisterService(service_.get());
  grpc_server_ = builder.BuildAndStart();
  std::string my_addr = ip_ + ":" + std::to_string(port_);
  return RemoteKVManager::Instance()->Put(addr_, my_addr);
}

void GrpcSchedulerService::Join() {
  grpc_server_->Wait();
}

}  // namespace

SchedulerService* NewSchedulerService(
    const tensorflow::ClusterDef& def, 
    const std::string& ip, 
    int port, 
    const std::string& kvaddr) {
  return new GrpcSchedulerService(def, ip, port, kvaddr);
}

}  // namespace efl


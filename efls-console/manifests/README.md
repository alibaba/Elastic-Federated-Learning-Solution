# 部署手册

### 服务

| role | database | console |
| :------ | :------ | :------ |
| host | msyql | ali-console-host |
| peer | mysqlpeer | ali-console-peer |

host 是一方的服务，peer 是另一方的服务，双方功能上是对等的，是 P2P 的设计，没有 master 管控。  
控制台依赖了两个服务，mysql 和 minio，前者提供 DBMS 能力，后者提供对象存储能力。  

## 流程
1. 一键部署 host 和 peer 服务，先部署 host，其中包含了双方共用的 minio 服务拉起。  
   注意修改 `console-host.yaml` 中 l83 中的 nodeName，l203 中的服务 url（注意使用公网可以访问的地址，例子中给出的是 Ingress 的地址）；  
   注意修改 `console-peer.yaml` 中 l95 中的服务 url（注意使用公网可以访问的地址，例子中给出的是 Ingress 的地址）；  

   
```commandline
kubectl create -f ./manifests/console-aliyun-host.yaml
kubectl create -f ./manifests/console-aliyun-peer.yaml
```  

2. 数据库初始化
命令行中填入双边的公网访问地址，初始化数据库
```commandline
curl --request POST 'http://xxx/host/db'
curl --request POST 'http://xxx/peer/db'
```

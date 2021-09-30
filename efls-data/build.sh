#!/bin/sh
python3 -m grpc_tools.protoc -I . --python_out=. ./xfl/data/tfreecord/tfrecords.proto
python3 -m grpc_tools.protoc -I . --python_out=. --grpc_python_out=. ./proto/*.proto

(cd xfl-java; mvn clean package)
mkdir -p lib/
mv xfl-java/target/efls-flink-connectors-1.0-SNAPSHOT.jar lib/
rm -rf xfl-java/target

DOMAIN_NAME="*.alifl.com"
openssl req -x509 -sha256 -nodes -days 365 -newkey rsa:2048 -keyout ./deploy/quickstart/tls.key -out ./deploy/quickstart/tls.crt -subj "/CN=${DOMAIN_NAME}/O=${DOMAIN_NAME}"
kubectl create secret tls tls-secret --key ./deploy/quickstart/tls.key --cert ./deploy/quickstart/tls.crt

[ ! $YOUR_DOCKER_NAME ] && YOUR_DOCKER_NAME="efls_docker:latest"
sudo docker build -t $YOUR_DOCKER_NAME -f ./Dockerfile ./


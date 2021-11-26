#!/bin/sh
[ ! $YOUR_DOCKER_NAME ] && YOUR_DOCKER_NAME="efls_docker:latest"
sudo docker build -t $YOUR_DOCKER_NAME -f ./Dockerfile ./

IP=$1
PORT=$2
HOST_NAME=$3
BASE_DIR=$(cd "$(dirname "$0")/"; pwd)
cd $BASE_DIR
python -m grpc_tools.protoc -I . --python_out=. --grpc_python_out=. *.proto
python grpc_ingress_test.py -i $IP -p $PORT -n $HOST_NAME

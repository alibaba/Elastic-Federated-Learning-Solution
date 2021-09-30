from __future__ import print_function

import argparse
import time
import json

import grpc
import helloworld_pb2
import helloworld_pb2_grpc

service_config_json = json.dumps({
    "methodConfig": [{
        "name": [{
            "service": "helloworld.Greeter",
            "method": "SayHello"
        }],
        "retryPolicy": {
            "maxAttempts": 5,
            "initialBackoff": "1s",
            "maxBackoff": "10s",
            "backoffMultiplier": 2,
            "retryableStatusCodes": ["UNAVAILABLE"],
        },
    }]
})

def run(ip, port, host_name):
  with open('tls.crt', 'rb') as f:
    trusted_certs = f.read()
  print('Try to greete with %s@%s:%s' % (host_name, ip, port))

  credentials = grpc.ssl_channel_credentials(root_certificates=trusted_certs)
  channel = grpc.secure_channel(
    '{}:{}'.format(ip, port), credentials,
    options=(('grpc.ssl_target_name_override', host_name,),
             ('grpc.max_send_message_length', 100 * 1024 * 1024),
             ('grpc.max_receive_message_length', 100 * 1024 * 1024),
             ("grpc.enable_retries", 1),
             ("grpc.service_config", service_config_json)))

  start = time.time()
  stub = helloworld_pb2_grpc.GreeterStub(channel)
  request = helloworld_pb2.HelloRequest(name='from alibaba')
  try:
    response = stub.SayHello(request)
    end = time.time()
    print("Greeter client received: " + response.message, " rt :{} s".format(end - start))
    print("Grpc Test Ok!")
  except grpc.RpcError as e:
    print(e.code())
    print(e.details())


if __name__ == '__main__':
  parser = argparse.ArgumentParser(description='grpc test tool command')
  parser.add_argument('-i', '--ip', type=str,
                      help='grpc server ip', required=True)
  parser.add_argument('-p', '--port', type=str,
                      help='grpc server port', required=True)
  parser.add_argument('-n', '--host_name', type=str,
                      help='grpc server host name', required=True)
  args = parser.parse_args()
  run(args.ip, args.port, args.host_name)

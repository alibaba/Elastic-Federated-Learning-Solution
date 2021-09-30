import os

from xfl.k8s.k8s_client import K8sClient

client = K8sClient()
if os.environ['K8S_CONFIG'] is not None and len(os.environ['K8S_CONFIG']) > 0:
  client.init(os.environ['K8S_CONFIG'])
else:
  client.init(os.path.join(os.environ['HOME'], '.kube', 'config'))

pod = client.get_pod("apple-app")
print (pod.metadata.uid)

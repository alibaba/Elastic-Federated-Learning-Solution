from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import os
from kubernetes import client, config
from kubernetes.client.rest import ApiException
from kubernetes.stream import stream


class K8sController():

    def __init__(self, kube_config=None):
        if not kube_config:
            config.load_incluster_config()
        else:
            config.load_kube_config(config_file=kube_config)
        self._appv1api = client.AppsV1Api()
        self._corev1api = client.CoreV1Api()
        self._networkv1api = client.NetworkingV1beta1Api()
        self._extendv1api = client.ExtensionsV1beta1Api()
        self._batchv1api = client.BatchV1Api()

    def deployment_ready(self, deploy_name, namespace='default'):
        ret = self._appv1api.read_namespaced_deployment(deploy_name, namespace)
        return ret.status.ready_replicas == ret.status.replicas

    def job_ready(self, job_name, namespace='default'):
        pod_names = self.get_job_pod_names(job_name, namespace=namespace)
        return len(pod_names) > 0

    def get_job_status(self, job_name, namespace='default'):
        ret = self._batchv1api.read_namespaced_job(job_name, namespace)
        if ret.status.succeeded is not None:
            return 'Success'
        pods = self._corev1api.list_namespaced_pod(
            namespace=namespace,
            label_selector='job-name={}'.format(job_name))
        if len(pods.items) > 1:
            return 'Error'
        return pods.items[0].status.phase

    def get_job_pod_names(self, job_name, namespace='default', get_all_pods=False):
        pod_names = []
        pods = self._corev1api.list_namespaced_pod(
            namespace=namespace,
            label_selector='job-name={}'.format(job_name))
        for pod in pods.items:
            if get_all_pods or pod.status.phase == "Running":
                pod_names.append(pod.metadata.name)
        return pod_names

    def get_pod_log(self, pod_name, namespace='default'):
        return self._corev1api.read_namespaced_pod_log(pod_name, namespace)

    def get_deployment_replica_set(self, deploy_name, namespace='default'):
        ret = self._appv1api.read_namespaced_deployment(deploy_name, namespace)
        if ret.status.ready_replicas == ret.status.replicas:
            appid = ret.status.conditions[-1].message.split(" ")[1][1:-1]
            return appid
        else:
            raise RuntimeError(
                "Deployment is pendding, ready pods: {}/{}".format(ret.status.ready_replicas, ret.status.replicas))

    def get_deployment_available_pod_names(self, deploy_name, namespace='default'):
        appid = self.get_deployment_replica_set(deploy_name, namespace=namespace)
        pod_names = []
        pod_ret = self._corev1api.list_namespaced_pod(namespace)
        for i in pod_ret.items:
            if appid in i.metadata.name and i.metadata.deletion_timestamp is None:
                pod_names.append(i.metadata.name)
        return pod_names

    def get_pod_ip(self, pod_name, namespace='default'):
        pod_ret = self._corev1api.read_namespaced_pod(pod_name, namespace)
        return pod_ret.status.pod_ip

    def execute_pod(self, pod_name, cmd_str, namespace='default'):
        os.system("kubectl exec -it {} -n {} -- {}".format(pod_name, namespace, cmd_str))

    def create_service(self, metadata, spec, namespace='default'):
        request = client.V1Service(api_version='v1',
                                   kind='Service',
                                   metadata=metadata,
                                   spec=spec)
        self._corev1api.create_namespaced_service(
            namespace, request)

    def create_ingress(self, metadata, spec, namespace='default'):
        request = client.NetworkingV1beta1Ingress(
            api_version='networking.k8s.io/v1beta1',
            kind='Ingress',
            metadata=metadata,
            spec=spec)
        self._networkv1api.create_namespaced_ingress(
            namespace, request)

    def create_deployment(self, body, namespace='default'):
        self._appv1api.create_namespaced_deployment(
            body=body,
            namespace=namespace)

    def create_job(self, body, namespace='default'):
        self._batchv1api.create_namespaced_job(
            body=body,
            namespace=namespace)

    def delete_service(self, service_name, namespace='default'):
        try:
            self._corev1api.delete_namespaced_service(service_name, namespace=namespace)
        except ApiException as e:
            print("Service {} delete failed, err msg: {}".format(service_name, e))

    def delete_ingress(self, ingress_name, namespace='default'):
        try:
            self._extendv1api.delete_namespaced_ingress(ingress_name, namespace=namespace)
        except ApiException as e:
            print("Ingress {} delete failed, err msg: {}".format(ingress_name, e))

    def delete_deployment(self, deploy_name, namespace='default'):
        try:
            self._appv1api.delete_namespaced_deployment(deploy_name, namespace=namespace)
        except ApiException as e:
            print("Deployment {} delete failed, err msg: {}".format(deploy_name, e))

    def delete_job(self, job_name, namespace='default'):
        try:
            self._batchv1api.delete_namespaced_job(job_name, namespace=namespace, propagation_policy='Background')
        except ApiException as e:
            print("Job {} delete failed, err msg: {}".format(job_name, e))

# -*- coding: utf8 -*-

import yaml
from argo.workflows.client import ApiClient, WorkflowServiceApi, Configuration, V1alpha1WorkflowCreateRequest


def main():
    config = Configuration(host="http://100.82.84.137:32222")
    client = ApiClient(configuration=config)
    service = WorkflowServiceApi(api_client=client)
    with open("test_template.py.yaml") as f:
        manifest: dict = yaml.safe_load(f)
    del manifest['spec']['serviceAccountName']
    service.create_workflow('argo', V1alpha1WorkflowCreateRequest(workflow=manifest))


if __name__ == '__main__':
    main()

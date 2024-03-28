#   Copyright 2021 Dynatrace LLC
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
import json
from datetime import datetime

from logs_ingest.main import parse_record
from logs_ingest.mapping import RESOURCE_NAME_ATTRIBUTE, RESOURCE_TYPE_ATTRIBUTE, RESOURCE_GROUP_ATTRIBUTE, \
    SUBSCRIPTION_ATTRIBUTE, RESOURCE_ID_ATTRIBUTE
from logs_ingest.self_monitoring import SelfMonitoring

kube_audit_record = {
    "operationName": "Microsoft.ContainerService/managedClusters/diagnosticLogs/Read",
    "category": "kube-audit",
    "ccpNamespace": "5db19e5910fd970001fb355e",
    "resourceId": "/SUBSCRIPTIONS/97E9B03F-04D6-4B69-B307-35F483F7ED81/RESOURCEGROUPS/DEMO-BACKEND-RG/PROVIDERS/MICROSOFT.CONTAINERSERVICE/MANAGEDCLUSTERS/DEMO-AKS",
    "properties": {
        "log": "{\"kind\":\"Event\",\"apiVersion\":\"audit.k8s.io/v1\",\"level\":\"RequestResponse\",\"auditID\":\"7df19974-f894-454b-a1f2-137258598c45\",\"stage\":\"ResponseComplete\",\"requestURI\":\"/apis/authorization.k8s.io/v1beta1/subjectaccessreviews\",\"verb\":\"create\",\"user\":{\"username\":\"system:serviceaccount:kube-system:metrics-server\",\"uid\":\"82956dc9-f65d-11e9-b4d7-da0e02e04c9e\",\"groups\":[\"system:serviceaccounts\",\"system:serviceaccounts:kube-system\",\"system:authenticated\"]},\"sourceIPs\":[\"52.188.216.128\"],\"userAgent\":\"metrics-server/v0.0.0 (linux/amd64) kubernetes/$Format\",\"objectRef\":{\"resource\":\"subjectaccessreviews\",\"apiGroup\":\"authorization.k8s.io\",\"apiVersion\":\"v1beta1\"},\"responseStatus\":{\"metadata\":{},\"code\":201},\"requestObject\":{\"kind\":\"SubjectAccessReview\",\"apiVersion\":\"authorization.k8s.io/v1beta1\",\"metadata\":{\"creationTimestamp\":null},\"spec\":{\"nonResourceAttributes\":{\"path\":\"/apis/metrics.k8s.io/v1beta1\",\"verb\":\"get\"},\"user\":\"system:serviceaccount:kube-system:generic-garbage-collector\",\"group\":[\"system:serviceaccounts\",\"system:serviceaccounts:kube-system\",\"system:authenticated\"]},\"status\":{\"allowed\":false}},\"responseObject\":{\"kind\":\"SubjectAccessReview\",\"apiVersion\":\"authorization.k8s.io/v1beta1\",\"metadata\":{\"creationTimestamp\":null,\"managedFields\":[{\"manager\":\"metrics-server\",\"operation\":\"Update\",\"apiVersion\":\"authorization.k8s.io/v1beta1\",\"time\":\"2021-02-02T15:00:00Z\",\"fieldsType\":\"FieldsV1\",\"fieldsV1\":{\"f:spec\":{\"f:group\":{},\"f:nonResourceAttributes\":{\".\":{},\"f:path\":{},\"f:verb\":{}},\"f:user\":{}}}}]},\"spec\":{\"nonResourceAttributes\":{\"path\":\"/apis/metrics.k8s.io/v1beta1\",\"verb\":\"get\"},\"user\":\"system:serviceaccount:kube-system:generic-garbage-collector\",\"group\":[\"system:serviceaccounts\",\"system:serviceaccounts:kube-system\",\"system:authenticated\"]},\"status\":{\"allowed\":true,\"reason\":\"RBAC: allowed by ClusterRoleBinding \\\"system:discovery\\\" of ClusterRole \\\"system:discovery\\\" to Group \\\"system:authenticated\\\"\"}},\"requestReceivedTimestamp\":\"2021-02-02T15:00:00.703531Z\",\"stageTimestamp\":\"2021-02-02T15:00:00.704551Z\",\"annotations\":{\"authentication.k8s.io/legacy-token\":\"system:serviceaccount:kube-system:metrics-server\",\"authorization.k8s.io/decision\":\"allow\",\"authorization.k8s.io/reason\":\"RBAC: allowed by ClusterRoleBinding \\\"metrics-server:system:auth-delegator\\\" of ClusterRole \\\"system:auth-delegator\\\" to ServiceAccount \\\"metrics-server/kube-system\\\"\",\"k8s.io/deprecated\":\"true\",\"k8s.io/removed-release\":\"1.22\"}}\n",
        "stream": "stdout",
        "pod": "kube-apiserver-6b497d8d5f-rb9qn"
    },
    "time": "2021-02-02T15:00:00.0000000Z",
    "Cloud": "AzureCloud",
    "Environment": "prod",
    "UnderlayClass": "hcp-underlay",
    "UnderlayName": "hcp-underlay-eastus-cx-424"
}

kube_audit_expected_output = {
    'cloud.provider': 'Azure',
    'timestamp': '2021-02-02T15:00:00.0000000Z',
    'log.source': 'kube-audit',
    'k8s.pod.name': 'kube-apiserver-6b497d8d5f-rb9qn',
    'content': json.dumps(kube_audit_record),
    RESOURCE_ID_ATTRIBUTE: "/SUBSCRIPTIONS/97E9B03F-04D6-4B69-B307-35F483F7ED81/RESOURCEGROUPS/DEMO-BACKEND-RG/PROVIDERS/MICROSOFT.CONTAINERSERVICE/MANAGEDCLUSTERS/DEMO-AKS",
    SUBSCRIPTION_ATTRIBUTE: "97E9B03F-04D6-4B69-B307-35F483F7ED81",
    RESOURCE_GROUP_ATTRIBUTE: "DEMO-BACKEND-RG",
    RESOURCE_TYPE_ATTRIBUTE: "MICROSOFT.CONTAINERSERVICE/MANAGEDCLUSTERS",
    RESOURCE_NAME_ATTRIBUTE: "DEMO-AKS",
    'dt.entity.custom_device': 'CUSTOM_DEVICE-895AED2A0D6C6D33',
    'dt.source_entity': 'CUSTOM_DEVICE-895AED2A0D6C6D33',
    'severity': 'Informational'
}

kube_controller_manager_record = {
    "attrs": "{\"annotation.io.kubernetes.container.hash\"=>\"f9c52847\", \"annotation.io.kubernetes.container.restartCount\"=>\"0\", \"annotation.io.kubernetes.container.terminationMessagePath\"=>\"/dev/termination-log\", \"annotation.io.kubernetes.container.terminationMessagePolicy\"=>\"File\", \"annotation.io.kubernetes.pod.terminationGracePeriod\"=>\"30\", \"description\"=>\"go based runner for distroless scenarios\", \"io.kubernetes.container.logpath\"=>\"/var/log/pods/5db19e5910fd970001fb355e_kube-controller-manager-84595d6f94-wcj7p_6d0a2d94-54fa-43d8-ad40-bc264fb0682c/kube-controller-manager/0.log\", \"io.kubernetes.container.name\"=>\"kube-controller-manager\", \"io.kubernetes.docker.type\"=>\"container\", \"io.kubernetes.pod.name\"=>\"kube-controller-manager-84595d6f94-wcj7p\", \"io.kubernetes.pod.namespace\"=>\"5db19e5910fd970001fb355e\", \"io.kubernetes.pod.uid\"=>\"6d0a2d94-54fa-43d8-ad40-bc264fb0682c\", \"io.kubernetes.sandbox.id\"=>\"356d4603057e511dfbd68039a7614443ae2db7efe8250953699e5f10b8b6339d\", \"maintainers\"=>\"Kubernetes Authors\"}",
    "operationName": "Microsoft.ContainerService/managedClusters/diagnosticLogs/Read",
    "category": "kube-controller-manager",
    "ccpNamespace": "5db19e5910fd970001fb355e",
    "resourceId": "/SUBSCRIPTIONS/97E9B03F-04D6-4B69-B307-35F483F7ED81/RESOURCEGROUPS/DEMO-BACKEND-RG/PROVIDERS/MICROSOFT.CONTAINERSERVICE/MANAGEDCLUSTERS/DEMO-AKS",
    "properties": {
        "log": "I0202 15:03:28.853066       1 event.go:291] \"Event occurred\" object=\"default/grafana\" kind=\"Service\" apiVersion=\"v1\" type=\"Normal\" reason=\"EnsuringLoadBalancer\" message=\"Ensuring load balancer\"\n",
        "stream": "stderr",
        "pod": "kube-controller-manager-84595d6f94-wcj7p",
        "containerID": "98350a126e2c7d3a4a9f34465ea68e638ad4ae25053be0816de3c9db11796cef"
    },
    "time": "2021-02-02T15:03:28.0000000Z",
    "Cloud": "AzureCloud",
    "Environment": "prod",
    "UnderlayClass": "hcp-underlay",
    "UnderlayName": "hcp-underlay-eastus-cx-424"
}

kube_controller_manager_expected_output = {
    "cloud.provider": "Azure",
    "timestamp": "2021-02-02T15:03:28.0000000Z",
    "log.source": "kube-controller-manager",
    "k8s.pod.name": "kube-controller-manager-84595d6f94-wcj7p",
    "content": json.dumps(kube_controller_manager_record),
    RESOURCE_ID_ATTRIBUTE: "/SUBSCRIPTIONS/97E9B03F-04D6-4B69-B307-35F483F7ED81/RESOURCEGROUPS/DEMO-BACKEND-RG/PROVIDERS/MICROSOFT.CONTAINERSERVICE/MANAGEDCLUSTERS/DEMO-AKS",
    SUBSCRIPTION_ATTRIBUTE: "97E9B03F-04D6-4B69-B307-35F483F7ED81",
    RESOURCE_GROUP_ATTRIBUTE: "DEMO-BACKEND-RG",
    RESOURCE_TYPE_ATTRIBUTE: "MICROSOFT.CONTAINERSERVICE/MANAGEDCLUSTERS",
    RESOURCE_NAME_ATTRIBUTE: "DEMO-AKS",
    'dt.entity.custom_device': 'CUSTOM_DEVICE-895AED2A0D6C6D33',
    'dt.source_entity': 'CUSTOM_DEVICE-895AED2A0D6C6D33',
    'severity': 'Informational'
}



def test_kube_audit():
    output = parse_record(kube_audit_record, SelfMonitoring(execution_time=datetime.utcnow()))
    assert output == kube_audit_expected_output


def test_kube_controller_manager():
    output = parse_record(kube_controller_manager_record, SelfMonitoring(execution_time=datetime.utcnow()))
    assert output == kube_controller_manager_expected_output


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

import pytest

from logs_ingest.main import parse_record
from logs_ingest.mapping import RESOURCE_NAME_ATTRIBUTE, RESOURCE_TYPE_ATTRIBUTE, RESOURCE_GROUP_ATTRIBUTE, \
    SUBSCRIPTION_ATTRIBUTE, RESOURCE_ID_ATTRIBUTE
from logs_ingest.self_monitoring import SelfMonitoring

alert_record = {
    "time": "2021-02-09T11:15:57.0501894Z",
    "resourceId": "/SUBSCRIPTIONS/69B51384-146C-4685-9DAB-5AE01877D7B8/RESOURCEGROUPS/DTMAWO/PROVIDERS/MICROSOFT.INSIGHTS/ACTIVITYLOGALERTS/AA - ALERT ADMINISTRACYJNY",
    "correlationId": "d9381714-0c92-49e4-b471-d67199f857c0",
    "operationName": "Microsoft.Insights/ActivityLogAlerts/Activated/action",
    "level": "Information",
    "resultType": "Succeeded.",
    "resultDescription": "Alert: AA - Alert Administracyjny called on action groups : sendwebhook",
    "category": "Alert",
    "properties": {
        "eventCategory": "Alert",
        "eventProperties": {
            "subscriptionId": "69b51384-146c-4685-9dab-5ae01877d7b8",
            "eventDataId": "d5d50404-bea9-471b-9894-400dc40b77e0",
            "resourceGroup": "",
            "resourceId": "/subscriptions/69b51384-146c-4685-9dab-5ae01877d7b8/providers/microsoft.insights/diagnosticSettings/eventhub",
            "eventTimestamp": "2021-02-09T11:14:10.8715705Z",
            "operationName": "microsoft.insights/diagnosticSettings/write",
            "status": "Started"
        }
    }
}

alert_expected_output = {
    "cloud.provider": "Azure",
    "timestamp": "2021-02-09T11:15:57.0501894Z",
    "log.source": "Activity Log - Alert",
    "severity": "Information",
    "content": json.dumps(alert_record),
    RESOURCE_ID_ATTRIBUTE: "/SUBSCRIPTIONS/69B51384-146C-4685-9DAB-5AE01877D7B8/RESOURCEGROUPS/DTMAWO/PROVIDERS/MICROSOFT.INSIGHTS/ACTIVITYLOGALERTS/AA - ALERT ADMINISTRACYJNY",
    SUBSCRIPTION_ATTRIBUTE: "69B51384-146C-4685-9DAB-5AE01877D7B8",
    RESOURCE_GROUP_ATTRIBUTE: "DTMAWO",
    RESOURCE_TYPE_ATTRIBUTE: "MICROSOFT.INSIGHTS/ACTIVITYLOGALERTS",
    RESOURCE_NAME_ATTRIBUTE: "AA - ALERT ADMINISTRACYJNY",
    "audit.action": "Microsoft.Insights/ActivityLogAlerts/Activated/action",
    "audit.result": "Succeeded"
}

administrative_record = {
    "time": "2021-02-09T11:38:31.6315770Z",
    "resourceId": "/SUBSCRIPTIONS/69B51384-146C-4685-9DAB-5AE01877D7B8/RESOURCEGROUPS/MW-GR1/PROVIDERS/MICROSOFT.STORAGE/STORAGEACCOUNTS/DTMWSTORAGE1",
    "operationName": "MICROSOFT.STORAGE/STORAGEACCOUNTS/LISTACCOUNTSAS/ACTION",
    "category": "Administrative",
    "resultType": "Failure",
    "resultSignature": "Failed.NotFound",
    "durationMs": "20",
    "callerIpAddress": "40.112.242.0",
    "correlationId": "3661e441-e836-4795-9148-c843525399bd",
    "identity": {
        "authorization": {
            "scope": "/subscriptions/69b51384-146c-4685-9dab-5ae01877d7b8/resourceGroups/mw-gr1/providers/Microsoft.Storage/storageAccounts/dtmwstorage1",
            "action": "Microsoft.Storage/storageAccounts/listAccountSas/action",
            "evidence": {
                "role": "Azure Eventhubs Service Role",
                "roleAssignmentScope": "/subscriptions/69b51384-146c-4685-9dab-5ae01877d7b8",
                "roleAssignmentId": "ab1ae998ac0c422bb1d484519bb503b7",
                "roleDefinitionId": "eb8e19915de042a6a64b29b059341b7b",
                "principalId": "e7018f6488e246afa1977b9084d8346a",
                "principalType": "ServicePrincipal"
            }
        },
        "claims": {
            "aud": "https://management.core.windows.net/",
            "iss": "https://sts.windows.net/70ebe3a3-5b30-435d-9d67-7716d74ca190/",
            "iat": "1612785544",
            "nbf": "1612785544",
            "exp": "1612872244",
            "aio": "AUQAu/8TAAAAlSdddOpuxGAphkybH3N4EdIz5xuTrAwxum1uL6e+FO03x2G20rOQD3KvxRiAhzEAPcXk61pJ4Tsv6IzQ9phcsA==",
            "appid": "04b07795-8ddb-461a-bbee-02f9e1bf7b46",
            "appidacr": "0",
            "http://schemas.microsoft.com/2012/01/devicecontext/claims/identifier": "7ey32c5a-9347-4f4c-8518-178b7cc0c1b7",
            "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/surname": "Kowalski",
            "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/givenname": "Jan",
            "uti": "gVQtWBk9fkuRyF80Tn1XAA",
            "ver": "1.0",
            "xms_tcdt": "1415644249",
            "http://schemas.microsoft.com/identity/claims/scope": "user_impersonation",
            "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/nameidentifier": "SQDfplmjvs2zlBolO2iAHUNgznOepOpteDiCAs0",
            "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/name": "jan.kowalski@somewhere.com",
            "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/upn": "jan.kowalski@somewhere.com",
        }
    },
    "level": "Error",
    "properties": {
        "statusCode": "NotFound",
        "serviceRequestId": None,
        "statusMessage": "{\"error\":{\"code\":\"ResourceGroupNotFound\",\"message\":\"Resource group 'mw-gr1' could not be found.\"}}",
        "eventCategory": "Administrative",
        "entity": "/SUBSCRIPTIONS/69B51384-146C-4685-9DAB-5AE01877D7B8/RESOURCEGROUPS/MW-GR1/PROVIDERS/MICROSOFT.STORAGE/STORAGEACCOUNTS/DTMWSTORAGE1",
        "message": "MICROSOFT.STORAGE/STORAGEACCOUNTS/LISTACCOUNTSAS/ACTION",
        "hierarchy": "70ebe3a3-5b30-435d-9d67-7716d74ca190/GroupLevel0/GroupALevel1/GroupAALevel2/69b51384-146c-4685-9dab-5ae01877d7b8"
    }
}

administrative_expected_output = {
    "cloud.provider": "Azure",
    "timestamp": "2021-02-09T11:38:31.6315770Z",
    "log.source": "Activity Log - Administrative",
    "severity": "Error",
    "content": json.dumps(administrative_record),
    RESOURCE_ID_ATTRIBUTE: "/SUBSCRIPTIONS/69B51384-146C-4685-9DAB-5AE01877D7B8/RESOURCEGROUPS/MW-GR1/PROVIDERS/MICROSOFT.STORAGE/STORAGEACCOUNTS/DTMWSTORAGE1",
    SUBSCRIPTION_ATTRIBUTE: "69B51384-146C-4685-9DAB-5AE01877D7B8",
    RESOURCE_GROUP_ATTRIBUTE: "MW-GR1",
    RESOURCE_TYPE_ATTRIBUTE: "MICROSOFT.STORAGE/STORAGEACCOUNTS",
    RESOURCE_NAME_ATTRIBUTE: "DTMWSTORAGE1",
    "dt.source_entity": "AZURE_STORAGE_ACCOUNT-A5A9F4A68D9B0D44",
    "audit.identity": "jan.kowalski@somewhere.com",
    "audit.action": "MICROSOFT.STORAGE/STORAGEACCOUNTS/LISTACCOUNTSAS/ACTION",
    "audit.result": "Failed.NotFound"
}

policy_record = {
    "time": "2021-02-09T08:45:27.3186996Z",
    "resourceId": "/SUBSCRIPTIONS/97E9B03F-04D6-4B69-B307-35F483F7ED81/RESOURCEGROUPS/AZUREBATCH-CB989D3E-4BCC-4ABC-BC32-D1B6DFA2E6B0-C/PROVIDERS/MICROSOFT.COMPUTE/VIRTUALMACHINESCALESETS/CB989D3E-4BCC-4ABC-BC32-D1B6DFA2E6B0-AZUREBATCH-VMSS-D",
    "operationName": "MICROSOFT.AUTHORIZATION/POLICIES/AUDIT/ACTION",
    "category": "Policy",
    "resultType": "Success",
    "resultSignature": "Succeeded.",
    "durationMs": "0",
    "callerIpAddress": "20.38.85.224",
    "correlationId": "d24b4648-5c79-4e6c-af4b-aa7f066669e8",
    "identity": {
        "authorization": {
            "scope": "/subscriptions/97e9b03f-04d6-4b69-b307-35f483f7ed81/resourcegroups/AzureBatch-cb989d3e-4bcc-4abc-bc32-d1b6dfa2e6b0-C/providers/Microsoft.Compute/virtualMachineScaleSets/cb989d3e-4bcc-4abc-bc32-d1b6dfa2e6b0-AzureBatch-VMSS-D",
            "action": "Microsoft.Compute/virtualMachineScaleSets/write",
            "evidence": {
                "role": "Contributor",
                "roleAssignmentScope": "/subscriptions/97e9b03f-04d6-4b69-b307-35f483f7ed81",
                "roleAssignmentId": "9fdcd7a40cc94bf8b44d09b3532b50d1",
                "roleDefinitionId": "b24988ac618042a0ab8820f7382dd24c",
                "principalId": "5418ef78e93844e98753ae55b81a65a0",
                "principalType": "ServicePrincipal"
            }
        },
        "claims": {
            "aud": "https://management.azure.com/",
            "iss": "https://sts.windows.net/70ebe3a3-5b30-435d-9d67-7716d74ca190/",
            "iat": "1612832422",
            "nbf": "1612832422",
            "exp": "1612919122",
            "aio": "E2ZgYNjLFbT/hNn2h6qSBw61Ln5zFgA=",
            "appid": "ddbf3205-c6bd-46ae-8127-60eb93363864",
            "appidacr": "2",
            "http://schemas.microsoft.com/identity/claims/identityprovider": "https://sts.windows.net/70ebe3a3-5b30-435d-9d67-7716d74ca190/",
            "http://schemas.microsoft.com/identity/claims/objectidentifier": "5418ef78-e938-44e9-8753-ae55b81a65a0",
            "rh": "0.AAAAo-PrcDBbXUOdZ3cW10yhkAUyv929xq5GgSdg65M2OGRFAAA.",
            "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/nameidentifier": "5418ef78-e938-44e9-8753-ae55b81a65a0",
            "http://schemas.microsoft.com/identity/claims/tenantid": "70ebe3a3-5b30-435d-9d67-7716d74ca190",
            "uti": "Y-3A0KDIoUmAybfVcngMAA",
            "ver": "1.0",
            "xms_tcdt": "1415644249"
        }
    },
    "level": "Warning",
    "properties": {
        "isComplianceCheck": "False",
        "resourceLocation": "northeurope",
        "ancestors": "70ebe3a3-5b30-435d-9d67-7716d74ca190",
        "policies": "[{\"policyDefinitionId\":\"/providers/Microsoft.Authorization/policyDefinitions/c3f317a7-a95c-4547-b7e7-11017ebdf2fe/\",\"policySetDefinitionId\":\"/providers/Microsoft.Authorization/policySetDefinitions/1f3afdf9-d0c9-4c3d-847f-89da613e70a8/\",\"policyDefinitionReferenceId\":\"vmssSystemUpdatesMonitoring\",\"policySetDefinitionName\":\"1f3afdf9-d0c9-4c3d-847f-89da613e70a8\",\"policyDefinitionName\":\"c3f317a7-a95c-4547-b7e7-11017ebdf2fe\",\"policyDefinitionEffect\":\"AuditIfNotExists\",\"policyAssignmentId\":\"/subscriptions/97e9b03f-04d6-4b69-b307-35f483f7ed81/providers/Microsoft.Authorization/policyAssignments/SecurityCenterBuiltIn/\",\"policyAssignmentName\":\"SecurityCenterBuiltIn\",\"policyAssignmentScope\":\"/subscriptions/97e9b03f-04d6-4b69-b307-35f483f7ed81\",\"policyAssignmentSku\":{\"name\":\"A1\",\"tier\":\"Standard\"},\"policyAssignmentParameters\":{},\"policyExemptionIds\":[]}]",
        "eventCategory": "Policy",
        "entity": "/subscriptions/97e9b03f-04d6-4b69-b307-35f483f7ed81/resourcegroups/AzureBatch-cb989d3e-4bcc-4abc-bc32-d1b6dfa2e6b0-C/providers/Microsoft.Compute/virtualMachineScaleSets/cb989d3e-4bcc-4abc-bc32-d1b6dfa2e6b0-AzureBatch-VMSS-D",
        "message": "Microsoft.Authorization/policies/audit/action",
        "hierarchy": ""
    }
}

policy_expected_output = {
    "cloud.provider": "Azure",
    "timestamp": "2021-02-09T08:45:27.3186996Z",
    "log.source": "Activity Log - Policy",
    "severity": "Warning",
    "content": json.dumps(policy_record),
    RESOURCE_ID_ATTRIBUTE: "/SUBSCRIPTIONS/97E9B03F-04D6-4B69-B307-35F483F7ED81/RESOURCEGROUPS/AZUREBATCH-CB989D3E-4BCC-4ABC-BC32-D1B6DFA2E6B0-C/PROVIDERS/MICROSOFT.COMPUTE/VIRTUALMACHINESCALESETS/CB989D3E-4BCC-4ABC-BC32-D1B6DFA2E6B0-AZUREBATCH-VMSS-D",
    SUBSCRIPTION_ATTRIBUTE: "97E9B03F-04D6-4B69-B307-35F483F7ED81",
    RESOURCE_GROUP_ATTRIBUTE: "AZUREBATCH-CB989D3E-4BCC-4ABC-BC32-D1B6DFA2E6B0-C",
    RESOURCE_TYPE_ATTRIBUTE: "MICROSOFT.COMPUTE/VIRTUALMACHINESCALESETS",
    RESOURCE_NAME_ATTRIBUTE: "CB989D3E-4BCC-4ABC-BC32-D1B6DFA2E6B0-AZUREBATCH-VMSS-D",
    "dt.source_entity": "AZURE_VM_SCALE_SET-E65F5FB7B1076140",
    "audit.action": "MICROSOFT.AUTHORIZATION/POLICIES/AUDIT/ACTION",
    "audit.result": "Succeeded"
}

resource_health_record = {
    "time": "2021-02-09T09:57:26.498Z",
    "resourceId": "/SUBSCRIPTIONS/97E9B03F-04D6-4B69-B307-35F483F7ED81/RESOURCEGROUPS/MC_DEMO-BACKEND-RG_DEMO-AKS_EASTUS/PROVIDERS/MICROSOFT.NETWORK/LOADBALANCERS/KUBERNETES",
    "correlationId": "55dc161c-c72e-4cb7-b41a-4e7e6835c076",
    "operationName": "Microsoft.Resourcehealth/healthevent/Updated/action",
    "level": "Information",
    "resultType": "Updated",
    "category": "ResourceHealth",
    "properties": {
        "eventCategory": "ResourceHealth",
        "eventProperties": {
            "title": "Unavailable",
            "details": "Some of your load balancing endpoints may be unavailable. Please see the metrics blade for availability information and troubleshooting steps for recommended solutions.",
            "currentHealthStatus": "Available",
            "previousHealthStatus": "Available",
            "type": "Downtime",
            "cause": "PlatformInitiated"
        }
    }
}

resource_health_expected_output = {
    "cloud.provider": "Azure",
    "timestamp": "2021-02-09T09:57:26.498Z",
    "log.source": "Activity Log - ResourceHealth",
    "severity": "Information",
    "content": json.dumps(resource_health_record),
    RESOURCE_ID_ATTRIBUTE: "/SUBSCRIPTIONS/97E9B03F-04D6-4B69-B307-35F483F7ED81/RESOURCEGROUPS/MC_DEMO-BACKEND-RG_DEMO-AKS_EASTUS/PROVIDERS/MICROSOFT.NETWORK/LOADBALANCERS/KUBERNETES",
    SUBSCRIPTION_ATTRIBUTE: "97E9B03F-04D6-4B69-B307-35F483F7ED81",
    RESOURCE_GROUP_ATTRIBUTE: "MC_DEMO-BACKEND-RG_DEMO-AKS_EASTUS",
    RESOURCE_TYPE_ATTRIBUTE: "MICROSOFT.NETWORK/LOADBALANCERS",
    RESOURCE_NAME_ATTRIBUTE: "KUBERNETES",
    "dt.source_entity": "AZURE_LOAD_BALANCER-0C3A32CD8FA39936",
    "audit.action": "Microsoft.Resourcehealth/healthevent/Updated/action",
    "audit.result": "Updated"
}


@pytest.fixture()
def self_monitoring():
    return SelfMonitoring(execution_time=datetime.utcnow())


def test_alert_log(self_monitoring):
    actual_output = parse_record(alert_record, self_monitoring)
    assert actual_output == alert_expected_output


def test_administrative_log(self_monitoring):
    actual_output = parse_record(administrative_record, self_monitoring)
    assert actual_output == administrative_expected_output


def test_policy_log(self_monitoring):
    actual_output = parse_record(policy_record, self_monitoring)
    assert actual_output == policy_expected_output


def test_resource_health_log(self_monitoring):
    actual_output = parse_record(resource_health_record, self_monitoring)
    assert actual_output == resource_health_expected_output

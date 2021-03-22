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

from logs_ingest.mapping import RESOURCE_ID_ATTRIBUTE, RESOURCE_TYPE_ATTRIBUTE
from logs_ingest.monitored_entity_id import create_monitored_entity_id, infer_monitored_entity_id

custom_device_id_pairs = [
    (
        "/subscriptions/69b51384-146c-4685-9dab-5ae01877d7b8/resourceGroups/testms/providers/Microsoft.Web/serverFarms/appplan",
        "CUSTOM_DEVICE-07F282A9E981851F"
    ),
    (
        "/subscriptions/97e9b03f-04d6-4b69-b307-35f483f7ed81/resourceGroups/AzureBatch-1bd9f1b9-5f53-4c25-8b8c-8cd077bc6c31-C/providers/Microsoft.Network/publicIPAddresses/azurebatch-1bd9f1b9-5f53-4c25-8b8c-8cd077bc6c31-cpublicip",
        "CUSTOM_DEVICE-10C71B284BD76E90"
    ),
    (
        "/subscriptions/a84d2d12-76ea-449c-8c1e-9fb2dee5f6b1/resourceGroups/rg-stepaw/providers/Microsoft.Network/dnszones/dns.azure.service",
        "CUSTOM_DEVICE-A66B778194B0F188"
    ),
    (
        "/subscriptions/69b51384-146c-4685-9dab-5ae01877d7b8/resourceGroups/marek-garwolinski/providers/Microsoft.Web/serverFarms/dyntracelogs-mg-test-11-plan",
        "CUSTOM_DEVICE-50421F17C3BC99B3"
    ),
    (
        "/subscriptions/69b51384-146c-4685-9dab-5ae01877d7b8/resourceGroups/testms2/providers/Microsoft.Network/frontdoors/frontdoor-alert-test",
        "CUSTOM_DEVICE-75CF30DE20E74758"
    ),
    (
        "/subscriptions/97e9b03f-04d6-4b69-b307-35f483f7ed81/resourceGroups/MC_demo-backend-rg_demo-aks_eastus/providers/Microsoft.Network/publicIPAddresses/kubernetes-a99019000145211eba495ce757676e8c",
        "CUSTOM_DEVICE-16A3F37C22A83A53"
    ),
    (
        "/subscriptions/a84d2d12-76ea-449c-8c1e-9fb2dee5f6b1/resourceGroups/rg-dadgiu/providers/Microsoft.KeyVault/vaults/kv-apm-239200",
        "CUSTOM_DEVICE-9860DE5FC97B050D"
    ),
    (
        "/subscriptions/69b51384-146c-4685-9dab-5ae01877d7b8/resourceGroups/new-resources-clients/providers/Microsoft.DBforMariaDB/servers/mariadb-test",
        "CUSTOM_DEVICE-723DA98B69CB9DA2"
    ),
]

legacy_id_triplets = [
    (
        "AZURE_SQL_SERVER",
        "/subscriptions/97e9b03f-04d6-4b69-b307-35f483f7ed81/resourceGroups/demo-backend-rg/providers/Microsoft.Sql/servers/azure-demo-sql-server",
        "AZURE_SQL_SERVER-431EDFA4E63CF989"
    ),
    (
        "AZURE_COSMOS_DB",
        "/subscriptions/97e9b03f-04d6-4b69-b307-35f483f7ed81/resourceGroups/demo-backend-rg/providers/Microsoft.DocumentDb/databaseAccounts/demo-cosmos-001",
        "AZURE_COSMOS_DB-5D586474E2D2766F"
    ),
    (
        "AZURE_REDIS_CACHE",
        "/subscriptions/97e9b03f-04d6-4b69-b307-35f483f7ed81/resourceGroups/demo-backend-rg/providers/Microsoft.Cache/Redis/demo-redis-0001",
        "AZURE_REDIS_CACHE-DFFBAFC17B5E89C3"
    ),
    (
        "AZURE_VM_SCALE_SET",
        "/subscriptions/69b51384-146c-4685-9dab-5ae01877d7b8/resourceGroups/BeluAzure2/providers/Microsoft.Compute/virtualMachineScaleSets/BeluVmScaleSet",
        "AZURE_VM_SCALE_SET-8A1207A362ED8371"
    ),
]


def test_create_custom_device_id():
    for item in custom_device_id_pairs:
        assert create_monitored_entity_id("CUSTOM_DEVICE", item[0]) == item[1]


def test_legacy_id():
    for item in legacy_id_triplets:
        assert create_monitored_entity_id(item[0], item[1]) == item[2]


def test_create_monitored_entity_id_for_default():
    record = {
        RESOURCE_ID_ATTRIBUTE: "/subscriptions/69b51384-146c-4685-9dab-5ae01877d7b8/resourceGroups/testms/providers/Microsoft.Web/serverFarms/appplan",
        RESOURCE_TYPE_ATTRIBUTE: "Microsoft.Web/serverFarms"
    }
    infer_monitored_entity_id("", record)
    assert record["dt.entity.custom_device"] == "CUSTOM_DEVICE-07F282A9E981851F"


def test_create_monitored_entity_id_for_non_custom_device():
    record = {
        RESOURCE_ID_ATTRIBUTE: "/subscriptions/97e9b03f-04d6-4b69-b307-35f483f7ed81/resourceGroups/demo-backend-rg/providers/Microsoft.Sql/servers/azure-demo-sql-server",
        RESOURCE_TYPE_ATTRIBUTE: "Microsoft.Sql/servers"
    }
    infer_monitored_entity_id("", record)
    assert "dt.entity.custom_device" not in record
    assert "dt.source_entity" in record
    assert record["dt.source_entity"] == "AZURE_SQL_SERVER-431EDFA4E63CF989"


def test_create_monitored_entity_id_for_activity_log():
    record = {
        RESOURCE_ID_ATTRIBUTE: "/SUBSCRIPTIONS/69B51384-146C-4685-9DAB-5AE01877D7B8/RESOURCEGROUPS/LOGS-INGEST-FUNCTION/PROVIDERS/MICROSOFT.EVENTHUB/NAMESPACES/LOGS-INGEST-EVENTHUB/AUTHORIZATIONRULES/ROOTMANAGESHAREDACCESSKEY",
        RESOURCE_TYPE_ATTRIBUTE: "MICROSOFT.EVENTHUB/NAMESPACES/AUTHORIZATIONRULES"
    }
    infer_monitored_entity_id("", record)
    assert "dt.entity.custom_device" not in record
    assert "dt.source_entity" in record
    assert record["dt.source_entity"] == "AZURE_EVENT_HUB_NAMESPACE-F97E6E78493D118C"


def test_not_create_monitored_entity_id():
    record = {
        RESOURCE_ID_ATTRIBUTE: "/SUBSCRIPTIONS/69B51384-146C-4685-9DAB-5AE01877D7B8/PROVIDERS/MICROSOFT.INSIGHTS/DIAGNOSTICSETTINGS/ACTIVITYLOGS-MS",
        RESOURCE_TYPE_ATTRIBUTE: "MICROSOFT.INSIGHTS/DIAGNOSTICSETTINGS"
    }
    infer_monitored_entity_id("", record)
    assert "dt.entity.custom_device" not in record
    assert "dt.source_entity" not in record
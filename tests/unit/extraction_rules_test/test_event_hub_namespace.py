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

record = {
    "Environment": "PROD",
    "Region": "East US",
    "ScaleUnit": "PROD-BL3-557",
    "ActivityId": "bf9763a1-7e65-4a43-8595-53e417c28bfb",
    "EventName": "Retreive Namespace",
    "resourceId": "/SUBSCRIPTIONS/97E9B03F-04D6-4B69-B307-35F483F7ED81/RESOURCEGROUPS/DEMO-BACKEND-RG/PROVIDERS/MICROSOFT.EVENTHUB/NAMESPACES/AZURELABS",
    "SubscriptionId": "97e9b03f-04d6-4b69-b307-35f483f7ed81",
    "EventTimeString": "2/2/2021 3:00:21 PM +00:00",
    "EventProperties": "{\"SubscriptionId\":\"97e9b03f-04d6-4b69-b307-35f483f7ed81\",\"Namespace\":\"azurelabs\",\"Via\":\"https://azurelabs.servicebus.windows.net/$Resources/eventhubs?api-version=2017-04\",\"TrackingId\":\"bf9763a1-7e65-4a43-8595-53e417c28bfb_M8CH3_M8CH3_G20\"}",
    "Status": "Succeeded",
    "Caller": "Portal",
    "category": "OperationalLogs"
}

expected_output = {
    "cloud.provider": "Azure",
    "cloud.region": "East US",
    "timestamp": "2/2/2021 3:00:21 PM +00:00",
    "log.source": "OperationalLogs",
    "content": json.dumps(record),
    RESOURCE_ID_ATTRIBUTE: "/SUBSCRIPTIONS/97E9B03F-04D6-4B69-B307-35F483F7ED81/RESOURCEGROUPS/DEMO-BACKEND-RG/PROVIDERS/MICROSOFT.EVENTHUB/NAMESPACES/AZURELABS",
    SUBSCRIPTION_ATTRIBUTE: "97E9B03F-04D6-4B69-B307-35F483F7ED81",
    RESOURCE_GROUP_ATTRIBUTE: "DEMO-BACKEND-RG",
    RESOURCE_TYPE_ATTRIBUTE: "MICROSOFT.EVENTHUB/NAMESPACES",
    RESOURCE_NAME_ATTRIBUTE: "AZURELABS",
    'dt.source_entity': 'AZURE_EVENT_HUB_NAMESPACE-273DE9D5A87802ED',
    'severity': 'Informational'
}


def test_event_hub_namespace():
    actual_output = parse_record(record, SelfMonitoring(execution_time=datetime.utcnow()))
    assert actual_output == expected_output

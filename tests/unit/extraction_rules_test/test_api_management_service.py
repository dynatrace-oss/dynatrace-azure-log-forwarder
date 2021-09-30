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
# Full schema available at https://docs.microsoft.com/pl-pl/azure/api-management/gateway-log-schema-reference
from logs_ingest.mapping import RESOURCE_NAME_ATTRIBUTE, RESOURCE_TYPE_ATTRIBUTE, RESOURCE_GROUP_ATTRIBUTE, \
    SUBSCRIPTION_ATTRIBUTE, RESOURCE_ID_ATTRIBUTE
from logs_ingest.self_monitoring import SelfMonitoring

record = {
    "Level": 4,
    "time": "2021-01-29T09:25:05.3511301Z",
    "operationName": "Microsoft.ApiManagement/GatewayLogs",
    "category": "GatewayLogs",
    "durationMs": 166,
    "callerIpAddress": "137.117.214.210",
    "correlationId": "bf0d72ed-e82f-4549-a642-223ebc40e5cc",
    "location": "West Europe",
    "properties": {
        "method": "GET",
        "url": "https://weatherapp-api-mgmt.azure-api.net/weather/current/Valparaiso",
        "backendResponseCode": 200,
        "responseCode": 200,
        "responseSize": 838,
        "cache": "none",
        "backendTime": 165,
        "requestSize": 288,
        "apiId": "testms-weather-service",
        "operationId": "5d0ca5ff56c952f6b5316199",
        "clientProtocol": "HTTP/1.1",
        "backendProtocol": "HTTP/1.1",
        "backendId": "ApiApp_testms-weather-service",
        "apiRevision": "1",
        "clientTlsVersion": "1.2",
        "backendMethod": "GET",
        "backendUrl": "https://testms-weather-service.azurewebsites.net/weather/current/Valparaiso"
    },
    "resourceId": "/SUBSCRIPTIONS/69B51384-146C-4685-9DAB-5AE01877D7B8/RESOURCEGROUPS/TESTMS/PROVIDERS/MICROSOFT.APIMANAGEMENT/SERVICE/WEATHERAPP-API-MGMT"
}

expected_output = {
    "cloud.provider": "Azure",
    "cloud.region": "West Europe",
    "timestamp": "2021-01-29T09:25:05.3511301Z",
    "log.source": "GatewayLogs",
    "severity": "Informational",
    "content": json.dumps(record),
    RESOURCE_ID_ATTRIBUTE: "/SUBSCRIPTIONS/69B51384-146C-4685-9DAB-5AE01877D7B8/RESOURCEGROUPS/TESTMS/PROVIDERS/MICROSOFT.APIMANAGEMENT/SERVICE/WEATHERAPP-API-MGMT",
    SUBSCRIPTION_ATTRIBUTE: "69B51384-146C-4685-9DAB-5AE01877D7B8",
    RESOURCE_GROUP_ATTRIBUTE: "TESTMS",
    RESOURCE_TYPE_ATTRIBUTE: "MICROSOFT.APIMANAGEMENT/SERVICE",
    RESOURCE_NAME_ATTRIBUTE: "WEATHERAPP-API-MGMT",
    'dt.source_entity': 'AZURE_API_MANAGEMENT_SERVICE-1B1340A5B6686700',
    "http.client_ip": "137.117.214.210",
    "http.flavor": "HTTP/1.1",
    "http.method": "GET",
    "http.host": "weatherapp-api-mgmt.azure-api.net",
    "http.route": "/weather/current/Valparaiso",
    "http.scheme": "https",
    "http.status_code": "200",
    "http.target": "https://weatherapp-api-mgmt.azure-api.net/weather/current/Valparaiso",
    "http.url": "https://weatherapp-api-mgmt.azure-api.net/weather/current/Valparaiso"
}


def test_api_management_service():
    actual_output = parse_record(record, SelfMonitoring(execution_time=datetime.utcnow()))
    assert actual_output == expected_output

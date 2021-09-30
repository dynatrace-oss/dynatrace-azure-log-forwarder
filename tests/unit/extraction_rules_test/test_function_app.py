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
from logs_ingest.mapping import RESOURCE_ID_ATTRIBUTE, RESOURCE_NAME_ATTRIBUTE, RESOURCE_TYPE_ATTRIBUTE, \
    RESOURCE_GROUP_ATTRIBUTE, SUBSCRIPTION_ATTRIBUTE
from logs_ingest.self_monitoring import SelfMonitoring

function_app_logs_record = {
    "resourceId": "/SUBSCRIPTIONS/69B51384-146C-4685-9DAB-5AE01877D7B8/RESOURCEGROUPS/LOGS-INGEST-FUNCTION/PROVIDERS/MICROSOFT.WEB/SITES/INGEST-LOGS-FUNCTION",
    "category": "FunctionAppLogs",
    "operationName": "Microsoft.Web/sites/functions/log",
    "level": "Informational",
    "time": "2021-02-04T07: 45: 44.5864815Z",
    "properties": {
        "message":"Executed \"Functions.logs_ingest\" (Succeeded, Id=26849b40-bba5-41ee-9521-fc3205a39b5e, Duration=50ms)",
        "hostVersion": "3.0.15277.0",
        "functionInvocationId": "26849b40-bba5-41ee-9521-fc3205a39b5e",
        "functionName": "logs_ingest",
        "level": "Information",
        "hostInstanceId": "d7e093b6-a758-43c8-b127-1349c016539e",
        "category": "Function.logs_ingest"
    },
    "EventStampType": "Stamp",
    "EventPrimaryStampName": "waws-prod-am2-369",
    "EventStampName": "waws-prod-am2-369",
    "Host": "lw1sdlwk00000V"
}

function_app_logs_expected_output = {
    "cloud.provider": "Azure",
    "timestamp": "2021-02-04T07: 45: 44.5864815Z",
    "log.source": "FunctionAppLogs",
    "severity": "Informational",
    "content": json.dumps(function_app_logs_record),
    "faas.name": "logs_ingest",
    "faas.instance": "d7e093b6-a758-43c8-b127-1349c016539e",
    "faas.version": "3.0.15277.0",
    RESOURCE_ID_ATTRIBUTE: "/SUBSCRIPTIONS/69B51384-146C-4685-9DAB-5AE01877D7B8/RESOURCEGROUPS/LOGS-INGEST-FUNCTION/PROVIDERS/MICROSOFT.WEB/SITES/INGEST-LOGS-FUNCTION",
    SUBSCRIPTION_ATTRIBUTE: "69B51384-146C-4685-9DAB-5AE01877D7B8",
    RESOURCE_GROUP_ATTRIBUTE: "LOGS-INGEST-FUNCTION",
    RESOURCE_TYPE_ATTRIBUTE: "MICROSOFT.WEB/SITES",
    RESOURCE_NAME_ATTRIBUTE: "INGEST-LOGS-FUNCTION",
    'dt.source_entity': 'AZURE_FUNCTION_APP-BBE7E69A31783E4F'
}

not_known_category_record = {
    "resourceId": "/SUBSCRIPTIONS/69B51384-146C-4685-9DAB-5AE01877D7B8/RESOURCEGROUPS/LOGS-INGEST-FUNCTION/PROVIDERS/MICROSOFT.WEB/SITES/INGEST-LOGS-FUNCTION",
    "category": "NotKnownCategory",
    "operationName": "Microsoft.Web/sites/functions/log",
    "level": "Informational",
    "time": "2021-02-04T07: 45: 44.5864815Z",
    "EventStampType": "Stamp",
    "EventPrimaryStampName": "waws-prod-am2-369",
    "EventStampName": "waws-prod-am2-369",
    "Host": "lw1sdlwk00000V"
}

not_known_category_expected_output = {
    "cloud.provider": "Azure",
    "timestamp": "2021-02-04T07: 45: 44.5864815Z",
    "log.source": "NotKnownCategory",
    "severity": "Informational",
    "content": json.dumps(not_known_category_record),
    RESOURCE_ID_ATTRIBUTE: "/SUBSCRIPTIONS/69B51384-146C-4685-9DAB-5AE01877D7B8/RESOURCEGROUPS/LOGS-INGEST-FUNCTION/PROVIDERS/MICROSOFT.WEB/SITES/INGEST-LOGS-FUNCTION",
    SUBSCRIPTION_ATTRIBUTE: "69B51384-146C-4685-9DAB-5AE01877D7B8",
    RESOURCE_GROUP_ATTRIBUTE: "LOGS-INGEST-FUNCTION",
    RESOURCE_TYPE_ATTRIBUTE: "MICROSOFT.WEB/SITES",
    RESOURCE_NAME_ATTRIBUTE: "INGEST-LOGS-FUNCTION",
    'dt.source_entity': 'AZURE_WEB_APP-BBE7E69A31783E4F'
}


def test_function_app_logs():
    actual_output = parse_record(function_app_logs_record, SelfMonitoring(execution_time=datetime.utcnow()))
    assert actual_output == function_app_logs_expected_output


def test_not_known_category():
    actual_output = parse_record(not_known_category_record, SelfMonitoring(execution_time=datetime.utcnow()))
    assert actual_output == not_known_category_expected_output

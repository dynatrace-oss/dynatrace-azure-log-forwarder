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

slow_log = {
    "LogicalServerName": "mariadb-test",
    "SubscriptionId": "69b51384-146c-4685-9dab-5ae01877d7b8",
    "ResourceGroup": "new-resources-clients",
    "time": "2021-07-19T12:07:46Z",
    "resourceId": "/SUBSCRIPTIONS/69B51384-146C-4685-9DAB-5AE01877D7B8/RESOURCEGROUPS/NEW-RESOURCES-CLIENTS/PROVIDERS/MICROSOFT.DBFORMARIADB/SERVERS/MARIADB-TEST",
    "category": "MySqlSlowLogs",
    "operationName": "LogEvent",
    "properties": {
        "event_class": "slow_log",
        "start_time": "2021-07-27T10:56:33Z",
        "query_time": 0.001,
        "lock_time": 0,
        "rows_sent": 0,
        "rows_examined": 0,
        "last_insert_id": 0,
        "insert_id": 0,
        "server_id": 1825589180,
        "thread_id": 28,
        "host": "mariadb[mariadb] @  [20.73.154.131]",
        "db": "mariadbtest",
        "sql_text": "set autocommit=1, sql_mode = concat(@@sql_mode,',STRICT_TRANS_TABLES')"
    }
}

slow_log_expected_output = {
    "cloud.provider": "Azure",
    "timestamp": "2021-07-19T12:07:46Z",
    "log.source": "MySqlSlowLogs",
    "severity": "Warning",
    "content": json.dumps(slow_log),
    RESOURCE_ID_ATTRIBUTE: "/SUBSCRIPTIONS/69B51384-146C-4685-9DAB-5AE01877D7B8/RESOURCEGROUPS/NEW-RESOURCES-CLIENTS/PROVIDERS/MICROSOFT.DBFORMARIADB/SERVERS/MARIADB-TEST",
    SUBSCRIPTION_ATTRIBUTE: "69B51384-146C-4685-9DAB-5AE01877D7B8",
    RESOURCE_GROUP_ATTRIBUTE: "NEW-RESOURCES-CLIENTS",
    RESOURCE_TYPE_ATTRIBUTE: "MICROSOFT.DBFORMARIADB/SERVERS",
    RESOURCE_NAME_ATTRIBUTE: "MARIADB-TEST",
    "db.name": "mariadbtest",
    "db.statement": "set autocommit=1, sql_mode = concat(@@sql_mode,',STRICT_TRANS_TABLES')",
    "db.user": "mariadb",
    "db.system": "mariadb",
    'dt.entity.custom_device': 'CUSTOM_DEVICE-723DA98B69CB9DA2',
    'dt.source_entity': 'CUSTOM_DEVICE-723DA98B69CB9DA2',
}

general_log = {
    "LogicalServerName": "mariadb-test",
    "SubscriptionId": "69b51384-146c-4685-9dab-5ae01877d7b8",
    "ResourceGroup": "new-resources-clients",
    "time": "2021-07-19T12:07:46Z",
    "resourceId": "/SUBSCRIPTIONS/69B51384-146C-4685-9DAB-5AE01877D7B8/RESOURCEGROUPS/NEW-RESOURCES-CLIENTS/PROVIDERS/MICROSOFT.DBFORMARIADB/SERVERS/MARIADB-TEST",
    "category": "MySqlAuditLogs",
    "operationName": "LogEvent",
    "properties": {
        "event_class": "general_log",
        "event_subclass": "RESULT",
        "event_time": "2021-07-27T11:30:33Z",
        "error_code": 0,
        "thread_id": 42,
        "host": "",
        "ip": "157.25.19.100",
        "user": "mariadb[mariadb] @  [157.25.19.100]",
        "sql_text": "SELECT * FROM mariadbtest.customer\nLIMIT 0, 1000"
    }
}

general_log_expected_output = {
    "cloud.provider": "Azure",
    "timestamp": "2021-07-19T12:07:46Z",
    "log.source": "MySqlAuditLogs - general_log",
    "severity": "Informational",
    "content": json.dumps(general_log),
    RESOURCE_ID_ATTRIBUTE: "/SUBSCRIPTIONS/69B51384-146C-4685-9DAB-5AE01877D7B8/RESOURCEGROUPS/NEW-RESOURCES-CLIENTS/PROVIDERS/MICROSOFT.DBFORMARIADB/SERVERS/MARIADB-TEST",
    SUBSCRIPTION_ATTRIBUTE: "69B51384-146C-4685-9DAB-5AE01877D7B8",
    RESOURCE_GROUP_ATTRIBUTE: "NEW-RESOURCES-CLIENTS",
    RESOURCE_TYPE_ATTRIBUTE: "MICROSOFT.DBFORMARIADB/SERVERS",
    RESOURCE_NAME_ATTRIBUTE: "MARIADB-TEST",
    "db.statement": "SELECT * FROM mariadbtest.customer\nLIMIT 0, 1000",
    "db.user": "mariadb",
    "db.system": "mariadb",
    'dt.entity.custom_device': 'CUSTOM_DEVICE-723DA98B69CB9DA2',
    'dt.source_entity': 'CUSTOM_DEVICE-723DA98B69CB9DA2'
}

connection_log_record = {
    "LogicalServerName": "mariadb-test",
    "SubscriptionId": "69b51384-146c-4685-9dab-5ae01877d7b8",
    "ResourceGroup": "new-resources-clients",
    "time": "2021-07-19T12:07:46Z",
    "resourceId": "/SUBSCRIPTIONS/69B51384-146C-4685-9DAB-5AE01877D7B8/RESOURCEGROUPS/NEW-RESOURCES-CLIENTS/PROVIDERS/MICROSOFT.DBFORMARIADB/SERVERS/MARIADB-TEST",
    "category": "MySqlAuditLogs",
    "operationName": "LogEvent",
    "properties": {
        "event_class": "connection_log",
        "event_subclass": "CONNECT",
        "connection_id": 36,
        "host": "",
        "ip": "20.73.154.131",
        "user": "mariadb",
        "db": "mariadbtest"
    }
}

connection_log_expected_output = {
    "cloud.provider": "Azure",
    "timestamp": "2021-07-19T12:07:46Z",
    "log.source": "MySqlAuditLogs - connection_log",
    "severity": "Informational",
    "content": json.dumps(connection_log_record),
    RESOURCE_ID_ATTRIBUTE: "/SUBSCRIPTIONS/69B51384-146C-4685-9DAB-5AE01877D7B8/RESOURCEGROUPS/NEW-RESOURCES-CLIENTS/PROVIDERS/MICROSOFT.DBFORMARIADB/SERVERS/MARIADB-TEST",
    SUBSCRIPTION_ATTRIBUTE: "69B51384-146C-4685-9DAB-5AE01877D7B8",
    RESOURCE_GROUP_ATTRIBUTE: "NEW-RESOURCES-CLIENTS",
    RESOURCE_TYPE_ATTRIBUTE: "MICROSOFT.DBFORMARIADB/SERVERS",
    RESOURCE_NAME_ATTRIBUTE: "MARIADB-TEST",
    "db.name": "mariadbtest",
    "db.user": "mariadb",
    "db.system": "mariadb",
    'dt.entity.custom_device': 'CUSTOM_DEVICE-723DA98B69CB9DA2',
    'dt.source_entity': 'CUSTOM_DEVICE-723DA98B69CB9DA2'
}


@pytest.fixture()
def self_monitoring():
    return SelfMonitoring(execution_time=datetime.utcnow())


def test_slow_log(self_monitoring):
    actual_output = parse_record(slow_log, self_monitoring)
    assert actual_output == slow_log_expected_output


def test_general_log(self_monitoring):
    actual_output = parse_record(general_log, self_monitoring)
    assert actual_output == general_log_expected_output


def test_connection_log(self_monitoring):
    actual_output = parse_record(connection_log_record, self_monitoring)
    assert actual_output == connection_log_expected_output

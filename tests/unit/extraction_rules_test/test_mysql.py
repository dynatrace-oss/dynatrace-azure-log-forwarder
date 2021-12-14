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
  "LogicalServerName": "mysql-custom",
  "SubscriptionId": "69b51384-146c-4685-9dab-5ae01877d7b8",
  "ResourceGroup": "new-resources-clients",
  "time": "2021-07-19T12:07:46Z",
  "resourceId": "/SUBSCRIPTIONS/69B51384-146C-4685-9DAB-5AE01877D7B8/RESOURCEGROUPS/NEW-RESOURCES-CLIENTS/PROVIDERS/MICROSOFT.DBFORMYSQL/SERVERS/MYSQL-CUSTOM",
  "category": "MySqlSlowLogs",
  "operationName": "LogEvent",
  "properties": {
    "event_class": "slow_log",
    "start_time": "2021-07-19T12:07:46Z",
    "query_time": 9.188,
    "lock_time": 0,
    "rows_sent": 62,
    "rows_examined": 2343249,
    "last_insert_id": 0,
    "insert_id": 0,
    "server_id": 3257147488,
    "thread_id": 39410,
    "host": "mysql[mysql] @  [40.91.226.68]",
    "db": "mysqltestdb",
    "sql_text": "select location0_.name as col_0_0_ from location location0_ where exists (select journey1_.id from journey journey1_ where journey1_.destination_name=location0_.name)"
  }
}

slow_log_expected_output = {
    "cloud.provider": "Azure",
    "timestamp": "2021-07-19T12:07:46Z",
    "log.source": "MySqlSlowLogs",
    "severity": "Warning",
    "content": json.dumps(slow_log),
    RESOURCE_ID_ATTRIBUTE: "/SUBSCRIPTIONS/69B51384-146C-4685-9DAB-5AE01877D7B8/RESOURCEGROUPS/NEW-RESOURCES-CLIENTS/PROVIDERS/MICROSOFT.DBFORMYSQL/SERVERS/MYSQL-CUSTOM",
    SUBSCRIPTION_ATTRIBUTE: "69B51384-146C-4685-9DAB-5AE01877D7B8",
    RESOURCE_GROUP_ATTRIBUTE: "NEW-RESOURCES-CLIENTS",
    RESOURCE_TYPE_ATTRIBUTE: "MICROSOFT.DBFORMYSQL/SERVERS",
    RESOURCE_NAME_ATTRIBUTE: "MYSQL-CUSTOM",
    "db.name": "mysqltestdb",
    "db.statement": "select location0_.name as col_0_0_ from location location0_ where exists (select journey1_.id from journey journey1_ where journey1_.destination_name=location0_.name)",
    "db.user": "mysql",
    "db.system": "mysql",
    'dt.entity.custom_device': 'CUSTOM_DEVICE-E17B017C6CFB4EF9',
    'dt.source_entity': 'CUSTOM_DEVICE-E17B017C6CFB4EF9',
}

general_log = {
  "LogicalServerName": "mysql-custom",
  "SubscriptionId": "69b51384-146c-4685-9dab-5ae01877d7b8",
  "ResourceGroup": "new-resources-clients",
  "time": "2021-07-19T08:19:27Z",
  "resourceId": "/SUBSCRIPTIONS/69B51384-146C-4685-9DAB-5AE01877D7B8/RESOURCEGROUPS/NEW-RESOURCES-CLIENTS/PROVIDERS/MICROSOFT.DBFORMYSQL/SERVERS/MYSQL-CUSTOM",
  "category": "MySqlAuditLogs",
  "operationName": "LogEvent",
  "properties": {
    "event_class": "general_log",
    "event_subclass": "LOG",
    "event_time": "2021-07-19T08:19:27Z",
    "error_code": 0,
    "thread_id": 37110,
    "host": "",
    "ip": "40.91.226.68",
    "user": "mysql[mysql] @  [40.91.226.68]",
    "sql_text": "select count(*) as col_0_0_ from customer customer0_"
  }
}

general_log_expected_output = {
    "cloud.provider": "Azure",
    "timestamp": "2021-07-19T08:19:27Z",
    "log.source": "MySqlAuditLogs - general_log",
    "severity": "Informational",
    "content": json.dumps(general_log),
    RESOURCE_ID_ATTRIBUTE: "/SUBSCRIPTIONS/69B51384-146C-4685-9DAB-5AE01877D7B8/RESOURCEGROUPS/NEW-RESOURCES-CLIENTS/PROVIDERS/MICROSOFT.DBFORMYSQL/SERVERS/MYSQL-CUSTOM",
    SUBSCRIPTION_ATTRIBUTE: "69B51384-146C-4685-9DAB-5AE01877D7B8",
    RESOURCE_GROUP_ATTRIBUTE: "NEW-RESOURCES-CLIENTS",
    RESOURCE_TYPE_ATTRIBUTE: "MICROSOFT.DBFORMYSQL/SERVERS",
    RESOURCE_NAME_ATTRIBUTE: "MYSQL-CUSTOM",
    "db.statement": "select count(*) as col_0_0_ from customer customer0_",
    "db.user": "mysql",
    "db.system": "mysql",
    'dt.entity.custom_device': 'CUSTOM_DEVICE-E17B017C6CFB4EF9',
    'dt.source_entity': 'CUSTOM_DEVICE-E17B017C6CFB4EF9'
}

table_access_log = {
  "LogicalServerName": "mysql-custom",
  "SubscriptionId": "69b51384-146c-4685-9dab-5ae01877d7b8",
  "ResourceGroup": "new-resources-clients",
  "time": "2021-07-19T08:19:35Z",
  "resourceId": "/SUBSCRIPTIONS/69B51384-146C-4685-9DAB-5AE01877D7B8/RESOURCEGROUPS/NEW-RESOURCES-CLIENTS/PROVIDERS/MICROSOFT.DBFORMYSQL/SERVERS/MYSQL-CUSTOM",
  "category": "MySqlAuditLogs",
  "operationName": "LogEvent",
  "properties": {
    "event_class": "table_access_log",
    "event_subclass": "READ",
    "connection_id": 37074,
    "db": "mysqltestdb",
    "table": "customer",
    "sql_text": "select count(*) as col_0_0_ from customer customer0_"
  }
}

table_access_log_expected_output = {
    "cloud.provider": "Azure",
    "timestamp": "2021-07-19T08:19:35Z",
    "log.source": "MySqlAuditLogs - table_access_log",
    "severity": "Informational",
    "content": json.dumps(table_access_log),
    RESOURCE_ID_ATTRIBUTE: "/SUBSCRIPTIONS/69B51384-146C-4685-9DAB-5AE01877D7B8/RESOURCEGROUPS/NEW-RESOURCES-CLIENTS/PROVIDERS/MICROSOFT.DBFORMYSQL/SERVERS/MYSQL-CUSTOM",
    SUBSCRIPTION_ATTRIBUTE: "69B51384-146C-4685-9DAB-5AE01877D7B8",
    RESOURCE_GROUP_ATTRIBUTE: "NEW-RESOURCES-CLIENTS",
    RESOURCE_TYPE_ATTRIBUTE: "MICROSOFT.DBFORMYSQL/SERVERS",
    RESOURCE_NAME_ATTRIBUTE: "MYSQL-CUSTOM",
    "db.name": "mysqltestdb",
    "db.statement": "select count(*) as col_0_0_ from customer customer0_",
    "db.operation": "READ",
    "db.system": "mysql",
    'dt.entity.custom_device': 'CUSTOM_DEVICE-E17B017C6CFB4EF9',
    'dt.source_entity': 'CUSTOM_DEVICE-E17B017C6CFB4EF9'
}

connection_log_record = {
  "LogicalServerName": "mysql-custom",
  "SubscriptionId": "69b51384-146c-4685-9dab-5ae01877d7b8",
  "ResourceGroup": "new-resources-clients",
  "time": "2021-07-19T08:19:32Z",
  "resourceId": "/SUBSCRIPTIONS/69B51384-146C-4685-9DAB-5AE01877D7B8/RESOURCEGROUPS/NEW-RESOURCES-CLIENTS/PROVIDERS/MICROSOFT.DBFORMYSQL/FLEXIBLESERVERS/MYSQL-CUSTOM",
  "category": "MySqlAuditLogs",
  "operationName": "LogEvent",
  "properties": {
    "event_class": "connection_log",
    "event_subclass": "CONNECT",
    "connection_id": 37115,
    "host": "",
    "ip": "40.91.226.68",
    "user": "mysql",
    "db": "mysqltestdb"
  }
}

connection_log_expected_output = {
    "cloud.provider": "Azure",
    "timestamp": "2021-07-19T08:19:32Z",
    "log.source": "MySqlAuditLogs - connection_log",
    "severity": "Informational",
    "content": json.dumps(connection_log_record),
    RESOURCE_ID_ATTRIBUTE: "/SUBSCRIPTIONS/69B51384-146C-4685-9DAB-5AE01877D7B8/RESOURCEGROUPS/NEW-RESOURCES-CLIENTS/PROVIDERS/MICROSOFT.DBFORMYSQL/FLEXIBLESERVERS/MYSQL-CUSTOM",
    SUBSCRIPTION_ATTRIBUTE: "69B51384-146C-4685-9DAB-5AE01877D7B8",
    RESOURCE_GROUP_ATTRIBUTE: "NEW-RESOURCES-CLIENTS",
    RESOURCE_TYPE_ATTRIBUTE: "MICROSOFT.DBFORMYSQL/FLEXIBLESERVERS",
    RESOURCE_NAME_ATTRIBUTE: "MYSQL-CUSTOM",
    "db.name": "mysqltestdb",
    "db.user": "mysql",
    "db.system": "mysql"
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


def test_table_access_log(self_monitoring):
    actual_output = parse_record(table_access_log, self_monitoring)
    assert actual_output == table_access_log_expected_output


def test_connection_log(self_monitoring):
    actual_output = parse_record(connection_log_record, self_monitoring)
    assert actual_output == connection_log_expected_output

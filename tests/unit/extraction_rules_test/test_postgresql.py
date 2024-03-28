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

postgresql_log = {
  "LogicalServerName": "postgresql-logs",
  "SubscriptionId": "69b51384-146c-4685-9dab-5ae01877d7b8",
  "ResourceGroup": "rg-ms-logs",
  "time": "2021-08-05T05:51:47Z",
  "resourceId": "/SUBSCRIPTIONS/69B51384-146C-4685-9DAB-5AE01877D7B8/RESOURCEGROUPS/RG-MS-LOGS/PROVIDERS/MICROSOFT.DBFORPOSTGRESQL/SERVERS/POSTGRESQL-LOGS",
  "category": "PostgreSQLLogs",
  "operationName": "LogEvent",
  "properties": {
    "prefix": "2021-08-05 05:51:47 UTC-610b6e2b.faec-",
    "message": "execute <unnamed>: set session statement_timeout to 90000",
    "detail": "",
    "errorLevel": "NOTICE",
    "domain": "postgres-11",
    "schemaName": "",
    "tableName": "",
    "columnName": "",
    "datatypeName": ""
  }
}

postgresql_log_expected_output = {
    "cloud.provider": "Azure",
    "timestamp": "2021-08-05T05:51:47Z",
    "log.source": "PostgreSQLLogs",
    "severity": "Notice",
    "content": json.dumps(postgresql_log),
    RESOURCE_ID_ATTRIBUTE: "/SUBSCRIPTIONS/69B51384-146C-4685-9DAB-5AE01877D7B8/RESOURCEGROUPS/RG-MS-LOGS/PROVIDERS/MICROSOFT.DBFORPOSTGRESQL/SERVERS/POSTGRESQL-LOGS",
    SUBSCRIPTION_ATTRIBUTE: "69B51384-146C-4685-9DAB-5AE01877D7B8",
    RESOURCE_GROUP_ATTRIBUTE: "RG-MS-LOGS",
    RESOURCE_TYPE_ATTRIBUTE: "MICROSOFT.DBFORPOSTGRESQL/SERVERS",
    RESOURCE_NAME_ATTRIBUTE: "POSTGRESQL-LOGS",
    "db.system": "postgresql",
    'dt.entity.custom_device': 'CUSTOM_DEVICE-837D1B039FD2DC6A',
    'dt.source_entity': 'CUSTOM_DEVICE-837D1B039FD2DC6A',
}

query_store_runtime_statistics_log = {
  "LogicalServerName": "postgresql-logs",
  "SubscriptionId": "69b51384-146c-4685-9dab-5ae01877d7b8",
  "ResourceGroup": "rg-ms-logs",
  "time": "2021-08-05T05:36:34.1217269Z",
  "resourceId": "/SUBSCRIPTIONS/69B51384-146C-4685-9DAB-5AE01877D7B8/RESOURCEGROUPS/RG-MS-LOGS/PROVIDERS/MICROSOFT.DBFORPOSTGRESQL/SERVERS/POSTGRESQL-LOGS",
  "category": "QueryStoreRuntimeStatistics",
  "operationName": "QueryStoreRuntimeStatisticsEvent",
  "properties": {
    "runtime_stats_entry_id": "2226",
    "user_id": "10",
    "db_id": "16384",
    "query_id": "1200766644",
    "start_time": "8/5/2021 4:28:48 AM",
    "end_time": "8/5/2021 4:43:48 AM",
    "calls": "1",
    "total_time": "76.7720793624988",
    "min_time": "76.7720793624988",
    "max_time": "76.7720793624988",
    "mean_time": "76.7720793624988",
    "stddev_time": "0",
    "rows": "99",
    "shared_blks_hit": "679",
    "shared_blks_read": "0",
    "shared_blks_dirtied": "10",
    "shared_blks_written": "0",
    "local_blks_hit": "0",
    "local_blks_read": "0",
    "local_blks_dirtied": "0",
    "local_blks_written": "0",
    "temp_blks_read": "199",
    "temp_blks_written": "200",
    "blk_read_time": "0",
    "blk_write_time": "0"
  }
}

query_store_runtime_statistics_log_expected_output = {
    "cloud.provider": "Azure",
    "timestamp": "2021-08-05T05:36:34.1217269Z",
    "log.source": "QueryStoreRuntimeStatistics",
    "content": json.dumps(query_store_runtime_statistics_log),
    RESOURCE_ID_ATTRIBUTE: "/SUBSCRIPTIONS/69B51384-146C-4685-9DAB-5AE01877D7B8/RESOURCEGROUPS/RG-MS-LOGS/PROVIDERS/MICROSOFT.DBFORPOSTGRESQL/SERVERS/POSTGRESQL-LOGS",
    SUBSCRIPTION_ATTRIBUTE: "69B51384-146C-4685-9DAB-5AE01877D7B8",
    RESOURCE_GROUP_ATTRIBUTE: "RG-MS-LOGS",
    RESOURCE_TYPE_ATTRIBUTE: "MICROSOFT.DBFORPOSTGRESQL/SERVERS",
    RESOURCE_NAME_ATTRIBUTE: "POSTGRESQL-LOGS",
    "db.system": "postgresql",
    'dt.entity.custom_device': 'CUSTOM_DEVICE-837D1B039FD2DC6A',
    'dt.source_entity': 'CUSTOM_DEVICE-837D1B039FD2DC6A',
    'severity': 'Informational'
}

query_store_wait_statistics_log = {
  "LogicalServerName": "postgresql-logs",
  "SubscriptionId": "69b51384-146c-4685-9dab-5ae01877d7b8",
  "ResourceGroup": "rg-ms-logs",
  "time": "2021-08-05T04:35:38.4516985Z",
  "resourceId": "/SUBSCRIPTIONS/69B51384-146C-4685-9DAB-5AE01877D7B8/RESOURCEGROUPS/RG-MS-LOGS/PROVIDERS/MICROSOFT.DBFORPOSTGRESQL/SERVERS/POSTGRESQL-LOGS",
  "category": "QueryStoreWaitStatistics",
  "operationName": "QueryStoreWaitEvent",
  "properties": {
    "start_time": "8/5/2021 3:43:48 AM",
    "end_time": "8/5/2021 3:58:48 AM",
    "user_id": "0",
    "db_id": "0",
    "query_id": "0",
    "event_type": "Activity",
    "event": "CheckpointerMain",
    "calls": "8101"
  }
}

query_store_wait_statistics_log_expected_output = {
    "cloud.provider": "Azure",
    "timestamp": "2021-08-05T04:35:38.4516985Z",
    "log.source": "QueryStoreWaitStatistics",
    "content": json.dumps(query_store_wait_statistics_log),
    RESOURCE_ID_ATTRIBUTE: "/SUBSCRIPTIONS/69B51384-146C-4685-9DAB-5AE01877D7B8/RESOURCEGROUPS/RG-MS-LOGS/PROVIDERS/MICROSOFT.DBFORPOSTGRESQL/SERVERS/POSTGRESQL-LOGS",
    SUBSCRIPTION_ATTRIBUTE: "69B51384-146C-4685-9DAB-5AE01877D7B8",
    RESOURCE_GROUP_ATTRIBUTE: "RG-MS-LOGS",
    RESOURCE_TYPE_ATTRIBUTE: "MICROSOFT.DBFORPOSTGRESQL/SERVERS",
    RESOURCE_NAME_ATTRIBUTE: "POSTGRESQL-LOGS",
    "db.system": "postgresql",
    'dt.entity.custom_device': 'CUSTOM_DEVICE-837D1B039FD2DC6A',
    'dt.source_entity': 'CUSTOM_DEVICE-837D1B039FD2DC6A',
    'severity': 'Informational'
}


@pytest.fixture()
def self_monitoring():
    return SelfMonitoring(execution_time=datetime.utcnow())


def test_postgresql_log(self_monitoring):
    actual_output = parse_record(postgresql_log, self_monitoring)
    assert actual_output == postgresql_log_expected_output


def test_query_store_runtime_statistics_log(self_monitoring):
    actual_output = parse_record(query_store_runtime_statistics_log, self_monitoring)
    assert actual_output == query_store_runtime_statistics_log_expected_output


def test_store_wait_statistics_access_log(self_monitoring):
    actual_output = parse_record(query_store_wait_statistics_log, self_monitoring)
    assert actual_output == query_store_wait_statistics_log_expected_output
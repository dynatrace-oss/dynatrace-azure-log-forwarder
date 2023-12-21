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


query_store_runtime_statistics_log = {
  "LogicalServerName": "mssql-managed-logs-test",
  "SubscriptionId": "69b51384-146c-4685-9dab-5ae01877d7b8",
  "ResourceGroup": "test-dk",
  "time": "2021-08-12T07:26:32.4015726Z",
  "resourceId": "/SUBSCRIPTIONS/69B51384-146C-4685-9DAB-5AE01877D7B8/RESOURCEGROUPS/TEST-DK/PROVIDERS/MICROSOFT.SQL/MANAGEDINSTANCES/MSSQL-MANAGED-LOGS-TEST/DATABASES/MSSQL-DATABASE",
  "category": "QueryStoreRuntimeStatistics",
  "operationName": "QueryStoreRuntimeStatisticsEvent",
  "properties": {
    "ElasticPoolName": "",
    "DatabaseName": "mssql-database",
    "interval_start_time": 190833994455872,
    "interval_end_time": 190833995535872,
    "logical_io_writes": 0,
    "max_logical_io_writes": 0,
    "physical_io_reads": 0,
    "max_physical_io_reads": 0,
    "logical_io_reads": 4,
    "max_logical_io_reads": 2,
    "execution_type": 0,
    "count_executions": 2,
    "cpu_time": 153,
    "max_cpu_time": 84,
    "dop": 2,
    "max_dop": 1,
    "rowcount": 6,
    "max_rowcount": 3,
    "query_max_used_memory": 0,
    "max_query_max_used_memory": 0,
    "duration": 153,
    "max_duration": 84,
    "num_physical_io_reads": 0,
    "max_num_physical_io_reads": 0,
    "log_bytes_used": 0,
    "max_log_bytes_used": 0,
    "query_id": 29,
    "query_hash": "0x64F8468CA9364122",
    "plan_id": 3,
    "query_plan_hash": "0xDEFFB1C27DCFA57F",
    "statement_sql_handle": "0x0900CDF04BEC72B3D951E471993706C5B0260000000000000000000000000000000000000000000000000000"
  }
}


query_store_runtime_statistics_log_expected_output = {
    "cloud.provider": "Azure",
    "timestamp": "2021-08-12T07:26:32.4015726Z",
    "log.source": "QueryStoreRuntimeStatistics",
    "severity": "Informational",
    "content": json.dumps(query_store_runtime_statistics_log),
    RESOURCE_ID_ATTRIBUTE: "/SUBSCRIPTIONS/69B51384-146C-4685-9DAB-5AE01877D7B8/RESOURCEGROUPS/TEST-DK/PROVIDERS/MICROSOFT.SQL/MANAGEDINSTANCES/MSSQL-MANAGED-LOGS-TEST/DATABASES/MSSQL-DATABASE",
    SUBSCRIPTION_ATTRIBUTE: "69B51384-146C-4685-9DAB-5AE01877D7B8",
    RESOURCE_GROUP_ATTRIBUTE: "TEST-DK",
    RESOURCE_TYPE_ATTRIBUTE: "MICROSOFT.SQL/MANAGEDINSTANCES/DATABASES",
    RESOURCE_NAME_ATTRIBUTE: "MSSQL-DATABASE",
    "db.system": "mssql",
    "db.name": "mssql-database",
    "dt.entity.custom_device": "CUSTOM_DEVICE-0F706DFF6F100685",
    "dt.source_entity": "CUSTOM_DEVICE-0F706DFF6F100685"
}


errors_log = {
  "LogicalServerName": "mssql-managed-logs-test",
  "SubscriptionId": "69b51384-146c-4685-9dab-5ae01877d7b8",
  "ResourceGroup": "test-dk",
  "time": "2021-08-12T07:26:32.4015726Z",
  "resourceId": "/SUBSCRIPTIONS/69B51384-146C-4685-9DAB-5AE01877D7B8/RESOURCEGROUPS/TEST-DK/PROVIDERS/MICROSOFT.SQL/MANAGEDINSTANCES/MSSQL-MANAGED-LOGS-TEST/DATABASES/MSSQL-DATABASE",
  "category": "Errors",
  "operationName": "ErrorEvent",
  "properties": {
    "ElasticPoolName": "",
    "DatabaseName": "mssql-database",
    "query_hash": "0",
    "query_plan_hash": "0",
    "message": "Column name or number of supplied values does not match table definition.",
    "error_number": 213,
    "severity": 16,
    "user_defined": False,
    "state": 1
  }
}

errors_log_expected_output = {
    "cloud.provider": "Azure",
    "timestamp": "2021-08-12T07:26:32.4015726Z",
    "log.source": "Errors",
    "severity": "ERROR",
    "content": json.dumps(errors_log),
    RESOURCE_ID_ATTRIBUTE: "/SUBSCRIPTIONS/69B51384-146C-4685-9DAB-5AE01877D7B8/RESOURCEGROUPS/TEST-DK/PROVIDERS/MICROSOFT.SQL/MANAGEDINSTANCES/MSSQL-MANAGED-LOGS-TEST/DATABASES/MSSQL-DATABASE",
    SUBSCRIPTION_ATTRIBUTE: "69B51384-146C-4685-9DAB-5AE01877D7B8",
    RESOURCE_GROUP_ATTRIBUTE: "TEST-DK",
    RESOURCE_TYPE_ATTRIBUTE: "MICROSOFT.SQL/MANAGEDINSTANCES/DATABASES",
    RESOURCE_NAME_ATTRIBUTE: "MSSQL-DATABASE",
    "db.system": "mssql",
    "db.name": "mssql-database",
    "dt.entity.custom_device": "CUSTOM_DEVICE-0F706DFF6F100685",
    "dt.source_entity": "CUSTOM_DEVICE-0F706DFF6F100685"
}


database_wait_statistics_log = {
  "LogicalServerName": "mssql-managed-logs-test",
  "SubscriptionId": "69b51384-146c-4685-9dab-5ae01877d7b8",
  "ResourceGroup": "test-dk",
  "time": "2021-08-12T07:26:32.4015726Z",
  "resourceId": "/SUBSCRIPTIONS/69B51384-146C-4685-9DAB-5AE01877D7B8/RESOURCEGROUPS/TEST-DK/PROVIDERS/MICROSOFT.SQL/MANAGEDINSTANCES/MSSQL-MANAGED-LOGS-TEST/DATABASES/MSSQL-DATABASE",
  "category": "QueryStoreWaitStatistics",
  "operationName": "QueryStoreWaitStatisticsEvent",
  "properties": {
    "ElasticPoolName": "",
    "DatabaseName": "mssql-database",
    "interval_start_time": 190829707048576,
    "interval_end_time": 190829708128576,
    "exec_type": 0,
    "wait_category": "NETWORKIO",
    "count_executions": 1.0,
    "total_query_wait_time_ms": 27,
    "max_query_wait_time_ms": 27,
    "is_parameterizable": "false",
    "statement_type": "x_estypSelect",
    "query_id": 28,
    "statement_key_hash": "1938133272",
    "plan_id": 1,
    "query_param_type": 1,
    "query_hash": "0xE2D481769B70E309",
    "query_plan_hash": "0xF98B361CAF20A317",
    "statement_sql_handle": "0x0900D261C85875D4EF3C90BD18D02D6245380000000000000000000000000000000000000000000000000000"
  }
}

database_wait_statistics_log_expected_output = {
    "cloud.provider": "Azure",
    "timestamp": "2021-08-12T07:26:32.4015726Z",
    "log.source": "QueryStoreWaitStatistics",
    "severity": "Informational",
    "content": json.dumps(database_wait_statistics_log),
    RESOURCE_ID_ATTRIBUTE: "/SUBSCRIPTIONS/69B51384-146C-4685-9DAB-5AE01877D7B8/RESOURCEGROUPS/TEST-DK/PROVIDERS/MICROSOFT.SQL/MANAGEDINSTANCES/MSSQL-MANAGED-LOGS-TEST/DATABASES/MSSQL-DATABASE",
    SUBSCRIPTION_ATTRIBUTE: "69B51384-146C-4685-9DAB-5AE01877D7B8",
    RESOURCE_GROUP_ATTRIBUTE: "TEST-DK",
    RESOURCE_TYPE_ATTRIBUTE: "MICROSOFT.SQL/MANAGEDINSTANCES/DATABASES",
    RESOURCE_NAME_ATTRIBUTE: "MSSQL-DATABASE",
    "db.system": "mssql",
    "db.name": "mssql-database",
    'dt.entity.custom_device': 'CUSTOM_DEVICE-0F706DFF6F100685',
    'dt.source_entity': 'CUSTOM_DEVICE-0F706DFF6F100685',
}


resource_usage_stats_log = {
  "LogicalServerName": "mssql-managed-logs-test",
  "SubscriptionId": "69b51384-146c-4685-9dab-5ae01877d7b8",
  "ResourceGroup": "test-dk",
  "time": "2021-08-12T07:26:32.4015726Z",
  "resourceId": "/SUBSCRIPTIONS/69B51384-146C-4685-9DAB-5AE01877D7B8/RESOURCEGROUPS/TEST-DK/PROVIDERS/MICROSOFT.SQL/MANAGEDINSTANCES/MSSQL-MANAGED-LOGS-TEST",
  "category": "ResourceUsageStats",
  "operationName": "ResourceUsageStatsEvent",
  "properties": {
    "SKU": "GeneralPurpose",
    "virtual_core_count": "4",
    "avg_cpu_percent": "0.052500",
    "reserved_storage_mb": "32768",
    "storage_space_used_mb": "312.000000",
    "io_requests": "6",
    "io_bytes_read": "0",
    "io_bytes_written": "34304"
  }
}

resource_usage_stats_log_expected_output = {
    "cloud.provider": "Azure",
    "timestamp": "2021-08-12T07:26:32.4015726Z",
    "log.source": "ResourceUsageStats",
    "severity": "Informational",
    "content": json.dumps(resource_usage_stats_log),
    RESOURCE_ID_ATTRIBUTE: "/SUBSCRIPTIONS/69B51384-146C-4685-9DAB-5AE01877D7B8/RESOURCEGROUPS/TEST-DK/PROVIDERS/MICROSOFT.SQL/MANAGEDINSTANCES/MSSQL-MANAGED-LOGS-TEST",
    SUBSCRIPTION_ATTRIBUTE: "69B51384-146C-4685-9DAB-5AE01877D7B8",
    RESOURCE_GROUP_ATTRIBUTE: "TEST-DK",
    RESOURCE_TYPE_ATTRIBUTE: "MICROSOFT.SQL/MANAGEDINSTANCES",
    RESOURCE_NAME_ATTRIBUTE: "MSSQL-MANAGED-LOGS-TEST",
    "db.system": "mssql",
    "dt.entity.custom_device": "CUSTOM_DEVICE-0F706DFF6F100685",
    "dt.source_entity": "CUSTOM_DEVICE-0F706DFF6F100685"
}


@pytest.fixture()
def self_monitoring():
    return SelfMonitoring(execution_time=datetime.utcnow())


def test_query_store_runtime_statistics_log(self_monitoring):
    actual_output = parse_record(query_store_runtime_statistics_log, self_monitoring)
    assert actual_output == query_store_runtime_statistics_log_expected_output


def test_errors_log(self_monitoring):
    actual_output = parse_record(errors_log, self_monitoring)
    assert actual_output == errors_log_expected_output


def test_database_wait_statistics_log(self_monitoring):
    actual_output = parse_record(database_wait_statistics_log, self_monitoring)
    assert actual_output == database_wait_statistics_log_expected_output


def test_resource_usage_stats_log(self_monitoring):
    actual_output = parse_record(resource_usage_stats_log, self_monitoring)
    assert actual_output == resource_usage_stats_log_expected_output



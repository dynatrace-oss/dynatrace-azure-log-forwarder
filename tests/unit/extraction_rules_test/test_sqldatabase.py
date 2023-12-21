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

automatic_tuning_log = {
  "LogicalServerName": "test-dk-sql-server",
  "SubscriptionId": "69b51384-146c-4685-9dab-5ae01877d7b8",
  "ResourceGroup": "test-dk",
  "time": "2021-08-12T07:26:32.4015726Z",
  "resourceId": "/SUBSCRIPTIONS/69B51384-146C-4685-9DAB-5AE01877D7B8/RESOURCEGROUPS/TEST-DK/PROVIDERS/MICROSOFT.SQL/SERVERS/TEST-DK-SQL-SERVER/DATABASES/MSSQL-LOG-TEST",
  "category": "AutomaticTuning",
  "operationName": "AutomaticTuningSettingsSnapshotEvent",
  "properties": {
    "DatabaseName": "mssql-log-test",
    "OptionName": "FORCE_LAST_GOOD_PLAN",
    "OptionDesiredState": "Default",
    "OptionActualState": "On",
    "OptionDisableReason": "Inherited from server",
    "IsDisabledBySystem": 0,
    "DatabaseDesiredMode": "Inherit",
    "DatabaseActualMode": "Auto"
  }
}

automatic_tuning_log_expected_output = {
    "cloud.provider": "Azure",
    "timestamp": "2021-08-12T07:26:32.4015726Z",
    "log.source": "AutomaticTuning",
    "severity": "Informational",
    "content": json.dumps(automatic_tuning_log),
    RESOURCE_ID_ATTRIBUTE: "/SUBSCRIPTIONS/69B51384-146C-4685-9DAB-5AE01877D7B8/RESOURCEGROUPS/TEST-DK/PROVIDERS/MICROSOFT.SQL/SERVERS/TEST-DK-SQL-SERVER/DATABASES/MSSQL-LOG-TEST",
    SUBSCRIPTION_ATTRIBUTE: "69B51384-146C-4685-9DAB-5AE01877D7B8",
    RESOURCE_GROUP_ATTRIBUTE: "TEST-DK",
    RESOURCE_TYPE_ATTRIBUTE: "MICROSOFT.SQL/SERVERS/DATABASES",
    RESOURCE_NAME_ATTRIBUTE: "MSSQL-LOG-TEST",
    "db.system": "mssql",
    "db.name": "mssql-log-test",
    'dt.source_entity': 'AZURE_SQL_DATABASE-AE715D5D0538D957',
}


query_store_runtime_statistics_log = {
  "LogicalServerName": "test-dk-sql-server",
  "SubscriptionId": "69b51384-146c-4685-9dab-5ae01877d7b8",
  "ResourceGroup": "test-dk",
  "time": "2021-08-12T07:26:32.4015726Z",
  "resourceId": "/SUBSCRIPTIONS/69B51384-146C-4685-9DAB-5AE01877D7B8/RESOURCEGROUPS/TEST-DK/PROVIDERS/MICROSOFT.SQL/SERVERS/TEST-DK-SQL-SERVER/DATABASES/MSSQL-LOG-TEST",
  "category": "QueryStoreRuntimeStatistics",
  "operationName": "QueryStoreRuntimeStatisticsEvent",
  "properties": {
    "ElasticPoolName": "",
    "DatabaseName": "mssql-log-test",
    "interval_start_time": 190795339750208,
    "interval_end_time": 190795340830208,
    "logical_io_writes": 0,
    "max_logical_io_writes": 0,
    "physical_io_reads": 0,
    "max_physical_io_reads": 0,
    "logical_io_reads": 390,
    "max_logical_io_reads": 26,
    "execution_type": 0,
    "count_executions": 15,
    "cpu_time": 2864,
    "max_cpu_time": 468,
    "dop": 15,
    "max_dop": 1,
    "rowcount": 60,
    "max_rowcount": 4,
    "query_max_used_memory": 0,
    "max_query_max_used_memory": 0,
    "duration": 2868,
    "max_duration": 468,
    "num_physical_io_reads": 0,
    "max_num_physical_io_reads": 0,
    "log_bytes_used": 0,
    "max_log_bytes_used": 0,
    "query_id": 21,
    "query_hash": "0xBD7BB7487C569456",
    "plan_id": 1,
    "query_plan_hash": "0x3E8B2F4730A974F0",
    "statement_sql_handle": "0x0900D11CBD9B9C98D44F145768E937530B340000000000000000000000000000000000000000000000000000"
  }
}

query_store_runtime_statistics_log_expected_output = {
    "cloud.provider": "Azure",
    "timestamp": "2021-08-12T07:26:32.4015726Z",
    "log.source": "QueryStoreRuntimeStatistics",
    "severity": "Informational",
    "content": json.dumps(query_store_runtime_statistics_log),
    RESOURCE_ID_ATTRIBUTE: "/SUBSCRIPTIONS/69B51384-146C-4685-9DAB-5AE01877D7B8/RESOURCEGROUPS/TEST-DK/PROVIDERS/MICROSOFT.SQL/SERVERS/TEST-DK-SQL-SERVER/DATABASES/MSSQL-LOG-TEST",
    SUBSCRIPTION_ATTRIBUTE: "69B51384-146C-4685-9DAB-5AE01877D7B8",
    RESOURCE_GROUP_ATTRIBUTE: "TEST-DK",
    RESOURCE_TYPE_ATTRIBUTE: "MICROSOFT.SQL/SERVERS/DATABASES",
    RESOURCE_NAME_ATTRIBUTE: "MSSQL-LOG-TEST",
    "db.system": "mssql",
    "db.name": "mssql-log-test",
    'dt.source_entity': 'AZURE_SQL_DATABASE-AE715D5D0538D957',
}


errors_log = {
  "LogicalServerName": "test-dk-sql-server",
  "SubscriptionId": "69b51384-146c-4685-9dab-5ae01877d7b8",
  "ResourceGroup": "test-dk",
  "time": "2021-08-12T07:26:32.4015726Z",
  "resourceId": "/SUBSCRIPTIONS/69B51384-146C-4685-9DAB-5AE01877D7B8/RESOURCEGROUPS/TEST-DK/PROVIDERS/MICROSOFT.SQL/SERVERS/TEST-DK-SQL-SERVER/DATABASES/MSSQL-LOG-TEST",
  "category": "Errors",
  "operationName": "ErrorEvent",
  "properties": {
    "ElasticPoolName": "",
    "DatabaseName": "mssql-log-test",
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
    RESOURCE_ID_ATTRIBUTE: "/SUBSCRIPTIONS/69B51384-146C-4685-9DAB-5AE01877D7B8/RESOURCEGROUPS/TEST-DK/PROVIDERS/MICROSOFT.SQL/SERVERS/TEST-DK-SQL-SERVER/DATABASES/MSSQL-LOG-TEST",
    SUBSCRIPTION_ATTRIBUTE: "69B51384-146C-4685-9DAB-5AE01877D7B8",
    RESOURCE_GROUP_ATTRIBUTE: "TEST-DK",
    RESOURCE_TYPE_ATTRIBUTE: "MICROSOFT.SQL/SERVERS/DATABASES",
    RESOURCE_NAME_ATTRIBUTE: "MSSQL-LOG-TEST",
    "db.system": "mssql",
    "db.name": "mssql-log-test",
    'dt.source_entity': 'AZURE_SQL_DATABASE-AE715D5D0538D957',
}


database_wait_statistics_log = {
  "LogicalServerName": "test-dk-sql-server",
  "SubscriptionId": "69b51384-146c-4685-9dab-5ae01877d7b8",
  "ResourceGroup": "test-dk",
  "time": "2021-08-12T07:26:32.4015726Z",
  "resourceId": "/SUBSCRIPTIONS/69B51384-146C-4685-9DAB-5AE01877D7B8/RESOURCEGROUPS/TEST-DK/PROVIDERS/MICROSOFT.SQL/SERVERS/TEST-DK-SQL-SERVER/DATABASES/MSSQL-LOG-TEST",
  "category": "QueryStoreWaitStatistics",
  "operationName": "QueryStoreWaitStatisticsEvent",
  "properties": {
    "ElasticPoolName": "",
    "DatabaseName": "mssql-log-test",
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
    RESOURCE_ID_ATTRIBUTE: "/SUBSCRIPTIONS/69B51384-146C-4685-9DAB-5AE01877D7B8/RESOURCEGROUPS/TEST-DK/PROVIDERS/MICROSOFT.SQL/SERVERS/TEST-DK-SQL-SERVER/DATABASES/MSSQL-LOG-TEST",
    SUBSCRIPTION_ATTRIBUTE: "69B51384-146C-4685-9DAB-5AE01877D7B8",
    RESOURCE_GROUP_ATTRIBUTE: "TEST-DK",
    RESOURCE_TYPE_ATTRIBUTE: "MICROSOFT.SQL/SERVERS/DATABASES",
    RESOURCE_NAME_ATTRIBUTE: "MSSQL-LOG-TEST",
    "db.system": "mssql",
    "db.name": "mssql-log-test",
    'dt.source_entity': 'AZURE_SQL_DATABASE-AE715D5D0538D957',
}


timeouts_log = {
  "LogicalServerName": "test-dk-sql-server",
  "SubscriptionId": "69b51384-146c-4685-9dab-5ae01877d7b8",
  "ResourceGroup": "test-dk",
  "time": "2021-08-12T07:26:32.4015726Z",
  "resourceId": "/SUBSCRIPTIONS/69B51384-146C-4685-9DAB-5AE01877D7B8/RESOURCEGROUPS/TEST-DK/PROVIDERS/MICROSOFT.SQL/SERVERS/TEST-DK-SQL-SERVER/DATABASES/MSSQL-LOG-TEST",
  "category": "Timeouts",
  "operationName": "TimeoutEvent",
  "properties": {
    "ElasticPoolName": "",
    "DatabaseName": "mssql-log-test",
    "error_state": 200,
    "query_hash": "0",
    "query_plan_hash": "0"
  }
}

timeouts_log_expected_output = {
    "cloud.provider": "Azure",
    "timestamp": "2021-08-12T07:26:32.4015726Z",
    "log.source": "Timeouts",
    "severity": "ERROR",
    "content": json.dumps(timeouts_log),
    RESOURCE_ID_ATTRIBUTE: "/SUBSCRIPTIONS/69B51384-146C-4685-9DAB-5AE01877D7B8/RESOURCEGROUPS/TEST-DK/PROVIDERS/MICROSOFT.SQL/SERVERS/TEST-DK-SQL-SERVER/DATABASES/MSSQL-LOG-TEST",
    SUBSCRIPTION_ATTRIBUTE: "69B51384-146C-4685-9DAB-5AE01877D7B8",
    RESOURCE_GROUP_ATTRIBUTE: "TEST-DK",
    RESOURCE_TYPE_ATTRIBUTE: "MICROSOFT.SQL/SERVERS/DATABASES",
    RESOURCE_NAME_ATTRIBUTE: "MSSQL-LOG-TEST",
    "db.system": "mssql",
    "db.name": "mssql-log-test",
    'dt.source_entity': 'AZURE_SQL_DATABASE-AE715D5D0538D957',
}


blocks_log = {
  "LogicalServerName": "test-dk-sql-server",
  "SubscriptionId": "69b51384-146c-4685-9dab-5ae01877d7b8",
  "ResourceGroup": "test-dk",
  "time": "2021-08-12T07:26:32.4015726Z",
  "resourceId": "/SUBSCRIPTIONS/69B51384-146C-4685-9DAB-5AE01877D7B8/RESOURCEGROUPS/TEST-DK/PROVIDERS/MICROSOFT.SQL/SERVERS/TEST-DK-SQL-SERVER/DATABASES/MSSQL-LOG-TEST",
  "category": "Blocks",
  "operationName": "BlockEvent",
  "properties": {
    "ElasticPoolName": "",
    "DatabaseName": "mssql-log-test",
    "duration": 33552000,
    "lock_mode": "X",
    "resource_owner_type": "LOCK",
    "blocked_process_filtered": "<blocked-process-report monitorLoop='101167'> <blocked-process> <process id='process2548f35a108' taskpriority='0' logused='0' waitresource='OBJECT: 5:1701581100:0 ' waittime='33552' ownerId='4938238' transactionname='user_transaction' lasttranstarted='2021-08-18T14:38:46.967' XDES='0x2549f9d0428' lockMode='X' schedulerid='1' kpid='58260' status='suspended' spid='82' sbid='0' ecid='0' priority='0' trancount='1' lastbatchstarted='2021-08-18T14:38:46.963' lastbatchcompleted='2021-08-18T14:38:46.957' lastattention='1900-01-01T00:00:00.957' clientapp='Azure SQL Query Editor' hostname='filtered' hostpid='31176' loginname='filtered' isolationlevel='read committed (2)' xactid='4938238' currentdb='5' currentdbname='mssql-log-test' lockTimeout='4294967295' clientoption1='671088672' clientoption2='128056'> <executionStack> <frame queryhash='0x31cb8cf160e93cc8' queryplanhash='0x8bc34538b4fd71aa' line='2' stmtstart='40' stmtend='156' sqlhandle='0x0200000051815707743fd1b5eaf6a22f0ba9f0fe30c5554b0000000000000000000000000000000000000000'/> </executionStack> <inputbuf> filtered </inputbuf> </process> </blocked-process> <blocking-process> <process status='suspended' waittime='51774' spid='63' sbid='0' ecid='0' priority='0' trancount='1' lastbatchstarted='2021-08-18T14:38:28.690' lastbatchcompleted='2021-08-18T14:38:27.863' lastattention='1900-01-01T00:00:00.863' clientapp='Azure SQL Query Editor' hostname='filtered' hostpid='31176' loginname='filtered' isolationlevel='read committed (2)' xactid='4937434' currentdb='5' currentdbname='mssql-log-test' lockTimeout='4294967295' clientoption1='671088672' clientoption2='128056'> <executionStack> <frame queryhash='0x0000000000000000' queryplanhash='0x0000000000000000' line='3' stmtstart='174' stmtend='254' sqlhandle='0x0200000082402729736a5bdd86aae03bd1d3a26dda62b9eb0000000000000000000000000000000000000000'/> </executionStack> <inputbuf> filtered </inputbuf> </process> </blocking-process> </blocked-process-report> "
  }
}

blocks_log_expected_output = {
    "cloud.provider": "Azure",
    "timestamp": "2021-08-12T07:26:32.4015726Z",
    "log.source": "Blocks",
    "severity": "ERROR",
    "content": json.dumps(blocks_log),
    RESOURCE_ID_ATTRIBUTE: "/SUBSCRIPTIONS/69B51384-146C-4685-9DAB-5AE01877D7B8/RESOURCEGROUPS/TEST-DK/PROVIDERS/MICROSOFT.SQL/SERVERS/TEST-DK-SQL-SERVER/DATABASES/MSSQL-LOG-TEST",
    SUBSCRIPTION_ATTRIBUTE: "69B51384-146C-4685-9DAB-5AE01877D7B8",
    RESOURCE_GROUP_ATTRIBUTE: "TEST-DK",
    RESOURCE_TYPE_ATTRIBUTE: "MICROSOFT.SQL/SERVERS/DATABASES",
    RESOURCE_NAME_ATTRIBUTE: "MSSQL-LOG-TEST",
    "db.system": "mssql",
    "db.name": "mssql-log-test",
    'dt.source_entity': 'AZURE_SQL_DATABASE-AE715D5D0538D957',
}


deadlocks_log = {
  "LogicalServerName": "test-dk-sql-server",
  "SubscriptionId": "69b51384-146c-4685-9dab-5ae01877d7b8",
  "ResourceGroup": "test-dk",
  "time": "2021-08-12T07:26:32.4015726Z",
  "resourceId": "/SUBSCRIPTIONS/69B51384-146C-4685-9DAB-5AE01877D7B8/RESOURCEGROUPS/TEST-DK/PROVIDERS/MICROSOFT.SQL/SERVERS/TEST-DK-SQL-SERVER/DATABASES/MSSQL-LOG-TEST",
  "category": "Deadlocks",
  "operationName": "DeadlockEvent",
  "properties": {
    "ElasticPoolName": "",
    "DatabaseName": "mssql-log-test",
    "deadlock_xml": "<deadlock> <victim-list> <victimProcess id='process254933a24e8'/> </victim-list> <process-list> <process id='process254933a24e8' taskpriority='0' logused='384' waitresource='KEY: 5:72057594047102976 (5495ec521809)' waittime='51240' ownerId='5796310' transactionname='user_transaction' lasttranstarted='2021-08-19T14:35:38.130' XDES='0x254a3abc428' lockMode='U' schedulerid='2' kpid='57548' status='suspended' spid='62' sbid='0' ecid='0' priority='0' trancount='2' lastbatchstarted='2021-08-19T14:35:38.123' lastbatchcompleted='2021-08-19T14:35:38.120' lastattention='1900-01-01T00:00:00.120' clientapp='Azure SQL Query Editor' hostname='filtered' hostpid='23692' loginname='filtered' isolationlevel='read committed (2)' xactid='5796310' currentdb='5' currentdbname='mssql-log-test' lockTimeout='4294967295' clientoption1='671088672' clientoption2='128056'> <executionStack> <frame procname='unknown' queryhash='0xfb56c41f149be1bf' queryplanhash='0x61108d8e53ae0281' line='5' stmtstart='190' stmtend='352' sqlhandle='0x0200000076fe5d1c0c6a574e5832f3b8ff93e633e3a1d6ae0000000000000000000000000000000000000000'> unknown </frame> <frame procname='unknown' queryhash='0xfb56c41f149be1bf' queryplanhash='0x61108d8e53ae0281' line='5' stmtstart='190' stmtend='352' sqlhandle='0x020000006422542410cc57ec92189c4c563c2ea7917ff1a20000000000000000000000000000000000000000'> unknown </frame> </executionStack> <inputbuf> filtered </inputbuf> </process> <process id='process2549ababc28' taskpriority='0' logused='628' waitresource='KEY: 5:72057594047037440 (8194443284a0)' waittime='2049' ownerId='5796274' transactionname='user_transaction' lasttranstarted='2021-08-19T14:35:37.317' XDES='0x2549f9cc428' lockMode='U' schedulerid='1' kpid='95368' status='suspended' spid='65' sbid='0' ecid='0' priority='0' trancount='2' lastbatchstarted='2021-08-19T14:35:37.277' lastbatchcompleted='2021-08-19T14:35:37.277' lastattention='1900-01-01T00:00:00.277' clientapp='Azure SQL Query Editor' hostname='filtered' hostpid='23692' loginname='filtered' isolationlevel='read committed (2)' xactid='5796274' currentdb='5' currentdbname='mssql-log-test' lockTimeout='4294967295' clientoption1='671088672' clientoption2='128056'> <executionStack> <frame procname='unknown' queryhash='0xa57159d12cb813fb' queryplanhash='0x10cbf3310dab2eb5' line='7' stmtstart='58' stmtend='186' sqlhandle='0x020000009897910214549261257b982dc5f67c7e4f562ee10000000000000000000000000000000000000000'> unknown </frame> <frame procname='unknown' queryhash='0xa57159d12cb813fb' queryplanhash='0x10cbf3310dab2eb5' line='7' stmtstart='270' stmtend='408' sqlhandle='0x0200000044d1d71bd22f410cda1c735bd7ac0e11cbcee6c30000000000000000000000000000000000000000'> unknown </frame> </executionStack> <inputbuf> filtered </inputbuf> </process> </process-list> <resource-list> <keylock hobtid='72057594047102976' dbid='5' objectname='filtered' indexname='filtered' id='lock2548759f780' mode='X' associatedObjectId='72057594047102976'> <owner-list> <owner id='process2549ababc28' mode='X'/> </owner-list> <waiter-list> <waiter id='process254933a24e8' mode='U' requestType='wait'/> </waiter-list> </keylock> <keylock hobtid='72057594047037440' dbid='5' objectname='filtered' indexname='filtered' id='lock25483184880' mode='X' associatedObjectId='72057594047037440'> <owner-list> <owner id='process254933a24e8' mode='X'/> </owner-list> <waiter-list> <waiter id='process2549ababc28' mode='U' requestType='wait'/> </waiter-list> </keylock> </resource-list> </deadlock> "
  }
}

deadlocks_log_expected_output = {
    "cloud.provider": "Azure",
    "timestamp": "2021-08-12T07:26:32.4015726Z",
    "log.source": "Deadlocks",
    "severity": "ERROR",
    "content": json.dumps(deadlocks_log),
    RESOURCE_ID_ATTRIBUTE: "/SUBSCRIPTIONS/69B51384-146C-4685-9DAB-5AE01877D7B8/RESOURCEGROUPS/TEST-DK/PROVIDERS/MICROSOFT.SQL/SERVERS/TEST-DK-SQL-SERVER/DATABASES/MSSQL-LOG-TEST",
    SUBSCRIPTION_ATTRIBUTE: "69B51384-146C-4685-9DAB-5AE01877D7B8",
    RESOURCE_GROUP_ATTRIBUTE: "TEST-DK",
    RESOURCE_TYPE_ATTRIBUTE: "MICROSOFT.SQL/SERVERS/DATABASES",
    RESOURCE_NAME_ATTRIBUTE: "MSSQL-LOG-TEST",
    "db.system": "mssql",
    "db.name": "mssql-log-test",
    'dt.source_entity': 'AZURE_SQL_DATABASE-AE715D5D0538D957',
}


@pytest.fixture()
def self_monitoring():
    return SelfMonitoring(execution_time=datetime.utcnow())


def test_query_store_runtime_statistics_log(self_monitoring):
    actual_output = parse_record(query_store_runtime_statistics_log, self_monitoring)
    assert actual_output == query_store_runtime_statistics_log_expected_output


def test_automatic_tuning_log(self_monitoring):
    actual_output = parse_record(automatic_tuning_log, self_monitoring)
    assert actual_output == automatic_tuning_log_expected_output


def test_errors_log(self_monitoring):
    actual_output = parse_record(errors_log, self_monitoring)
    assert actual_output == errors_log_expected_output


def test_database_wait_statistics_log(self_monitoring):
    actual_output = parse_record(database_wait_statistics_log, self_monitoring)
    assert actual_output == database_wait_statistics_log_expected_output


def test_timeouts_log(self_monitoring):
    actual_output = parse_record(timeouts_log, self_monitoring)
    assert actual_output == timeouts_log_expected_output


def test_blocks_log(self_monitoring):
    actual_output = parse_record(blocks_log, self_monitoring)
    assert actual_output == blocks_log_expected_output


def test_deadlocks_log(self_monitoring):
    actual_output = parse_record(deadlocks_log, self_monitoring)
    assert actual_output == deadlocks_log_expected_output



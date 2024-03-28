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
import os
from typing import NewType, Any

from logs_ingest.filtering import LogFilter

MonkeyPatchFixture = NewType("MonkeyPatchFixture", Any)

parsed_record = {
    'cloud.provider': 'Azure',
    'severity': 'Informational',
    "content": "Executed \"Functions.logs_ingest\" (Succeeded, Id=26849b40-bba5-41ee-9521-fc3205a39b5e, Duration=50ms)",
    'azure.resource.id': '/SUBSCRIPTIONS/69B51384-146C-4685-9DAB-5AE01877D7B8/RESOURCEGROUPS/LOGS-INGEST-FUNCTION/PROVIDERS/MICROSOFT.WEB/SITES/INGEST-LOGS-FUNCTION',
    'azure.subscription': '69B51384-146C-4685-9DAB-5AE01877D7B8',
    'azure.resource.group': 'LOGS-INGEST-FUNCTION',
    'azure.resource.name': 'INGEST-LOGS-FUNCTION',
    'azure.resource.type': 'MICROSOFT.WEB/SITES'}


def test_wrong_filter_config(monkeypatch: MonkeyPatchFixture):
    monkeypatch.setenv("FILTER_CONFIG", ";")
    log_filter = LogFilter()
    assert log_filter.filters_dict == {}
    assert not log_filter.should_filter_out_record(parsed_record)


def test_wrong_filter_config2(monkeypatch: MonkeyPatchFixture):
    monkeypatch.setenv("FILTER_CONFIG", ";=")
    log_filter = LogFilter()
    assert log_filter.filters_dict == {}
    assert not log_filter.should_filter_out_record(parsed_record)


def test_wrong_filter_config_with_not_supported_filter_name(monkeypatch: MonkeyPatchFixture):
    monkeypatch.setenv("FILTER_CONFIG", "FILTER.TEST.MIN_LOG_LEVEL=2")
    log_filter = LogFilter()
    assert not log_filter.should_filter_out_record(parsed_record)


def test_filter_config_with_spaces(monkeypatch: MonkeyPatchFixture):
    monkeypatch.setenv("FILTER_CONFIG", "FILTER.GLOBAL.MIN_LOG_LEVEL=  informational; FILTER.GLOBAL.CONTAINS_PATTERN = *logs_ingest*")
    log_filter = LogFilter()
    assert not log_filter.should_filter_out_record(parsed_record)


def test_none_level_with_log_level_filter(monkeypatch: MonkeyPatchFixture):
    monkeypatch.setenv("FILTER_CONFIG", "FILTER.RESOURCE_TYPE.MIN_LOG_LEVEL.MICROSOFT.WEB/SITES=2")
    parsed_record = {
        'azure.resource.id': '/SUBSCRIPTIONS/69B51384-146C-4685-9DAB-5AE01877D7B8/RESOURCEGROUPS/LOGS-INGEST-FUNCTION/PROVIDERS/MICROSOFT.WEB/SITES/INGEST-LOGS-FUNCTION',
        'azure.resource.type': 'MICROSOFT.WEB/SITES',}
    log_filter = LogFilter()
    assert log_filter.should_filter_out_record(parsed_record)


#GLOBAL FILTERS
def test_filter_global_min_log_level_warning(monkeypatch: MonkeyPatchFixture):
    monkeypatch.setenv("FILTER_CONFIG", "FILTER.GLOBAL.MIN_LOG_LEVEL=warning")
    log_filter = LogFilter()
    assert log_filter.should_filter_out_record(parsed_record)


def test_filter_global_min_log_level_warning_uppercase():
    os.environ["FILTER_CONFIG"] = "FILTER.GLOBAL.MIN_LOG_LEVEL=WARNING"
    log_filter = LogFilter()
    assert log_filter.should_filter_out_record(parsed_record)


def test_filter_global_min_log_level_warning_digit():
    os.environ["FILTER_CONFIG"] = "FILTER.GLOBAL.MIN_LOG_LEVEL=3"
    log_filter = LogFilter()
    assert log_filter.should_filter_out_record(parsed_record)


def test_filter_global_incorrect_min_log_level():
    os.environ["FILTER_CONFIG"] = "FILTER.GLOBAL.MIN_LOG_LEVEL=Info"
    log_filter = LogFilter()
    assert not log_filter.should_filter_out_record(parsed_record)


def test_filter_global_incorrect_min_log_level_digit():
    os.environ["FILTER_CONFIG"] = "FILTER.GLOBAL.MIN_LOG_LEVEL=20"
    log_filter = LogFilter()
    assert not log_filter.should_filter_out_record(parsed_record)


def test_filter_global_contains_pattern_functions_logs():
    os.environ["FILTER_CONFIG"] = "FILTER.GLOBAL.CONTAINS_PATTERN=*logs_ingest*"
    log_filter = LogFilter()
    assert not log_filter.should_filter_out_record(parsed_record)


def test_filter_global_contains_pattern_sql():
    os.environ["FILTER_CONFIG"] = "FILTER.GLOBAL.CONTAINS_PATTERN=*SQL*"
    log_filter = LogFilter()
    assert log_filter.should_filter_out_record(parsed_record)


def test_filter_global_log_level_and_contains_pattern():
    os.environ["FILTER_CONFIG"] = "FILTER.GLOBAL.MIN_LOG_LEVEL=4;FILTER.GLOBAL.CONTAINS_PATTERN=*logs_ingest*"
    log_filter = LogFilter()
    assert not log_filter.should_filter_out_record(parsed_record)


def test_filter_global_log_level_and_contains_pattern_sql():
    os.environ["FILTER_CONFIG"] = "FILTER.GLOBAL.MIN_LOG_LEVEL=4;FILTER.GLOBAL.CONTAINS_PATTERN=*SQL*"
    log_filter = LogFilter()
    assert log_filter.should_filter_out_record(parsed_record)


def test_several_filters_global_patterns_last_correct():
    os.environ["FILTER_CONFIG"] = "FILTER.GLOBAL.CONTAINS_PATTERN=*SQL*;FILTER.GLOBAL.CONTAINS_PATTERN=*logs_ingest*"
    log_filter = LogFilter()
    assert not log_filter.should_filter_out_record(parsed_record)


def test_several_filters_global_patterns_last_incorrect():
    os.environ["FILTER_CONFIG"] = "FILTER.GLOBAL.CONTAINS_PATTERN=*Microsoft.Web/sites/functions/log*;FILTER.GLOBAL.CONTAINS_PATTERN=*SQL*"
    log_filter = LogFilter()
    assert log_filter.should_filter_out_record(parsed_record)


# RESOURCE TYPE FILTERS
def test_filter_global_and_resource_type_min_log_level():
    os.environ["FILTER_CONFIG"] = "FILTER.GLOBAL.MIN_LOG_LEVEL=2;FILTER.RESOURCE_TYPE.MIN_LOG_LEVEL.microsoft.web/sites=4"
    log_filter = LogFilter()
    assert not log_filter.should_filter_out_record(parsed_record)


def test_filter_global_and_resource_type_incorrect_min_log_level():
    os.environ["FILTER_CONFIG"] = "FILTER.GLOBAL.MIN_LOG_LEVEL=2;FILTER.RESOURCE_TYPE.MIN_LOG_LEVEL.MICROSOFT.WEB/SITES=Info"
    log_filter = LogFilter()
    assert log_filter.should_filter_out_record(parsed_record)


def test_global_level_and_resource_type_contains_pattern():
    os.environ["FILTER_CONFIG"] = "FILTER.GLOBAL.MIN_LOG_LEVEL=2;FILTER.RESOURCE_TYPE.CONTAINS_PATTERN.MICROSOFT.WEB/SITES=*logs_ingest*"
    log_filter = LogFilter()
    assert not log_filter.should_filter_out_record(parsed_record)


def test_all_global_and_resource_type_filters():
    os.environ["FILTER_CONFIG"] = "FILTER.GLOBAL.MIN_LOG_LEVEL=2;FILTER.GLOBAL.CONTAINS_PATTERN=*Microsoft.Web/sites/functions/log*;FILTER.RESOURCE_TYPE.MIN_LOG_LEVEL.MICROSOFT.WEB/SITES=Informational;FILTER.RESOURCE_TYPE.CONTAINS_PATTERN.MICROSOFT.WEB/SITES=*logs_ingest*"
    log_filter = LogFilter()
    assert not log_filter.should_filter_out_record(parsed_record)


#RESOURCE_ID FILTERS
def test_filter_all_min_log_level():
    os.environ["FILTER_CONFIG"] = "FILTER.GLOBAL.MIN_LOG_LEVEL=2;FILTER.RESOURCE_TYPE.MIN_LOG_LEVEL.MICROSOFT.WEB/SITES=Critical;FILTER.RESOURCE_ID.MIN_LOG_LEVEL./SUBSCRIPTIONS/69B51384-146C-4685-9DAB-5AE01877D7B8/RESOURCEGROUPS/LOGS-INGEST-FUNCTION/PROVIDERS/MICROSOFT.WEB/SITES/ingest-logs-function=Informational"
    log_filter = LogFilter()
    assert not log_filter.should_filter_out_record(parsed_record)


def test_all_filters_not_filter_out():
    os.environ["FILTER_CONFIG"] = "FILTER.GLOBAL.MIN_LOG_LEVEL=2;FILTER.GLOBAL.CONTAINS_PATTERN=*pattern*;FILTER.RESOURCE_TYPE.MIN_LOG_LEVEL.MICROSOFT.WEB/SITES=3;FILTER.RESOURCE_TYPE.CONTAINS_PATTERN.MICROSOFT.WEB/SITES=*pattern*;FILTER.RESOURCE_ID.MIN_LOG_LEVEL./SUBSCRIPTIONS/69B51384-146C-4685-9DAB-5AE01877D7B8/RESOURCEGROUPS/LOGS-INGEST-FUNCTION/PROVIDERS/MICROSOFT.WEB/SITES/INGEST-LOGS-FUNCTION=Informational;FILTER.RESOURCE_ID.CONTAINS_PATTERN./SUBSCRIPTIONS/69B51384-146C-4685-9DAB-5AE01877D7B8/RESOURCEGROUPS/LOGS-INGEST-FUNCTION/PROVIDERS/MICROSOFT.WEB/SITES/INGEST-LOGS-FUNCTION=*logs_ingest*"
    log_filter = LogFilter()
    assert not log_filter.should_filter_out_record(parsed_record)


def test_all_filters_filter_out():
    os.environ["FILTER_CONFIG"] = "FILTER.GLOBAL.MIN_LOG_LEVEL=2;FILTER.GLOBAL.CONTAINS_PATTERN=*pattern*;FILTER.RESOURCE_TYPE.MIN_LOG_LEVEL.MICROSOFT.WEB/SITES=3;FILTER.RESOURCE_TYPE.CONTAINS_PATTERN.MICROSOFT.WEB/SITES=*pattern*;FILTER.RESOURCE_ID.MIN_LOG_LEVEL./SUBSCRIPTIONS/69B51384-146C-4685-9DAB-5AE01877D7B8/RESOURCEGROUPS/LOGS-INGEST-FUNCTION/PROVIDERS/MICROSOFT.WEB/SITES/INGEST-LOGS-FUNCTION=Informational;FILTER.RESOURCE_ID.CONTAINS_PATTERN./SUBSCRIPTIONS/69B51384-146C-4685-9DAB-5AE01877D7B8/RESOURCEGROUPS/LOGS-INGEST-FUNCTION/PROVIDERS/MICROSOFT.WEB/SITES/INGEST-LOGS-FUNCTION=pattern"
    log_filter = LogFilter()
    assert log_filter.should_filter_out_record(parsed_record)


def test_filter_global_with_bad_or_condition():
    os.environ["FILTER_CONFIG"] = "FILTER.GLOBAL.MIN_LOG_LEVEL=3;FILTER.GLOBAL.CONTAINS_PATTERN=Executed* | *Functions* | *not_fitting*"
    log_filter = LogFilter()
    assert log_filter.should_filter_out_record(parsed_record)


def test_filter_global_with_good_or_conditions():
    os.environ["FILTER_CONFIG"] = "FILTER.GLOBAL.CONTAINS_PATTERN=*logs_ingest* | *Succeeded*"
    log_filter = LogFilter()
    assert not log_filter.should_filter_out_record(parsed_record)


def test_filter_global_with_only_bad_conditions():
    os.environ["FILTER_CONFIG"] = "FILTER.GLOBAL.CONTAINS_PATTERN=*bad* | *not_fitting_anything*"
    log_filter = LogFilter()
    assert log_filter.should_filter_out_record(parsed_record)

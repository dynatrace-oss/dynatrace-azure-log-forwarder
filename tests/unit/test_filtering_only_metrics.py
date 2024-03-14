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
  "cloud.provider": "Azure",
  "severity": "Informational",
  "azure.resource.id": "/SUBSCRIPTIONS/C85913AE-8C54-47FA-84E0-FF171B8D3579/RESOURCEGROUPS/DYNATRACERG/PROVIDERS/MICROSOFT.WEB/SITES/DYNATRACELOGFW-FUNCTION",
  "azure.subscription": "C85913AE-8C54-47FA-84E0-FF171B8D3579",
  "azure.resource.group": "DYNATRACERG",
  "azure.resource.name": "DYNATRACELOGFW-FUNCTION",
  "azure.resource.type": "MICROSOFT.WEB/SITES",
  "isMetric": "True"
}


def test_resource_id_not_filter_out_only_metrics():
    os.environ["FILTER_CONFIG"] = "FILTER.RESOURCE_ID.ONLY_METRICS./SUBSCRIPTIONS/C85913AE-8C54-47FA-84E0-FF171B8D3579/RESOURCEGROUPS/DYNATRACERG/PROVIDERS/MICROSOFT.WEB/SITES/DYNATRACELOGFW-FUNCTION=True"
    log_filter = LogFilter()
    assert not log_filter.should_filter_out_record(parsed_record)

def test_resource_id_filter_out_only_metrics():
    os.environ["FILTER_CONFIG"] = "FILTER.RESOURCE_ID.ONLY_METRICS./SUBSCRIPTIONS/C85913AE-8C54-47FA-84E0-FF171B8D3579/RESOURCEGROUPS/DYNATRACERG/PROVIDERS/MICROSOFT.WEB/SITES/DYNATRACELOGFW-FUNCTION=False"
    log_filter = LogFilter()
    assert log_filter.should_filter_out_record(parsed_record)

def test_resource_type_not_filter_out_only_metrics():
    os.environ["FILTER_CONFIG"] = "FILTER.RESOURCE_TYPE.ONLY_METRICS.MICROSOFT.WEB/SITES=True"
    log_filter = LogFilter()
    assert not log_filter.should_filter_out_record(parsed_record)

def test_resource_type_filter_out_only_metrics():
    os.environ["FILTER_CONFIG"] = "FILTER.RESOURCE_TYPE.ONLY_METRICS.MICROSOFT.WEB/SITES=False"
    log_filter = LogFilter()
    assert log_filter.should_filter_out_record(parsed_record)

def test_all_filters_not_filter_out_only_metrics():
    os.environ["FILTER_CONFIG"] = "FILTER.RESOURCE_ID.ONLY_METRICS./SUBSCRIPTIONS/C85913AE-8C54-47FA-84E0-FF171B8D3579/RESOURCEGROUPS/DYNATRACERG/PROVIDERS/MICROSOFT.WEB/SITES/DYNATRACELOGFW-FUNCTION=True;FILTER.RESOURCE_TYPE.ONLY_METRICS.MICROSOFT.WEB/SITES=True"
    log_filter = LogFilter()
    assert not log_filter.should_filter_out_record(parsed_record)

def test_all_filters_filter_out_only_metrics():
    os.environ["FILTER_CONFIG"] = "FILTER.RESOURCE_ID.ONLY_METRICS./SUBSCRIPTIONS/C85913AE-8C54-47FA-84E0-FF171B8D3579/RESOURCEGROUPS/DYNATRACERG/PROVIDERS/MICROSOFT.WEB/SITES/DYNATRACELOGFW-FUNCTION=False;FILTER.RESOURCE_TYPE.ONLY_METRICS.MICROSOFT.WEB/SITES=False"
    log_filter = LogFilter()
    assert log_filter.should_filter_out_record(parsed_record)

def test_global_filters_not_filter_out_only_metrics():
    os.environ["FILTER_CONFIG"] = "FILTER.GLOBAL.ONLY_METRICS=True"
    log_filter = LogFilter()
    assert not log_filter.should_filter_out_record(parsed_record)

def test_global_filters_filter_out_v2():
    os.environ["FILTER_CONFIG"] = "FILTER.GLOBAL.ONLY_METRICS=False"
    log_filter = LogFilter()
    assert log_filter.should_filter_out_record(parsed_record)

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
import os
from collections import Counter
from datetime import datetime
from typing import NewType, Any
from urllib.error import HTTPError

import pytest
from azure.functions import EventHubEvent
from wiremock.constants import Config
from wiremock.resources.mappings import Mapping, MappingRequest, HttpMethods, MappingResponse
from wiremock.resources.mappings.resource import Mappings
from wiremock.resources.requests.resource import Requests
from wiremock.server import WireMockServer

from logs_ingest import main
from logs_ingest.self_monitoring import DynatraceConnectivity, SelfMonitoring

MOCKED_API_PORT = 9011
ACCESS_KEY = 'abcdefjhij1234567890'
CODE_DIRECTORY = os.path.dirname(os.path.realpath(__file__))
EVENTS_PATH = os.path.join(CODE_DIRECTORY, 'events.json')
FILE_SIZE = os.path.getsize(EVENTS_PATH)
EVENTS_NUMBER = 5

MonkeyPatchFixture = NewType("MonkeyPatchFixture", Any)
system_variables = {
    'DYNATRACE_LOG_INGEST_REQUEST_MAX_SIZE': str(FILE_SIZE*2),
    'DYNATRACE_URL': 'http://localhost:' + str(MOCKED_API_PORT),
    'DYNATRACE_ACCESS_KEY': ACCESS_KEY,
    'REQUIRE_VALID_CERTIFICATE': 'False'
    # Set below-mentioned environment variables to push custom metrics to Azure Function App
    # 'SELF_MONITORING_ENABLED': 'True',
    # 'RESOURCE_ID': '',
    # 'REGION': ''
}


@pytest.fixture(scope="session", autouse=True)
def setup_wiremock():
    # setup WireMock server
    wiremock = WireMockServer(port=MOCKED_API_PORT)
    wiremock.start()
    Config.base_url = 'http://localhost:{}/__admin'.format(MOCKED_API_PORT)

    # run test
    yield

    # stop WireMock server
    wiremock.stop()


@pytest.fixture(scope="module")
def init_events():
    with open(EVENTS_PATH) as file:
        records = json.load(file)
        current_datetime = datetime.utcnow()
        old_datetime = datetime.fromtimestamp(1615806000) #15.03.2021 11:00
        # Two records with old timestamp,
        # one with timestamp without timezone,
        # rest with current timestamps UTC
        timestamp = current_datetime.replace(microsecond=0).isoformat()
        records[2]["time"] = timestamp
        for record in records[3:]:
            record["time"] = timestamp + "Z"
        events = [EventHubEvent(body=json.dumps({"records": records}).encode('utf-8'), enqueued_time=old_datetime)]
        for _ in range(1, EVENTS_NUMBER):
            events.append(EventHubEvent(body=json.dumps({"records": records}).encode('utf-8'), enqueued_time=current_datetime))
        return events


@pytest.fixture(scope="function", autouse=True)
def cleanup():
    Mappings.delete_all_mappings()
    Requests.reset_request_journal()


@pytest.fixture(scope="function")
def self_monitoring():
    return SelfMonitoring(execution_time=datetime.utcnow())


def test_main_success(monkeypatch: MonkeyPatchFixture, init_events, self_monitoring):
    response(200, "Success")

    # given
    for variable_name in system_variables:
        monkeypatch.setenv(variable_name, system_variables[variable_name])
    monkeypatch.setattr(main, 'content_length_limit', 1000)

    # when
    main.process_logs(init_events, self_monitoring)

    # then
    sent_requests = Requests.get_all_received_requests().get_json_data()
    print("Sent requests: {}".format(json.dumps(sent_requests)))

    assert int(sent_requests.get('meta').get('total')) == EVENTS_NUMBER - 2 # rejected 8 too old logs (4 records = 1 event)
    for request in sent_requests.get('requests'):
        assert_correct_body_structure(request)
        assert request.get('responseDefinition').get('status') == 200

    assert self_monitoring.too_old_records == 5
    assert self_monitoring.parsing_errors == 4
    assert self_monitoring.too_long_content_size == [1317, 1317, 1317, 1317]
    assert Counter(self_monitoring.dynatrace_connectivities) == {DynatraceConnectivity.Ok: 3}
    assert self_monitoring.processing_time > 0
    assert self_monitoring.sending_time > 0
    assert self_monitoring.sent_log_entries == 16


def test_main_expired_token(monkeypatch: MonkeyPatchFixture, init_events, self_monitoring):
    response(401, "Expired token")

    # given
    for variable_name in system_variables:
        monkeypatch.setenv(variable_name, system_variables[variable_name])
    monkeypatch.setattr(main, 'content_length_limit', 1000)

    # when
    main.process_logs(init_events, self_monitoring)

    # then
    sent_requests = Requests.get_all_received_requests().get_json_data()
    print("Sent requests: {}".format(json.dumps(sent_requests)))

    assert int(sent_requests.get('meta').get('total')) == EVENTS_NUMBER - 2
    for request in sent_requests.get('requests'):
        assert_correct_body_structure(request)
        assert request.get('responseDefinition').get('status') == 401

    assert self_monitoring.too_old_records == 5
    assert self_monitoring.parsing_errors == 4
    assert self_monitoring.too_long_content_size == [1317, 1317, 1317, 1317]
    assert Counter(self_monitoring.dynatrace_connectivities) == {DynatraceConnectivity.ExpiredToken: 3}
    assert self_monitoring.processing_time > 0
    assert self_monitoring.sending_time > 0
    assert self_monitoring.sent_log_entries == 0


def test_main_server_error(monkeypatch: MonkeyPatchFixture, init_events, self_monitoring):
    response(500, "Server error")

    # given
    for variable_name in system_variables:
        monkeypatch.setenv(variable_name, system_variables[variable_name])
    monkeypatch.setattr(main, 'content_length_limit', 1000)

    # when
    with pytest.raises(HTTPError):
        main.process_logs(init_events, self_monitoring)

    # then
    sent_requests = Requests.get_all_received_requests().get_json_data()
    print("Sent requests: {}".format(json.dumps(sent_requests)))

    assert int(sent_requests.get('meta').get('total')) == 3
    for request in sent_requests.get('requests'):
        assert_correct_body_structure(request)
        assert request.get('responseDefinition').get('status') == 500

    assert self_monitoring.too_old_records == 5
    assert self_monitoring.parsing_errors == 4
    assert self_monitoring.too_long_content_size == [1317, 1317, 1317, 1317]
    assert Counter(self_monitoring.dynatrace_connectivities) == {DynatraceConnectivity.Other:3}
    assert self_monitoring.processing_time > 0
    assert self_monitoring.sending_time > 0
    assert self_monitoring.sent_log_entries == 0


def response(status: int, status_message: str):
    Mappings.create_mapping(mapping=Mapping(
        priority=100,
        request=MappingRequest(
            method=HttpMethods.POST,
            url='/api/v2/logs/ingest',
            headers={'Authorization': {'equalTo': "Api-Token {}".format(ACCESS_KEY)}},
        ),
        response=MappingResponse(
            status=status,
            status_message=status_message
        ),
        persistent=False
    ))


def assert_correct_body_structure(request):
    request_body = request.get("request", {}).get("body", None)
    assert request_body
    request_data = json.loads(request_body)

    for record in request_data:
        assert 'cloud.provider' in record
        assert 'severity' in record
        assert 'azure.resource.id' in record
        assert 'content' in record

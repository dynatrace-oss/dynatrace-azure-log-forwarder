#   Copyright 2022 Dynatrace LLC
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

from logs_ingest.main import parse_to_json

def test_linux_log():

    # given
    log_entry = "{\
        \"level\": \"Informational\",\
        \"time\": \"04/05/2022 07:54:00\", \
        \"properties\": \"{\'appName\':\'ik-log-forwarder-function\',\'message\':\'Pare to json test.\',\'level\':\'Information\',\'levelId\':2,\'processId\':24}\"\
    }"
    expected_linux_log = {
        "level": "Informational",
        "time": "04/05/2022 07:54:00",
        "properties": {"appName":"ik-log-forwarder-function","message":"Pare to json test.","level":"Information","levelId":2,"processId":24}
    }

    # when
    json_event = parse_to_json(log_entry)
    if json_event["properties"] and isinstance(json_event["properties"], str):
        json_event["properties"] = parse_to_json(json_event["properties"])

    # then
    assert json_event == expected_linux_log


def test_windows_log():

    # given
    log_entry = "{\
        \"level\": \"Informational\",\
        \"time\": \"2022-04-05T10:29:59.9999691Z\", \
        \"properties\": {\"appName\":\"ik-log-forwarder-function\",\"message\":\"Pare to json test.\",\"level\":\"Information\",\"levelId\":2,\"processId\":24}\
    }"
    expected_windows_log = {
        "level": "Informational",
        "time": "2022-04-05T10:29:59.9999691Z",
        "properties": {"appName":"ik-log-forwarder-function","message":"Pare to json test.","level":"Information","levelId":2,"processId":24}
    }

    # when
    json_event = parse_to_json(log_entry)
    if json_event["properties"] and isinstance(json_event["properties"], str):
        json_event["properties"] = parse_to_json(json_event["properties"])

    # then
    assert json_event == expected_windows_log

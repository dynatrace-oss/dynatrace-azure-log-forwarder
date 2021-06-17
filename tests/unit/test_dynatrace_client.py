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
import random
from math import ceil
from typing import NewType, Any

from logs_ingest import dynatrace_client

log_message = "WALTHAM, Mass.--(BUSINESS WIRE)-- Software intelligence company Dynatrace (NYSE: DT) announced today its entry into the cloud application security market with the addition of a new module to its industry-leading Software Intelligence Platform. The Dynatrace® Application Security Module provides continuous runtime application self-protection (RASP) capabilities for applications in production as well as preproduction and is optimized for Kubernetes architectures and DevSecOps approaches. This module inherits the automation, AI, scalability, and enterprise-grade robustness of the Dynatrace® Software Intelligence Platform and extends it to modern cloud RASP use cases. Dynatrace customers can launch this module with the flip of a switch, empowering the world’s leading organizations currently using the Dynatrace platform to immediately increase security coverage and precision.;"

request_body_len_max = len(log_message.encode("UTF-8")) * 3 + 20

MonkeyPatchFixture = NewType("MonkeyPatchFixture", Any)


def create_log_entry_with_random_len_msg():
    random_len = random.randint(1, len(log_message))
    random_len_str = log_message[0: random_len]

    return {
        'content': random_len_str,
        'cloud.provider': 'AWS',
        'severity': 'INFO'
    }


def test_prepare_serialized_batches(monkeypatch: MonkeyPatchFixture):
    monkeypatch.setenv("DYNATRACE_LOG_INGEST_REQUEST_MAX_SIZE", str(request_body_len_max))

    how_many_logs = 200
    logs = [create_log_entry_with_random_len_msg() for x in range(how_many_logs)]

    batches = dynatrace_client.prepare_serialized_batches(logs)

    assert len(batches) >= 1

    entries_in_batches = 0

    for batch in batches:
        batch_log = batch[0]
        assert len(batch_log) <= request_body_len_max
        entries_in_batches += len(json.loads(batch_log))

    assert entries_in_batches == how_many_logs

    logs_lengths = [len(log) for log in logs]
    logs_total_length = sum(logs_lengths)

    batches_lengths = [len(batch[0]) for batch in batches]
    batches_total_length = sum(batches_lengths)

    assert batches_total_length > logs_total_length

def test_prepare_serialized_batches_split_by_events_limit(monkeypatch: MonkeyPatchFixture):
    max_events = 5
    how_many_logs = 51
    expected_batches = ceil(how_many_logs / max_events)

    monkeypatch.setenv("DYNATRACE_LOG_INGEST_REQUEST_MAX_EVENTS", str(max_events))

    logs = [create_log_entry_with_random_len_msg() for x in range(how_many_logs)]

    batches = dynatrace_client.prepare_serialized_batches(logs)

    assert len(batches) == expected_batches

    entries_in_batches = 0

    for batch in batches:
        batch_log = batch[0]
        entries_in_batches += len(json.loads(batch_log))

    assert entries_in_batches == how_many_logs

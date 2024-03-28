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

import logs_ingest.main
from logs_ingest.main import parse_record
from logs_ingest.self_monitoring import SelfMonitoring

log_message = "WALTHAM, Mass.--(BUSINESS WIRE)-- Software intelligence company Dynatrace (NYSE: DT) announced today its entry into the cloud application security market with the addition of a new module to its industry-leading Software Intelligence Platform. The Dynatrace® Application Security Module provides continuous runtime application self-protection (RASP) capabilities for applications in production as well as preproduction and is optimized for Kubernetes architectures and DevSecOps approaches. This module inherits the automation, AI, scalability, and enterprise-grade robustness of the Dynatrace® Software Intelligence Platform and extends it to modern cloud RASP use cases. Dynatrace customers can launch this module with the flip of a switch, empowering the world’s leading organizations currently using the Dynatrace platform to immediately increase security coverage and precision.;"


def create_log_entry(message=None):
    return {
        'content': message
    }


def test_content_trimmed():
    content_length_limit = 100
    content_length_limit_backup = logs_ingest.main.content_length_limit

    # given
    log_entry = create_log_entry(log_message)
    logs_ingest.main.content_length_limit = content_length_limit

    # when
    try:
        actual_output = parse_record(log_entry, SelfMonitoring(execution_time=datetime.utcnow()))
    finally:
        # restore original value
        logs_ingest.main.content_length_limit = content_length_limit_backup

    # then
    expected_content = "{\"content\": \"WALTHAM, Mass.--(BUSINESS WIRE)-- Software intelligence company Dynatrace (N[TRUNCATED]"
    assert len(actual_output["content"]) == content_length_limit
    assert actual_output["content"] == expected_content


def test_content_with_exact_len_not_trimmed():
    message = "WALTHAM, Mass.--(BUSINESS WIRE)-- Software intelligence company Dynatrace (NYSE: DT)"
    content_length_limit_backup = logs_ingest.main.content_length_limit

    # given
    log_entry = create_log_entry(message)
    logs_ingest.main.content_length_limit = len(json.dumps(log_entry))

    # when
    try:
        actual_output = parse_record(log_entry, SelfMonitoring(execution_time=datetime.utcnow()))
    finally:
        # restore original value
        logs_ingest.main.content_length_limit = content_length_limit_backup

    # then
    expected_output = {
        "cloud.provider": "Azure",
        "severity": "Informational",
        "content": '{"content": "WALTHAM, Mass.--(BUSINESS WIRE)-- Software intelligence company Dynatrace (NYSE: DT)"}'
    }
    assert actual_output == expected_output

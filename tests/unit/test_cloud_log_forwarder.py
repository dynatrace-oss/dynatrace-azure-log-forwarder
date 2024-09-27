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
from datetime import datetime

import logs_ingest.main
from logs_ingest.main import parse_record
from logs_ingest.self_monitoring import SelfMonitoring


def test_log_forwarder_setup():
    cloud_log_forwarder_backup = logs_ingest.main.cloud_log_forwarder
    logs_ingest.main.cloud_log_forwarder = "MyLogForwarderSetup"

    # given
    test_record = {
        "cloud.provider": "Azure",
        "severity": "Informational",
        "content": '{"content": "WALTHAM, Mass.--(BUSINESS WIRE)-- Software intelligence company Dynatrace (NYSE: DT)"}'
    }

    # when
    try:
        actual_output = parse_record(test_record, SelfMonitoring(execution_time=datetime.utcnow()))
    finally:
        logs_ingest.main.cloud_log_forwarder = cloud_log_forwarder_backup

    # then
    assert actual_output['cloud.log_forwarder'] == "MyLogForwarderSetup"

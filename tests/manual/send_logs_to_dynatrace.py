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
import time
from datetime import datetime

from logs_ingest.dynatrace_client import send_logs
# script for testing sending implementation and logs ingest endpoint responses,
# loads dynatrace URL and token from local.settings.json
from logs_ingest.self_monitoring import SelfMonitoring

source_directory = os.path.dirname(os.path.realpath(__file__))
local_settings_json_path = os.path.join(source_directory, "../../local.settings.json")
with open(local_settings_json_path) as local_settings_json_file:
    local_settings_json = json.load(local_settings_json_file)

logs = [
    {
        "cloud.provider": "Azure",
        "timestamp": time.time(),
        "content": "TOO_LONG" * 8192
    } for i in range(1)
]

send_logs(local_settings_json["Values"]["DYNATRACE_URL"], local_settings_json["Values"]["DYNATRACE_ACCESS_KEY"], logs,
          SelfMonitoring(execution_time=datetime.utcnow()))
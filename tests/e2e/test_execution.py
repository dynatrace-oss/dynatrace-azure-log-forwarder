#     Copyright 2021 Dynatrace LLC
#
#     Licensed under the Apache License, Version 2.0 (the "License");
#     you may not use this file except in compliance with the License.
#     You may obtain a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#     Unless required by applicable law or agreed to in writing, software
#     distributed under the License is distributed on an "AS IS" BASIS,
#     WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#     See the License for the specific language governing permissions and
#     limitations under the License.

import os
import time

import requests


def test_environment_vars():
    assert "TARGET_URL" in os.environ
    assert "TARGET_API_TOKEN" in os.environ


def test_logs_on_dynatrace():
    print("Waiting for Logic app to produce logs for 3 min...")
    start_time = round(time.time() * 1000)
    time.sleep(3*60)
    end_time = round(time.time() * 1000)
    print(f"Try to receive logs from Dynatrace in 5 min (timeframe: start time={start_time}, end time={end_time})")
    time.sleep(5*60)

    url = f"{os.environ['TARGET_URL']}/api/v2/logs/search"
    params = {
        'from': start_time,
        'to': end_time,
        'query': 'azure.resource.type="MICROSOFT.LOGIC/WORKFLOWS/RUNS/TRIGGERS" AND content="\\"workflowName\\": \\"logs-forwarding-e2e-logicapp\\"" "\\"resourceGroupName\\": \\"logs-forwarding-e2e-static-resources\\"" "\\"status\\": \\"Running\\""'
    }
    headers = {
        'Authorization': f"Api-Token {os.environ['TARGET_API_TOKEN']}"
    }
    resp = requests.get(url, params=params, headers=headers)

    assert resp.status_code == 200
    # We should receive 3 Logic App logs from Dynatrace with status 'Running' in 3 min time span (Logic App is triggered once per min)
    assert resp.json()['sliceSize'] == 3
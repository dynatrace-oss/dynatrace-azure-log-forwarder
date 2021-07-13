#!/bin/bash
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

echo "Waiting for Logic app to produce logs for 5 min..."
START_TIME=$(date +%s%N | cut -b1-13)
sleep 5m
END_TIME=$(date +%s%N | cut -b1-13)
echo "Try to receive logs from Dynatrace in 5 min (timeframe: start time=$START_TIME, end time=$END_TIME)"
sleep 5m

readonly SEARCH_QUERY='query=azure.resource.type="MICROSOFT.LOGIC/WORKFLOWS/RUNS/TRIGGERS" AND content="\"status\": \"Running\""'
if RESPONSE=$(curl -k -s -G --data-urlencode "$SEARCH_QUERY" --data-urlencode "limit=100" --data-urlencode "from=$START_TIME" --data-urlencode "to=$END_TIME" "$TARGET_URL/api/v2/logs/search" -w "<<HTTP_CODE>>%{http_code}" -H "Accept: application/json; charset=utf-8" -H "Content-Type: application/json; charset=utf-8" -H "Authorization: Api-Token $TARGET_API_TOKEN")
then
  CODE=$(sed -rn 's/.*<<HTTP_CODE>>(.*)$/\1/p' <<< "$RESPONSE")
  RESPONSE=$(sed -r 's/(.*)<<HTTP_CODE>>.*$/\1/' <<< "$RESPONSE")
  if [ "$CODE" -ge 300 ]; then
    echo "Failed to get logs from Dynatrace: $RESPONSE"
    exit 1
  fi
fi

NUMBER_OF_LOGS=$(jq -r '.sliceSize' <<< "$RESPONSE")
# We should receive 5 Logic App logs from Dynatrace with status 'Running' in 5 min time span (Logic App is triggered once per min)
if [ "$NUMBER_OF_LOGS" -eq 5 ]; then
  echo "Successfully received all expected logs from Dynatrace"
  exit 0
elif [ "$NUMBER_OF_LOGS" -gt 0 ] && [ "$NUMBER_OF_LOGS" -ne 5 ]; then
  echo "Failed, received: $NUMBER_OF_LOGS logs from Dynatrace (should be 5)"
  exit 1
else
  echo "Failed, no logs received from Dynatrace"
  exit 1
fi
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

import enum
import json
import os
import urllib
from collections import Counter
from datetime import datetime
from urllib.error import HTTPError
from urllib.request import Request

from . import logging
from logs_ingest.azure_credentials import get_azure_token


class SelfMonitoring:

    def __init__(self, execution_time: datetime):
        self.execution_time = execution_time.replace(microsecond=0)
        self.too_old_records: int = 0
        self.parsing_errors: int = 0
        self.all_requests: int = 0
        self.too_long_content_size = []
        self.dynatrace_connectivities = []
        self.processing_time: int = 0
        self.sending_time: int = 0

    def push_time_series_to_azure(self):
        azure_token = get_azure_token()
        if azure_token:
            self_monitoring_metrics = self.prepare_metric_data()
            for self_monitoring_metric in self_monitoring_metrics:
                serialized_json = json.dumps(self_monitoring_metric)
                encoded_body = serialized_json.encode("UTF-8")
                resource_id = os.environ.get("RESOURCE_ID", None)
                region = os.environ.get("REGION", None)
                if not resource_id or not region:
                    logging.info("Please set RESOURCE_ID and REGION in application settings to send self monitoring metrics to Azure")
                    return
                resource_id = resource_id[1:] if resource_id.startswith('/') else resource_id
                url = f"https://{region}.monitoring.azure.com/{resource_id}/metrics"
                headers = {
                    "Authorization": f"Bearer {azure_token}",
                    "Content-Type": "application/json"
                }
                req = Request(url, encoded_body, headers, method="POST")

                metric_name = self_monitoring_metric.get("data", "").get("baseData", "").get("metric", "")
                try:
                    urllib.request.urlopen(req)
                    logging.debug(f'Successfully sent self monitoring metric ({metric_name}) to Azure')
                except HTTPError as e:
                    logging.exception(
                        f'Failed to push self monitoring metric ({metric_name}) to Azure: {e.code}, reason: {e.reason}", url: {url}')
                except Exception as e:
                    logging.exception(f"Failed to push self monitoring metric ({metric_name}) to Azure. Reason is {type(e).__name__} {e}")

    def prepare_metric_data(self):
        time = self.execution_time.isoformat() + "Z"
        self_monitoring_metrics = []

        if self.too_old_records:
            self_monitoring_metrics.append(self.metric_data(time, "too_old_records", self.too_old_records, count=self.too_old_records))

        if self.parsing_errors:
            self_monitoring_metrics.append(self.metric_data(time, "parsing_errors", self.parsing_errors, count=self.parsing_errors))

        if self.all_requests:
            self_monitoring_metrics.append(self.metric_data(time, "all_requests", self.all_requests, count=self.all_requests))

        self_monitoring_metrics.append(self.metric_data(time, "processing_time", self.processing_time, count=1))
        self_monitoring_metrics.append(self.metric_data(time, "sending_time", self.sending_time, count=1))

        if self.too_long_content_size:
            self_monitoring_metrics.append(
                {
                    "time": time,
                    "data": {
                        "baseData": {
                            "metric": "too_long_content_size",
                            "namespace": "dynatrace_logs_self_monitoring",
                            "series": [
                                {
                                    "min": min(self.too_long_content_size),
                                    "max": max(self.too_long_content_size),
                                    "sum": sum(self.too_long_content_size),
                                    "count": len(self.too_long_content_size)
                                }
                            ]
                        }
                    }
                }
            )

        counter = Counter(self.dynatrace_connectivities)
        for element, count in counter.items():
            if element.name != DynatraceConnectivity.Ok.name:
                self_monitoring_metrics.append(
                    {
                        "time": time,
                        "data": {
                            "baseData": {
                                "metric": "dynatrace_connectivity_failures",
                                "namespace": "dynatrace_logs_self_monitoring",
                                "dimNames": ["connectivity_status"],
                                "series": [
                                    {
                                        "dimValues": [
                                            element.name
                                        ],
                                        "min": count,
                                        "max": count,
                                        "sum": count,
                                        "count": count
                                    }
                                ]
                            }
                        }
                    }
                )

        return self_monitoring_metrics

    @staticmethod
    def metric_data(time, name, value, count):
        return {
            "time": time,
            "data": {
                "baseData": {
                    "metric": name,
                    "namespace": "dynatrace_logs_self_monitoring",
                    "series": [
                        {
                            "min": value,
                            "max": value,
                            "sum": value,
                            "count": count
                        }
                    ]
                }
            }
        }


class DynatraceConnectivity(enum.Enum):
    Ok = 0,
    ExpiredToken = 1,
    WrongToken = 2,
    WrongURL = 3,
    InvalidInput = 4,
    TooManyRequests = 5,
    Other = 6

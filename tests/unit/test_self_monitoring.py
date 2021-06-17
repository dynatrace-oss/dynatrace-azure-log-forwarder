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

from logs_ingest.self_monitoring import SelfMonitoring, DynatraceConnectivity

execution_time=datetime.fromisoformat("2021-02-25T09:06:06")


def test_all_self_monitoring_metrics():
    self_monitoring = SelfMonitoring(execution_time=execution_time)
    self_monitoring.dynatrace_connectivities = [DynatraceConnectivity.Other, DynatraceConnectivity.Other, DynatraceConnectivity.TooManyRequests]
    self_monitoring.too_old_records = 6
    self_monitoring.parsing_errors = 3
    self_monitoring.all_requests = 3
    self_monitoring.processing_time = 0.0878758430480957
    self_monitoring.sending_time = 0.3609178066253662
    self_monitoring.too_long_content_size = [2000, 5000, 6000, 40000]
    self_monitoring.log_ingest_payload_size = 10.123
    self_monitoring.sent_log_entries = 10

    metric_data = self_monitoring.prepare_metric_data()
    assert metric_data == all_expected_metric_data


def test_self_monitoring_metrics_with_zero_values():
    self_monitoring = SelfMonitoring(execution_time=execution_time)
    self_monitoring.dynatrace_connectivities = [DynatraceConnectivity.Ok]
    self_monitoring.too_old_records = 0
    self_monitoring.parsing_errors = 0
    self_monitoring.all_requests = 1
    self_monitoring.processing_time = 0.0878758430480957
    self_monitoring.sending_time = 0.3609178066253662
    self_monitoring.too_long_content_size = []

    metric_data = self_monitoring.prepare_metric_data()
    assert metric_data == expected_metric_data_without_zeros_metrics


all_expected_metric_data = [
    {
        "time": "2021-02-25T09:06:06Z",
        "data": {
            "baseData": {
                "metric": "too_old_records",
                "namespace": "dynatrace_logs_self_monitoring",
                "series": [
                    {
                        "min": 6,
                        "max": 6,
                        "sum": 6,
                        "count": 6
                    }
                ]
            }
        }
    },
    {
        "time": "2021-02-25T09:06:06Z",
        "data": {
            "baseData": {
                "metric": "parsing_errors",
                "namespace": "dynatrace_logs_self_monitoring",
                "series": [
                    {
                        "min": 3,
                        "max": 3,
                        "sum": 3,
                        "count": 3
                    }
                ]
            }
        }
    },
    {
        "time": "2021-02-25T09:06:06Z",
        "data": {
            "baseData": {
                "metric": "all_requests",
                "namespace": "dynatrace_logs_self_monitoring",
                "series": [
                    {
                        "min": 3,
                        "max": 3,
                        "sum": 3,
                        "count": 3
                    }
                ]
            }
        }
    },
    {
        "time": "2021-02-25T09:06:06Z",
        "data": {
            "baseData": {
                "metric": "sent_log_entries",
                "namespace": "dynatrace_logs_self_monitoring",
                "series": [
                    {
                        "min": 10,
                        "max": 10,
                        "sum": 10,
                        "count": 10
                    }
                ]
            }
        }
    },
    {
        "time": "2021-02-25T09:06:06Z",
        "data": {
            "baseData": {
                "metric": "log_ingest_payload_size",
                "namespace": "dynatrace_logs_self_monitoring",
                "series": [
                    {
                        "min": 10.123,
                        "max": 10.123,
                        "sum": 10.123,
                        "count": 1
                    }
                ]
            }
        }
    },
    {
        "time": "2021-02-25T09:06:06Z",
        "data": {
            "baseData": {
                "metric": "processing_time",
                "namespace": "dynatrace_logs_self_monitoring",
                "series": [
                    {
                        "min": 0.0878758430480957,
                        "max": 0.0878758430480957,
                        "sum": 0.0878758430480957,
                        "count": 1
                    }
                ]
            }
        }
    },
    {
        "time": "2021-02-25T09:06:06Z",
        "data": {
            "baseData": {
                "metric": "sending_time",
                "namespace": "dynatrace_logs_self_monitoring",
                "series": [
                    {
                        "min": 0.3609178066253662,
                        "max": 0.3609178066253662,
                        "sum": 0.3609178066253662,
                        "count": 1
                    }
                ]
            }
        }
    },
    {
        "time": "2021-02-25T09:06:06Z",
        "data": {
            "baseData": {
                "metric": "too_long_content_size",
                "namespace": "dynatrace_logs_self_monitoring",
                "series": [
                    {
                        "min": 2000,
                        "max": 40000,
                        "sum": 53000,
                        "count": 4
                    }
                ]
            }
        }
    },
    {
        "time": "2021-02-25T09:06:06Z",
        "data": {
            "baseData": {
                "metric": "dynatrace_connectivity_failures",
                "namespace": "dynatrace_logs_self_monitoring",
                "dimNames": ["connectivity_status"],
                "series": [
                    {
                        "dimValues": [
                            DynatraceConnectivity.Other.name
                        ],
                        "min": 2,
                        "max": 2,
                        "sum": 2,
                        "count": 2
                    }
                ]
            }
        }
    },
    {
        "time": "2021-02-25T09:06:06Z",
        "data": {
            "baseData": {
                "metric": "dynatrace_connectivity_failures",
                "namespace": "dynatrace_logs_self_monitoring",
                "dimNames": ["connectivity_status"],
                "series": [
                    {
                        "dimValues": [
                            DynatraceConnectivity.TooManyRequests.name
                        ],
                        "min": 1,
                        "max": 1,
                        "sum": 1,
                        "count": 1
                    }
                ]
            }
        }
    }
]

expected_metric_data_without_zeros_metrics = [
    {
        "time": "2021-02-25T09:06:06Z",
        "data": {
            "baseData": {
                "metric": "all_requests",
                "namespace": "dynatrace_logs_self_monitoring",
                "series": [
                    {
                        "min": 1,
                        "max": 1,
                        "sum": 1,
                        "count": 1
                    }
                ]
            }
        }
    },
    {
        "time": "2021-02-25T09:06:06Z",
        "data": {
            "baseData": {
                "metric": "processing_time",
                "namespace": "dynatrace_logs_self_monitoring",
                "series": [
                    {
                        "min": 0.0878758430480957,
                        "max": 0.0878758430480957,
                        "sum": 0.0878758430480957,
                        "count": 1
                    }
                ]
            }
        }
    },
    {
        "time": "2021-02-25T09:06:06Z",
        "data": {
            "baseData": {
                "metric": "sending_time",
                "namespace": "dynatrace_logs_self_monitoring",
                "series": [
                    {
                        "min": 0.3609178066253662,
                        "max": 0.3609178066253662,
                        "sum": 0.3609178066253662,
                        "count": 1
                    }
                ]
            }
        }
    }
]
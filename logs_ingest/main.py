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
from datetime import datetime, timezone
from typing import List, Dict

import azure.functions as func
from dateutil import parser

from . import logging
from .dynatrace_client import send_logs
from .mapping import extract_resource_id_attributes, extract_severity, \
    azure_properties_names
from .metadata_engine import MetadataEngine
from .monitored_entity_id import infer_monitored_entity_id
from .self_monitoring import SelfMonitoring
from .utils import get_int_environment_value

record_age_limit = get_int_environment_value("DYNATRACE_LOG_INGEST_MAX_RECORD_AGE", 3600 * 24)

DYNATRACE_URL = "DYNATRACE_URL"
DYNATRACE_ACCESS_KEY = "DYNATRACE_ACCESS_KEY"

metadata_engine = MetadataEngine()


def main(events: List[func.EventHubEvent]):
    self_monitoring = SelfMonitoring(execution_time=datetime.utcnow())
    process_logs(events, self_monitoring)


def process_logs(events: List[func.EventHubEvent], self_monitoring: SelfMonitoring):
    try:
        if DYNATRACE_URL not in os.environ.keys() or DYNATRACE_ACCESS_KEY not in os.environ.keys():
            raise Exception(f"Please set {DYNATRACE_URL} and {DYNATRACE_ACCESS_KEY} in application settings")

        dt_payload = []
        start_time = time.time()
        for event in events:
            timestamp = event.enqueued_time.replace(microsecond=0).replace(tzinfo=None).isoformat() + 'Z' if event.enqueued_time else None
            if not is_too_old(timestamp, self_monitoring, "event"):
                event_body = event.get_body()
                event_json = json.loads(event_body.decode('utf-8'))
                records = event_json.get("records", [])
                for record in records:
                    try:
                        process_record(dt_payload, record, self_monitoring)
                    except Exception:
                        self_monitoring.parsing_errors += 1
                        logging.exception(f"Failed to parse log record")

        self_monitoring.processing_time = time.time() - start_time
        logging.info(f"Successfully parsed {len(dt_payload)} log records")
        if dt_payload:
            send_logs(os.environ[DYNATRACE_URL], os.environ[DYNATRACE_ACCESS_KEY], dt_payload, self_monitoring)
    except Exception as e:
        logging.exception("Failed to process logs")
        raise e
    finally:
        self_monitoring_enabled = os.environ.get("SELF_MONITORING_ENABLED", "False") in ["True", "true"]
        if self_monitoring_enabled:
            self_monitoring.push_time_series_to_azure()


def process_record(dt_payload: List[Dict], record: Dict, self_monitoring: SelfMonitoring):
    deserialize_properties(record)
    parsed_record = parse_record(record, self_monitoring)
    timestamp = parsed_record.get("timestamp", None)
    if is_too_old(timestamp, self_monitoring, "record"):
        return
    dt_payload.append(parsed_record)


def is_too_old(timestamp: str, self_monitoring: SelfMonitoring, log_part: str):
    if timestamp:
        try:
            date = parser.parse(timestamp)
            # LINT won't accept any log line older than one day, 60 seconds of margin to send
            if (datetime.now(timezone.utc) - date).total_seconds() > (record_age_limit - 60):
                logging.info(f"Skipping too old {log_part} with timestamp '{timestamp}'")
                self_monitoring.too_old_records += 1
                return True
        except Exception:
            # Not much we can do when we can't parse the timestamp
            logging.debug(f"Failed to parse timestamp {timestamp}")
            self_monitoring.parsing_errors += 1
            pass
    return False


def deserialize_properties(record: Dict):
    properties_name = next((properties for properties in azure_properties_names if properties in record.keys()), "")
    properties = record.get(properties_name, {})
    if properties and type(properties) is str:
        record["properties"] = json.loads(properties)


def parse_record(record: Dict, self_monitoring: SelfMonitoring):
    parsed_record = {
        "cloud.provider": "Azure"
    }
    extract_severity(record, parsed_record)

    if "resourceId" in record:
        extract_resource_id_attributes(parsed_record, record["resourceId"])

    metadata_engine.apply(record, parsed_record)
    category = record.get("category", "").lower()
    infer_monitored_entity_id(category, parsed_record)

    content = parsed_record.get("content", None)
    content_length_limit = get_int_environment_value("DYNATRACE_LOG_INGEST_CONTENT_MAX_LENGTH", 8192)
    if content:
        if not isinstance(content, str):
            parsed_record["content"] = json.dumps(parsed_record["content"])
        if len(parsed_record["content"]) >= content_length_limit:
            self_monitoring.too_long_content_size.append(len(parsed_record["content"]))
            parsed_record["content"] = parsed_record["content"][:content_length_limit]

    return parsed_record

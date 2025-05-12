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
from json import JSONDecodeError
from typing import List, Dict, Optional
import re
import asyncio

import azure.functions as func
from dateutil import parser

from . import logging
from .dynatrace_client import send_logs
from .filtering import LogFilter
from .mapping import extract_resource_id_attributes, extract_severity, azure_properties_names
from .metadata_engine import MetadataEngine
from .monitored_entity_id import infer_monitored_entity_id
from .self_monitoring import SelfMonitoring
from .util import util_misc
from .util.util_misc import get_int_environment_value

record_age_limit = get_int_environment_value("DYNATRACE_LOG_INGEST_MAX_RECORD_AGE", 3600 * 24)
attribute_value_length_limit = get_int_environment_value("DYNATRACE_LOG_INGEST_ATTRIBUTE_VALUE_MAX_LENGTH", 250)
content_length_limit = get_int_environment_value("DYNATRACE_LOG_INGEST_CONTENT_MAX_LENGTH", 8192)
cloud_log_forwarder = os.environ.get("RESOURCE_ID", "")  # Function app id

DYNATRACE_URL = "DYNATRACE_URL"
DYNATRACE_ACCESS_KEY = "DYNATRACE_ACCESS_KEY"
DYNATRACE_LOG_INGEST_CONTENT_MARK_TRIMMED = "[TRUNCATED]"

metadata_engine = MetadataEngine()
log_filter = LogFilter()


def main(events: List[func.EventHubEvent]):
    self_monitoring = SelfMonitoring(execution_time=datetime.utcnow())
    process_logs(events, self_monitoring)


def process_logs(events: List[func.EventHubEvent], self_monitoring: SelfMonitoring):
    try:
        verify_dt_access_params_provided()
        logging.throttling_counter.reset_throttling_counter()

        start_time = time.perf_counter()

        logs_to_be_sent_to_dt = extract_logs(events, self_monitoring)

        self_monitoring.processing_time = time.perf_counter() - start_time
        logging.info(f"Successfully parsed {len(logs_to_be_sent_to_dt)} log records")

        if logs_to_be_sent_to_dt:
            asyncio.run(send_logs(os.environ[DYNATRACE_URL], os.environ[DYNATRACE_ACCESS_KEY], logs_to_be_sent_to_dt, self_monitoring))
    except Exception as e:
        logging.exception("Failed to process logs", "log-processing-exception")
        raise e
    finally:
        self_monitoring_enabled = os.environ.get("SELF_MONITORING_ENABLED", "False") in ["True", "true"]
        self_monitoring.log_self_monitoring_data()
        if self_monitoring_enabled:
            self_monitoring.push_time_series_to_azure()


def verify_dt_access_params_provided():
    if DYNATRACE_URL not in os.environ.keys() or DYNATRACE_ACCESS_KEY not in os.environ.keys():
        raise Exception(f"Please set {DYNATRACE_URL} and {DYNATRACE_ACCESS_KEY} in application settings")


def extract_logs(events: List[func.EventHubEvent], self_monitoring: SelfMonitoring):
    logs_to_be_sent_to_dt = []
    for event in events:
        timestamp = event.enqueued_time.replace(microsecond=0).replace(tzinfo=None).isoformat() + 'Z' if event.enqueued_time else None
        if is_too_old(timestamp, self_monitoring, "event"):
            continue

        event_body = event.get_body().decode('utf-8')
        event_json = parse_to_json(event_body)
        if event_json:
            records = event_json.get("records", [])
            for record in records:
                try:
                    extracted_record = extract_dt_record(record, self_monitoring)
                    if extracted_record:
                        logs_to_be_sent_to_dt.append(extracted_record)
                except JSONDecodeError as json_e:
                    self_monitoring.parsing_errors += 1
                    logging.exception(
                        f"Failed to decode JSON for the record (base64 applied for safety!): {util_misc.to_base64_text(str(record))}. Exception: {json_e}",
                        "log-record-parsing-jsondecode-exception")
                except Exception as e:
                    self_monitoring.parsing_errors += 1
                    logging.exception(
                        f"Failed to parse log record (base64 applied for safety!): {util_misc.to_base64_text(str(record))}. Exception: {e}",
                        "log-record-parsing-exception")
    return logs_to_be_sent_to_dt


def extract_dt_record(record: Dict, self_monitoring: SelfMonitoring) -> Optional[Dict]:
    deserialize_properties(record)

    parsed_record = parse_record(record, self_monitoring)
    if not parsed_record:
        return None

    timestamp = parsed_record.get("timestamp", None)
    if is_too_old(timestamp, self_monitoring, "record"):
        return None

    return parsed_record


def is_too_old(timestamp: str, self_monitoring: SelfMonitoring, log_part: str):
    if timestamp:
        try:
            date = parser.parse(timestamp)
            if not date.tzinfo:
                date=date.replace(tzinfo=timezone.utc)
            # Logs Ingest API won't accept any log line older than one day, 60 seconds of margin to send
            if (datetime.now(timezone.utc) - date).total_seconds() > (record_age_limit - 60):
                logging.info(f"Skipping too old {log_part} with timestamp '{timestamp}'")
                self_monitoring.too_old_records += 1
                return True
        except Exception:
            # Not much we can do when we can't parse the timestamp
            logging.exception(f"Failed to parse timestamp {timestamp}", "timestamp-parsing-exception")
            self_monitoring.parsing_errors += 1
    return False


def deserialize_properties(record: Dict):
    properties_name = next((properties for properties in azure_properties_names if properties in record.keys()), "")
    properties = record.get(properties_name, {})
    if properties and isinstance(properties, str):
        record["properties"] = parse_to_json(properties)


def parse_record(record: Dict, self_monitoring: SelfMonitoring):
    parsed_record = {
        "cloud.provider": "Azure"
    }
    extract_severity(record, parsed_record)
    extract_cloud_log_forwarder(parsed_record)

    if "resourceId" in record:
        extract_resource_id_attributes(parsed_record, record["resourceId"])

    metadata_engine.apply(record, parsed_record)
    convert_date_format(parsed_record)
    category = record.get("category", "").lower()
    infer_monitored_entity_id(category, parsed_record)

    for attribute_key, attribute_value in parsed_record.items():
        if attribute_key not in ["content", "severity", "timestamp"] and attribute_value:
            string_attribute_value = attribute_value
            if not isinstance(attribute_value, str):
                string_attribute_value = str(attribute_value)
            parsed_record[attribute_key] = string_attribute_value[: attribute_value_length_limit]

    content = parsed_record.get("content", None)

    if log_filter.should_filter_out_record(parsed_record):
        return None

    if content:
        if not isinstance(content, str):
            parsed_record["content"] = json.dumps(parsed_record["content"])
        if len(parsed_record["content"]) > content_length_limit:
            self_monitoring.too_long_content_size.append(len(parsed_record["content"]))
            trimmed_len = content_length_limit - len(DYNATRACE_LOG_INGEST_CONTENT_MARK_TRIMMED)
            parsed_record["content"] = parsed_record["content"][
                                       :trimmed_len] + DYNATRACE_LOG_INGEST_CONTENT_MARK_TRIMMED
    return parsed_record


def extract_cloud_log_forwarder(parsed_record):
    if cloud_log_forwarder:
        parsed_record["cloud.log_forwarder"] = cloud_log_forwarder


def parse_to_json(text):
    try:
        event_json = json.loads(text)
    except Exception:
        try:
            event_json = json.loads(text.replace("\n", ""), strict=False)
        except Exception:
            try:
                event_json = json.loads(text.replace("\'", "\""))
            except Exception:
                try:
                    event_json = json.loads(text.replace('\\\'', '').replace("\'", "\""), strict=False)
                except Exception:
                    logging.exception(
                        f"Failed to decode JSON for the event (base64 applied for safety!): {util_misc.to_base64_text(str(text))}.",
                        "log-record-parsing-jsondecode-exception")
                    return None
    return event_json


def convert_date_format(record):
    timestamp = record.get("timestamp", None)
    if timestamp and re.findall('[0-9]{2}/[0-9]{2}/[0-9]{4} [0-9]{2}:[0-9]{2}:[0-9]{2}', timestamp):
        record["timestamp"] = str(datetime.strptime(timestamp, '%m/%d/%Y %H:%M:%S').isoformat()) + "Z"

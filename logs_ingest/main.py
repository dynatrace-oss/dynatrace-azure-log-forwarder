import asyncio
import json
import os
import time
from datetime import datetime, timezone
from json import JSONDecodeError
from typing import List, Dict, Optional
import re
import multiprocessing

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

        asyncio.run(extract_and_send_logs(events, self_monitoring))

        self_monitoring.processing_time = time.perf_counter() - start_time
    except Exception as e:
        logging.exception("Failed to process logs", "log-processing-exception")
        raise e
    finally:
        self_monitoring_enabled = os.environ.get("SELF_MONITORING_ENABLED", "False") in ["True", "true"]
        self_monitoring.log_self_monitoring_data()
        if self_monitoring_enabled:
            self_monitoring.push_time_series_to_azure()


async def extract_and_send_logs(events: List[func.EventHubEvent], self_monitoring: SelfMonitoring):
    logs_to_be_sent_to_dt = []

    async with multiprocessing.Pool() as pool:
        extracted_logs = await asyncio.gather(
            *[extract_log(event, self_monitoring, pool) for event in events]
        )
        logs_to_be_sent_to_dt = [log for log in extracted_logs if log is not None]

    logging.info(f"Successfully parsed {len(logs_to_be_sent_to_dt)} log records")

    if logs_to_be_sent_to_dt:
        await send_logs(os.environ[DYNATRACE_URL], os.environ[DYNATRACE_ACCESS_KEY], logs_to_be_sent_to_dt, self_monitoring)


def extract_log(event: func.EventHubEvent, self_monitoring: SelfMonitoring, pool: multiprocessing.Pool):
    event_body = event.get_body().decode('utf-8')
    event_json = parse_to_json(event_body)
    records = event_json.get("records", [])

    extracted_logs = pool.map(
        lambda record: extract_dt_record(record, self_monitoring),
        records
    )

    return next((log for log in extracted_logs if log is not None), None)


def verify_dt_access_params_provided():
    if DYNATRACE_URL not in os.environ.keys() or DYNATRACE_ACCESS_KEY not in os.environ.keys():
        raise Exception(f"Please set {DYNATRACE_URL} and {DYNATRACE_ACCESS_KEY} in application settings")


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
            # LINT won't accept any log line older than one day, 60 seconds of margin to send
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
    record["cloud.provider"] = "Azure"
    extract_severity(record, record)
    extract_cloud_log_forwarder(record)

    if "resourceId" in record:
        extract_resource_id_attributes(record, record["resourceId"])

    if log_filter.should_filter_out_record(record):
        return None

    metadata_engine.apply(record, record)
    convert_date_format(record)
    category = record.get("category", "").lower()
    infer_monitored_entity_id(category, record)

    for attribute_key, attribute_value in record.items():
        if attribute_key not in ["content", "severity", "timestamp"] and attribute_value:
            string_attribute_value = attribute_value
            if not isinstance(attribute_value, str):
                string_attribute_value = str(attribute_value)
            record[attribute_key] = string_attribute_value[: attribute_value_length_limit]

    content = record.get("content", "")
    if len(content) > content_length_limit:
        record["content"] = f"{content[: content_length_limit - len(DYNATRACE_LOG_INGEST_CONTENT_MARK_TRIMMED)]}{DYNATRACE_LOG_INGEST_CONTENT_MARK_TRIMMED}"

    return record


def extract_cloud_log_forwarder(record: Dict):
    if not record.get("cloud.log.forwarder"):
        record["cloud.log.forwarder"] = cloud_log_forwarder


def convert_date_format(record: Dict):
    timestamp = record.get("timestamp", "")
    if isinstance(timestamp, str):
        try:
            parsed_timestamp = parser.parse(timestamp)
            formatted_timestamp = parsed_timestamp.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
            record["timestamp"] = formatted_timestamp
        except Exception:
            logging.exception(f"Failed to parse timestamp {timestamp}", "timestamp-parsing-exception")
            record["timestamp"] = timestamp


def parse_to_json(json_str: str) -> Optional[Dict]:
    try:
        return json.loads(json_str)
    except JSONDecodeError:
        logging.exception("Failed to parse JSON string", "json-parsing-exception")
        return None

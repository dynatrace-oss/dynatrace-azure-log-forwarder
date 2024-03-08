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

import gzip
import json
import os
import ssl
import time
import aiohttp
import asyncio

from typing import List, Dict, Tuple, NamedTuple
from urllib.error import HTTPError
from urllib.parse import urlparse

from logs_ingest.self_monitoring import SelfMonitoring, DynatraceConnectivity
from .util.util_misc import get_int_environment_value
from . import logging

should_verify_ssl_certificate = os.environ.get("REQUIRE_VALID_CERTIFICATE", "True") in ["True", "true"]

number_of_concurrent_send_calls = get_int_environment_value("NUMBER_OF_CONCURRENT_SEND_CALLS", 2)
ssl_context = ssl.create_default_context()
if not should_verify_ssl_certificate:
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE


class LogBatch(NamedTuple):
    serialized_batch: str
    number_of_logs_in_batch: int


async def send_logs(dynatrace_url: str, dynatrace_token: str, logs: List[Dict], self_monitoring: SelfMonitoring):
    start_time = time.perf_counter()
    log_ingest_url = urlparse(dynatrace_url.rstrip("/") + "/api/v2/logs/ingest").geturl()
    batches = prepare_serialized_batches(logs)
    number_of_http_errors = 0

    semaphore = asyncio.Semaphore(number_of_concurrent_send_calls)
    async with aiohttp.ClientSession() as session:  # Create the session once
        async def process_batch(batch: LogBatch):
            nonlocal number_of_http_errors
            async with semaphore:
                encoded_body_bytes = batch.serialized_batch.encode("UTF-8")
                display_payload_size = round((len(encoded_body_bytes) / 1024), 3)
                logging.info(f'Log ingest payload size: {display_payload_size} kB')
                sent_logs_successfully = False
                try:
                    sent_logs_successfully = await _send_logs(session, dynatrace_token, encoded_body_bytes,
                                                              log_ingest_url, self_monitoring)
                except HTTPError as e:
                    raise e
                except Exception as e:
                    self_monitoring.dynatrace_connectivities.append(DynatraceConnectivity.Other)
                    number_of_http_errors += 1
                    logging.exception("Failed to ingest logs", "ingesting-logs-exception")
                    # # all http requests failed and this is the last batch, raise this exception to trigger retry
                    if number_of_http_errors == len(batches):
                        raise e
                finally:
                    self_monitoring.sending_time = time.perf_counter() - start_time
                    if sent_logs_successfully:
                        self_monitoring.log_ingest_payload_size += display_payload_size
                        self_monitoring.sent_log_entries += batch.number_of_logs_in_batch

        await asyncio.gather(*[process_batch(batch) for batch in batches])


async def _send_logs(session, dynatrace_token, encoded_body_bytes, log_ingest_url, self_monitoring):
    self_monitoring.all_requests += 1
    is_request_successful = False
    headers = {
        "Authorization": f"Api-Token {dynatrace_token}",
        "Content-Type": "application/json; charset=utf-8",
        "Content-Encoding": "gzip"
    }

    encoded_body_bytes = gzip.compress(encoded_body_bytes, compresslevel=6)
    compressed_size_kb = len(encoded_body_bytes) / 1024.0

    logging.info(f'Log ingest payload size compressed: {compressed_size_kb} kB')

    status, reason, response = await _perform_http_request(
        session,
        method="POST",
        url=log_ingest_url,
        headers=headers,
        encoded_body_bytes=encoded_body_bytes,
    )
    if status > 299:
        logging.error(
            f'Log ingest error: {status}, reason: {reason}, url: {log_ingest_url}, body: "{response}"',
            "log-ingest-error",
        )
        if status == 400:
            self_monitoring.dynatrace_connectivities.append(DynatraceConnectivity.InvalidInput)
        elif status == 401:
            self_monitoring.dynatrace_connectivities.append(DynatraceConnectivity.ExpiredToken)
        elif status == 403:
            self_monitoring.dynatrace_connectivities.append(DynatraceConnectivity.WrongToken)
        elif status in (404, 405):
            self_monitoring.dynatrace_connectivities.append(DynatraceConnectivity.WrongURL)
        elif status in (413, 429):
            self_monitoring.dynatrace_connectivities.append(DynatraceConnectivity.TooManyRequests)
            raise HTTPError(log_ingest_url, 429, "Dynatrace throttling response", "", "")
        elif status == 500:
            self_monitoring.dynatrace_connectivities.append(DynatraceConnectivity.Other)
            raise HTTPError(log_ingest_url, 500, "Dynatrace server error", "", "")
    else:
        is_request_successful = True
        self_monitoring.dynatrace_connectivities.append(DynatraceConnectivity.Ok)
        logging.info("Log ingest payload pushed successfully")
    return is_request_successful



async def _perform_http_request(session, method, url, encoded_body_bytes, headers) -> Tuple[int, str, str]:
    timeout = aiohttp.ClientTimeout(total=10)
    async with session.request(method, url, headers=headers, data=encoded_body_bytes, ssl=ssl_context, timeout=timeout) as response:
        response_text = await response.text()
        return response.status, response.reason, response_text


# Heavily based on AWS log forwarder batching implementation
def prepare_serialized_batches(logs: List[Dict]) -> List[LogBatch]:
    request_body_max_size = get_int_environment_value("DYNATRACE_LOG_INGEST_REQUEST_MAX_SIZE", 4718592)
    request_max_events = get_int_environment_value("DYNATRACE_LOG_INGEST_REQUEST_MAX_EVENTS", 5000)
    log_entry_max_size = request_body_max_size - 2  # account for braces

    batches: List[LogBatch] = []

    logs_for_next_batch: List[str] = []
    logs_for_next_batch_total_len = 0
    logs_for_next_batch_events_count = 0

    log_entries = 0
    for log_entry in logs:
        new_batch_len = logs_for_next_batch_total_len + 2 + len(logs_for_next_batch) - 1  # add bracket length (2) and commas for each entry but last one.

        next_entry_serialized = json.dumps(log_entry)

        next_entry_size = len(next_entry_serialized.encode("UTF-8"))
        if next_entry_size > log_entry_max_size:
            # shouldn't happen as we are already truncating the content field, but just for safety
            logging.info(f"Dropping entry, as its size is {next_entry_size}, bigger than max entry size: {log_entry_max_size}")

        batch_length_if_added_entry = new_batch_len + 1 + len(next_entry_serialized)  # +1 is for comma

        if batch_length_if_added_entry > request_body_max_size or logs_for_next_batch_events_count >= request_max_events:
            # would overflow limit, close batch and prepare new
            batch = LogBatch("[" + ",".join(logs_for_next_batch) + "]", log_entries)
            batches.append(batch)
            log_entries = 0

            logs_for_next_batch = []
            logs_for_next_batch_total_len = 0
            logs_for_next_batch_events_count = 0

        logs_for_next_batch.append(next_entry_serialized)
        log_entries += 1
        logs_for_next_batch_total_len += next_entry_size
        logs_for_next_batch_events_count += 1

    if len(logs_for_next_batch) >= 1:
        # finalize the last batch
        batch = LogBatch("[" + ",".join(logs_for_next_batch) + "]", log_entries)
        batches.append(batch)

    return batches
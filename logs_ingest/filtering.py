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
import fnmatch
import os
import re
from typing import Dict, Set

from logs_ingest import logging
from logs_ingest.mapping import severity_to_log_level_dict, log_level_to_severity_dict, RESOURCE_TYPE_ATTRIBUTE, \
    RESOURCE_ID_ATTRIBUTE

GLOBAL = "global"
FILTER_NAMES_PREFIXES = ["filter.resource_type.min_log_level.", "filter.resource_type.contains_pattern.",
                         "filter.resource_id.min_log_level.","filter.resource_id.contains_pattern."]


class LogFilter:
    def __init__(self):
        self._filter_config: str = os.environ.get("FILTER_CONFIG", "")
        logging.info(f"Filter_config: {self._filter_config}")
        filter_config_pattern = re.compile(r'([^;\s].+?)=([^;]*)')
        self._filters_tuples = filter_config_pattern.findall(self._filter_config)
        self._filters_tuples = [modified_filter_tuple for filter_tuple in self._filters_tuples
                                if (modified_filter_tuple := self._prepare_filters_tuples(filter_tuple)) is not None]
        self.filters_dict = self._prepare_filters_dict()

    @staticmethod
    def _prepare_filters_tuples(filter_tuple):
        filter_name = filter_tuple[0].strip().casefold()
        value = filter_tuple[1].strip()
        if filter_name.startswith("filter.global."):
            key = GLOBAL
            return key, (filter_name, value)

        for prefix in FILTER_NAMES_PREFIXES:
            if filter_name.startswith(prefix):
                key = filter_name.split(prefix)[1].casefold()
                if key:
                    return key, (filter_name, value)

        return None

    def _prepare_filters_dict(self) -> Dict:
        grouped_filters = self._group_filters()
        filters_to_apply_dict = {}
        parsed_filters_to_log = []
        for k, filter_name_value_dict in grouped_filters.items():
            filters_to_apply = []
            for filter_name, filter_value in filter_name_value_dict.items():
                if "min_log_level" in filter_name:
                    log_levels = self._get_log_levels(filter_value)
                    if log_levels:
                        log_level_filter = self._create_log_level_filter(log_levels)
                        filters_to_apply.append(log_level_filter)
                        parsed_filters_to_log.append(filter_name)
                if "contains_pattern" in filter_name:
                    if isinstance(filter_value, list):
                        for filter_pattern in filter_value:
                            contains_pattern_filter = (
                                self._create_contains_pattern_filter(filter_pattern)
                            )
                            filters_to_apply.append(contains_pattern_filter)
                            parsed_filters_to_log.append(filter_name)
                    if not isinstance(filter_value, list):
                        contains_pattern_filter = self._create_contains_pattern_filter(
                            filter_value
                        )
                        filters_to_apply.append(contains_pattern_filter)
                        parsed_filters_to_log.append(filter_name)
            if filters_to_apply:
                filters_to_apply_dict[k] = filters_to_apply
        logging.info(f"Successfully parsed filters: {parsed_filters_to_log}")
        return filters_to_apply_dict

    def _group_filters(self) -> Dict:
        filters_dict = {}
        for key, filter_name_value in self._filters_tuples:
            if "|" in filter_name_value[1]:
                filter_patterns = filter_name_value[1].split("|")
                if filter_patterns:
                    filter_patterns = [
                        f"{pattern.strip()}" for pattern in filter_patterns
                    ]
                    filters_dict.setdefault(key, {}).update(
                        {filter_name_value[0]: filter_patterns}
                    )
                    continue

            filters_dict.setdefault(key, {}).update(
                {filter_name_value[0]: filter_name_value[1]}
            )

        return filters_dict

    @staticmethod
    def _create_log_level_filter(log_levels: Set):
        return lambda severity, record: severity in log_levels

    @staticmethod
    def _create_contains_pattern_filter(pattern: str):
        return lambda severity, record: fnmatch.fnmatch(record, pattern)

    def should_filter_out_record(self, parsed_record: Dict) -> bool:
        if not self.filters_dict:
            return False

        severity = parsed_record.get("severity", "")
        resource_id = parsed_record.get(RESOURCE_ID_ATTRIBUTE, "").casefold()
        resource_type = parsed_record.get(RESOURCE_TYPE_ATTRIBUTE, "").casefold()
        content = parsed_record.get("content", "")

        log_filters = self._get_filters(resource_id, resource_type)

        filter_patterns = []

        for log_filter in log_filters:
            if 'contains_pattern' in str(log_filter):
                filter_patterns.append(log_filter)

        pipe_separated_filters_result = True

        if len(filter_patterns) > 1:
            log_filters = set(log_filters) - set(filter_patterns)
            pipe_separated_filters_result = any(log_filter(severity, str(content)) for log_filter in filter_patterns)

        return (not all(log_filter(severity, str(content)) for log_filter in log_filters)
                or not pipe_separated_filters_result)



    def _get_filters(self, resource_id, resource_type):
        filters = self.filters_dict.get(resource_id, [])
        if not filters:
            filters = self.filters_dict.get(resource_type, [])
        if not filters:
            filters = self.filters_dict.get(GLOBAL, [])
        return filters

    @staticmethod
    def _get_log_levels(min_log_level) -> Set:
        log_level_set = set()
        if min_log_level.isdigit():
            min_log_level = int(min_log_level)
            log_level_set = {severity for log_level_digit, severity in log_level_to_severity_dict.items()
                             if log_level_digit <= min_log_level}
        else:
            min_log_level = min_log_level.capitalize()
            min_log_level_digit = severity_to_log_level_dict.get(min_log_level, None)
            if min_log_level_digit:
                log_level_set = {severity for log_level_digit, severity in log_level_to_severity_dict.items()
                                 if log_level_digit <= min_log_level_digit}
            else:
                logging.warning(f"Incorrect log level in FILTER_CONFIG: {min_log_level}.",
                                "incorrect-log-level-warning")
        return log_level_set




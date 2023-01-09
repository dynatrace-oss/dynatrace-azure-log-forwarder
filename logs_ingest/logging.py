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

import logging
import os

LOG_THROTTLING_LIMIT_PER_CALLER = 10

script_directory = os.path.dirname(os.path.realpath(__file__))
version_file_path = os.path.join(script_directory, "version.txt")
with open(version_file_path) as version_file:
    _version = version_file.readline()
    _version_tag = f"[{_version}] "


class ThrottlingCounter:
    counter = dict()

    def reset_throttling_counter(self):
        # the state has to be cleared for each function execution because consecutive calls might share same
        # execution environment (in such case static variables are not being initialized again!)
        self.counter = dict()

    def check_if_caller_exceeded_limit(self, caller) -> bool:
        log_calls_performed = self.counter.get(caller, 0)
        log_calls_left = LOG_THROTTLING_LIMIT_PER_CALLER - log_calls_performed

        if log_calls_left == 0:
            self.counter[caller] = log_calls_performed + 1
            logging.warning(_version_tag + f"Logging calls from caller '{caller}' exceeded the throttling limit of"
                                           f" {LOG_THROTTLING_LIMIT_PER_CALLER}. Further logs from this caller will be discarded")

        caller_exceeded_limit = log_calls_left <= 0
        if not caller_exceeded_limit:
            self.counter[caller] = log_calls_performed + 1

        return caller_exceeded_limit


throttling_counter = ThrottlingCounter()


def exception(msg, caller: str, *args, **kwargs):
    if throttling_counter.check_if_caller_exceeded_limit(caller):
        return
    logging.exception(_version_tag + msg, *args, **kwargs)


def error(msg, caller: str, *args, **kwargs):
    if throttling_counter.check_if_caller_exceeded_limit(caller):
        return
    logging.error(_version_tag + msg, *args, **kwargs)


def warning(msg, caller: str, *args, **kwargs):
    if throttling_counter.check_if_caller_exceeded_limit(caller):
        return
    logging.warning(_version_tag + msg, *args, **kwargs)


def info(msg, *args, **kwargs):
    logging.info(_version_tag + msg, *args, **kwargs)


def debug(msg, *args, **kwargs):
    logging.debug(_version_tag + msg, *args, **kwargs)



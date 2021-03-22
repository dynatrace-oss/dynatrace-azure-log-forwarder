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

script_directory = os.path.dirname(os.path.realpath(__file__))
version_file_path = os.path.join(script_directory, "version.txt")
with open(version_file_path) as version_file:
    _version = version_file.readline()
    _version_tag = f"[{_version}] "


def exception(msg, *args, **kwargs):
    logging.exception(_version_tag + msg, *args, **kwargs)


def error(msg, *args, **kwargs):
    logging.error(_version_tag + msg, *args, **kwargs)


def warning(msg, *args, **kwargs):
    logging.warning(_version_tag + msg, *args, **kwargs)


def info(msg, *args, **kwargs):
    logging.info(_version_tag + msg, *args, **kwargs)


def debug(msg, *args, **kwargs):
    logging.debug(_version_tag + msg, *args, **kwargs)
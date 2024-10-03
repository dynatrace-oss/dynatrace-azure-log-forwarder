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

import ctypes
import re
import struct
from typing import Dict

from logs_ingest.mapping import dt_me_type_mapper, RESOURCE_TYPE_ATTRIBUTE, RESOURCE_ID_ATTRIBUTE

int64 = ctypes.c_int64 # pylint: disable=C0103

CUSTOM_DEVICE_ENTITY_TYPE = "CUSTOM_DEVICE"
MIN_RESOURCE_TYPE_LENGTH = 2


def infer_monitored_entity_id(category: str, parsed_record: Dict):
    resource_id: str = parsed_record.get(RESOURCE_ID_ATTRIBUTE, None)
    resource_type: str = parsed_record.get(RESOURCE_TYPE_ATTRIBUTE, "").casefold()

    if not resource_id or not resource_type:
        return

    resource_type_with_category = ",".join([resource_type, category.casefold()])
    # Function App and Web app have the same resource type - AZURE_FUNCTION_APP meType can be difine only by resource type and log category combination
    dt_me_type = dt_me_type_mapper.get(resource_type_with_category, dt_me_type_mapper.get(resource_type, None))
    resource_type_elements = resource_type.split("/")
    if not dt_me_type and len(resource_type_elements) > MIN_RESOURCE_TYPE_LENGTH:
        # If we get resourceType for subresource we will cut additional segments out to find Dynatrace MeType within supported resourceTypes.
        # If we don't find it, we won't calculate identifier and send it to Dynatrace.
        # e.g.
        # MICROSOFT.EVENTHUB/NAMESPACES/AUTHORIZATIONRULES -> we will find MICROSOFT.EVENTHUB/NAMESPACES as Dynatrace MeType
        # MICROSOFT.SQL/SERVERS/DATABASES/TESTMS-SQL-DB/AUDITINGSETTINGS/DEFAULT -> MICROSOFT.SQL/SERVERS/DATABASES
        # MICROSOFT.INSIGHTS/DIAGNOSTICSETTINGS -> identifier won't be calculated
        while dt_me_type is None and len(resource_type_elements) > MIN_RESOURCE_TYPE_LENGTH:
            resource_type_elements.pop()
            resource_type = "/".join(resource_type_elements)
            dt_me_type = dt_me_type_mapper.get(resource_type, None)
        if dt_me_type:
            resource_id_pattern = re.compile(rf".*{resource_type.casefold()}/[^/]*", re.IGNORECASE)
            resource_id = resource_id_pattern.match(resource_id).group(0) if resource_id_pattern.match(resource_id) else None

    if dt_me_type and resource_id:
        identifier = [create_monitored_entity_id(dt_me_type_element, resource_id) for dt_me_type_element in dt_me_type]
        parsed_record["dt.source_entity"] = identifier
        custom_device = next((s for s in identifier if CUSTOM_DEVICE_ENTITY_TYPE.casefold() in s.casefold()), None)
        if custom_device is not None:
            parsed_record["dt.entity.custom_device"] = custom_device

def create_monitored_entity_id(entity_type: str, resource_id: str) -> str:
    long_id = _murmurhash2_64A(resource_id.lower().encode("UTF-8"))
    identifier = _encode_me_identifier(entity_type, long_id)
    return identifier


def _zfrs(num, shift):
    # Zero fill right shift.
    return int64((num & 0xFFFFFFFFFFFFFFFF) >> shift).value


def _murmurhash2_64A(data: bytes, seed=0xe17a1465):
    # pylint: disable=C0103
    buf = bytearray(data)
    m = int64(0xc6a4a7935bd1e995).value
    r = 47
    offset = 0
    length = len(buf)

    h = int64(seed ^ ((length - offset) * m)).value

    k = 0

    while (length - offset) >= 8:
        k = struct.unpack_from('<q', buf, offset)[0]
        offset += 8

        k = int64(k * m).value
        k = int64(k ^ _zfrs(k, r)).value
        k = int64(k * m).value

        h = int64(h ^ k).value
        h = int64(h * m).value

    remaining = length - offset
    if remaining > 0:
        finish = bytearray(8)
        finish[:remaining] = buf[offset:]

        h = int64(h ^ struct.unpack_from('<q', finish)[0]).value
        h = int64(h * m).value

    h = int64(h ^ _zfrs(h, r)).value
    h = int64(h * m).value
    h = int64(h ^ _zfrs(h, r)).value
    return h


HEX_DIGITS = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', 'A', 'B', 'C', 'D', 'E', 'F']


def _encode_me_identifier(type_name: str, identifier: int) -> str:
    string_id = type_name + "-"
    i = 60
    while i >= 0:
        hex_digit_index = _zfrs(identifier, i) & 0xF
        string_id += HEX_DIGITS[hex_digit_index]
        i -= 4

    return string_id
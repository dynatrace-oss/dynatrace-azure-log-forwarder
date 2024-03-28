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
from typing import Dict

from . import logging

DEFAULT_SEVERITY_INFO = "Informational"

RESOURCE_ID_ATTRIBUTE = "azure.resource.id"
SUBSCRIPTION_ATTRIBUTE = "azure.subscription"
RESOURCE_GROUP_ATTRIBUTE = "azure.resource.group"
RESOURCE_TYPE_ATTRIBUTE = "azure.resource.type"
RESOURCE_NAME_ATTRIBUTE = "azure.resource.name"

log_level_to_severity_dict = {
    1: 'Critical',
    2: 'Error',
    3: 'Warning',
    4: 'Informational'
}

severity_to_log_level_dict = {v: k for k, v in log_level_to_severity_dict.items()}

azure_level_properties = ['Level', 'level']
azure_properties_names = ['properties', 'EventProperties']
activity_log_categories = ['alert', 'administrative', 'resourcehealth', 'servicehealth', 'security', 'policy', 'recommendation', 'autoscale']

working_directory = os.path.dirname(os.path.realpath(__file__))
me_type_mapper_file_path = os.path.join(working_directory, "me_type_mapper.json")
dt_me_type_mapper = {}
try:
    with open(me_type_mapper_file_path) as me_type_mapper_file:
        me_type_mapper_json = json.load(me_type_mapper_file)
        for resource_type_to_me_type in me_type_mapper_json:
            resource_type = resource_type_to_me_type["resourceType"].lower()
            category = resource_type_to_me_type.get("category", "").lower()
            key = ",".join(filter(None, [resource_type, category]))
            dt_me_type_mapper.update({key: resource_type_to_me_type["meType"]})
except Exception:
    logging.exception(f"Failed to load file with meType mapping: '{me_type_mapper_file_path}'",
                      "meType-mapping-file-loading-exception")


def extract_resource_id_attributes(parsed_record: Dict, resource_id: str):
    """
    based on https://github.com/Azure/azure-libraries-for-net/blob/Fluent-v1.37.0/src/ResourceManagement/ResourceManager/Core/ResourceId.cs#L29
    Format of id:
    /subscriptions/<subscriptionId>/resourceGroups/<resourceGroupName>/providers/<providerNamespace>(/<parentResourceType>/<parentName>)*/<resourceType>/<name>
    0             1                2              3                   4         5                                                        N-2            N-1
    example: /SUBSCRIPTIONS/69B51384-146C-4685-9DAB-5AE01877D7B8/RESOURCEGROUPS/TESTMS/PROVIDERS/MICROSOFT.APIMANAGEMENT/SERVICE/WEATHERAPP-API-MGMT
    """
    parsed_record[RESOURCE_ID_ATTRIBUTE] = resource_id
    parts = resource_id.lstrip("/").split("/")

    # No logging on invalid resource_id to avoid flooding logs. Invalid resource id will be sent
    # with log line to Dynatrace so we keep the ability to debug in case of any issues
    if len(parts) < 7:
        return
    if parts[0].casefold() != "SUBSCRIPTIONS".casefold():
        return
    if parts[2].casefold() != "RESOURCEGROUPS".casefold():
        return
    if parts[4].casefold() != "PROVIDERS".casefold():
        return

    parsed_record[SUBSCRIPTION_ATTRIBUTE] = parts[1]
    parsed_record[RESOURCE_GROUP_ATTRIBUTE] = parts[3]
    parsed_record[RESOURCE_NAME_ATTRIBUTE] = parts[-1]

    resource_type_parts_with_parent = parts[5:-1]
    # Filter out parent resource name to create hierarchic resource type as cloudbuilder does
    resource_type_parts = [part for index, part in enumerate(resource_type_parts_with_parent) if (index == 0 or index % 2 != 0)]
    parsed_record[RESOURCE_TYPE_ATTRIBUTE] = "/".join(resource_type_parts)


def extract_severity(record: Dict, parsed_record: Dict):
    level_property = next((level for level in azure_level_properties if level in record.keys()), None)
    if level_property:
        map_to_severity(record, parsed_record, level_property)
    else:
        parsed_record["severity"] = DEFAULT_SEVERITY_INFO


def map_to_severity(record: Dict, parsed_record: Dict, level_property: str):
    if isinstance(record[level_property], int):
        parsed_record["severity"] = log_level_to_severity_dict.get(record[level_property], DEFAULT_SEVERITY_INFO)
    else:
        parsed_record["severity"] = record[level_property]

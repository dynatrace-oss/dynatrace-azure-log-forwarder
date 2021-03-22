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

from logs_ingest.mapping import RESOURCE_TYPE_ATTRIBUTE
from logs_ingest.metadata_engine import SourceMatcher, _create_config_rule


def test_resource_type_eq_source_matcher():
    matcher = SourceMatcher("resourceType", "$eq('TEST')")
    assert matcher.match({}, {RESOURCE_TYPE_ATTRIBUTE: "TEST"})
    assert not matcher.match({}, {RESOURCE_TYPE_ATTRIBUTE: "TEST2"})
    assert not matcher.match({}, {})


def test_resource_type_contains_source_matcher():
    matcher = SourceMatcher("resourceType", "$contains('TEST')")
    assert matcher.match({}, {RESOURCE_TYPE_ATTRIBUTE: "AZURE_TEST_2"})
    assert not matcher.match({}, {RESOURCE_TYPE_ATTRIBUTE: "AZURE_PROD"})
    assert not matcher.match({}, {})


def test_resource_type_prefix_source_matcher():
    matcher = SourceMatcher("resourceType", "$prefix('TEST')")
    assert matcher.match({}, {RESOURCE_TYPE_ATTRIBUTE: "TEST_AZURE"})
    assert not matcher.match({}, {RESOURCE_TYPE_ATTRIBUTE: "AZURE_TEST"})
    assert not matcher.match({}, {})


def test_category_eq_source_matcher():
    matcher = SourceMatcher("category", "$eq('TEST')")
    assert matcher.match({"category": "TEST"}, {})
    assert not matcher.match({"category": "BONOBO"}, {})
    assert not matcher.match({}, {})


def test_create_valid_config_rule():
    rule_json = {
        "sources": [{"sourceType": "logs", "source": "resourceType", "condition": "$eq('MICROSOFT.APIMANAGEMENT/SERVICE')"}]
    }
    assert _create_config_rule("TEST", rule_json)


def test_create_invalid_config_rule_source_missing_field():
    rule_json = {
        "sources": [{"sourceType": "logs", "condition": "$eq('MICROSOFT.APIMANAGEMENT/SERVICE')"}]
    }
    assert not _create_config_rule("TEST", rule_json)


def test_create_invalid_config_rule_invalid_source():
    rule_json = {
        "sources": [{"sourceType": "logs", "source": "INVALID", "condition": "$eq('MICROSOFT.APIMANAGEMENT/SERVICE')"}]
    }
    assert not _create_config_rule("TEST", rule_json)


def test_default_rule_can_have_no_sources():
    rule_json = {
        "sources": []
    }
    assert _create_config_rule("default", rule_json)
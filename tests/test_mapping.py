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

from logs_ingest.mapping import extract_resource_id_attributes, RESOURCE_ID_ATTRIBUTE, SUBSCRIPTION_ATTRIBUTE, \
    RESOURCE_GROUP_ATTRIBUTE, RESOURCE_TYPE_ATTRIBUTE, RESOURCE_NAME_ATTRIBUTE


def test_extract_resource_id_simple_resource_id():
    run_successful_extraction_test(
        resource_id="subscriptions/a84d2d12-76ea-449c-8c1e-9fb2dee5f6b1/resourceGroups/rg-adagze/providers/Microsoft.Maps/accounts/maps-hackaton-test",
        expected_subscription="a84d2d12-76ea-449c-8c1e-9fb2dee5f6b1",
        expected_resource_group="rg-adagze",
        expected_resource_type="Microsoft.Maps/accounts",
        expected_resource_name="maps-hackaton-test"
    )


def test_extract_resource_id_attributes_nested_resource_type():
    run_successful_extraction_test(
        resource_id="/subscriptions/a84d2d12-76ea-449c-8c1e-9fb2dee5f6b1/resourceGroups/rg-jelpet/providers/Microsoft.NetApp/netAppAccounts/naf-jelpet-just-trying/capacityPools/cappool-jelpet-just-trying",
        expected_subscription="a84d2d12-76ea-449c-8c1e-9fb2dee5f6b1",
        expected_resource_group="rg-jelpet",
        expected_resource_type="Microsoft.NetApp/netAppAccounts/capacityPools",
        expected_resource_name="cappool-jelpet-just-trying"
    )


def test_extract_resource_id_attributes_invalid_resource_id():
    result_dict = {}
    resource_id = "a84d2d12-76ea-449c-8c1e-9fb2dee5f6b1/resourceGroups/rg-jelpet/providers/Microsoft.NetApp/netAppAccounts/naf-jelpet-just-trying/capacityPools/cappool-jelpet-just-trying"
    extract_resource_id_attributes(result_dict, resource_id)
    assert result_dict == {RESOURCE_ID_ATTRIBUTE: resource_id}


def run_successful_extraction_test(
        resource_id: str,
        expected_subscription: str,
        expected_resource_group: str,
        expected_resource_type: str,
        expected_resource_name: str
):
    result_dict = {}
    extract_resource_id_attributes(result_dict, resource_id)
    assert result_dict[SUBSCRIPTION_ATTRIBUTE].casefold() == expected_subscription.casefold()
    assert result_dict[RESOURCE_GROUP_ATTRIBUTE].casefold() == expected_resource_group.casefold()
    assert result_dict[RESOURCE_TYPE_ATTRIBUTE].casefold() == expected_resource_type.casefold()
    assert result_dict[RESOURCE_NAME_ATTRIBUTE].casefold() == expected_resource_name.casefold()

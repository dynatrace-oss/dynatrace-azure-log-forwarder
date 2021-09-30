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
from datetime import datetime
from typing import NewType, Any

from logs_ingest import main
from logs_ingest.mapping import RESOURCE_NAME_ATTRIBUTE, RESOURCE_TYPE_ATTRIBUTE, RESOURCE_GROUP_ATTRIBUTE, \
    SUBSCRIPTION_ATTRIBUTE, RESOURCE_ID_ATTRIBUTE
from logs_ingest.self_monitoring import SelfMonitoring

MonkeyPatchFixture = NewType("MonkeyPatchFixture", Any)

record = {
    "Level": 4,
    "time": "2021-01-29T09:25:05.3511301Z",
    "operationName": "Microsoft.ApiManagement/GatewayLogs",
    "category": "GatewayLogs",
    "durationMs": 166,
    "callerIpAddress": "137.117.214.210",
    "correlationId": "bf0d72ed-e82f-4549-a642-223ebc40e5cc",
    "location": "West Europe",
    "properties": {
        "method": "GET",
        "url": "https://weatherapp-api-mgmt.azure-api.net/weather/current/Valparaiso",
        "backendResponseCode": 200,
        "responseCode": 200,
        "responseSize": 838,
        "cache": "none",
        "backendTime": 165,
        "requestSize": 288,
        "apiId": "testms-weather-service",
        "operationId": "5d0ca5ff56c952f6b5316199",
        "clientProtocol": "HTTP/1.1",
        "backendProtocol": "HTTP/1.1",
        "backendId": "ApiApp_testms-weather-service",
        "apiRevision": "1",
        "clientTlsVersion": "1.2",
        "backendMethod": "GET",
        "backendUrl": "https://testms-weather-service.azurewebsites.net/weather/current/Valparaiso"
    },
    "resourceId": "/SUBSCRIPTIONS/69B51384-146C-4685-9DAB-5AE01877D7B8/RESOURCEGROUPS/TESTMS/PROVIDERS/MICROSOFT/FAKE_SERVICE/WEATHERAPP-API-MGMT"
}

expected_output = {
    "cloud.provider": "Azure",
    "cloud.region": "West Europe",
    "timestamp": "2021-01-29T09:25:05.3511301Z",
    "log.source": "GatewayLogs",
    "severity": "Informational",
    "content": json.dumps(record),
    RESOURCE_ID_ATTRIBUTE: "/SUBSCRIPTIONS/69B51384-146C-4685-9DAB-5AE01877D7B8/RESOURCEGROUPS/TESTMS/PROVIDERS/MICROSOFT/FAKE_SERVICE/WEATHERAPP-API-MGMT",
    SUBSCRIPTION_ATTRIBUTE: "69B51384-146C-4685-9DAB-5AE01877D7B8",
    RESOURCE_GROUP_ATTRIBUTE: "TESTMS",
    RESOURCE_TYPE_ATTRIBUTE: "MICROSOFT/FAKE_SERVICE",
    RESOURCE_NAME_ATTRIBUTE: "WEATHERAPP-API-MGMT"
}

expected_output_attribute_values_trimmed = {
    "cloud.provider": "Azur",
    "cloud.region": "West",
    "timestamp": "2021-01-29T09:25:05.3511301Z",
    "log.source": "Gate",
    "severity": "Informational",
    "content": json.dumps(record),
    RESOURCE_ID_ATTRIBUTE: "/SUB",
    SUBSCRIPTION_ATTRIBUTE: "69B5",
    RESOURCE_GROUP_ATTRIBUTE: "TEST",
    RESOURCE_TYPE_ATTRIBUTE: "MICR",
    RESOURCE_NAME_ATTRIBUTE: "WEAT"
}

default_activity_log = {
    "time": "2021-02-09T09:57:26.498Z",
    "correlationId": "55dc161c-c72e-4cb7-b41a-4e7e6835c076",
    "operationName": "Microsoft.ServiceHealth/actionrequired/action",
    "level": "Information",
    "resultType": "Activated",
    "category": "ServiceHealth",
    "properties": {
        "eventCategory": "ServiceHealth",
        "eventProperties": {
            "title": "Action Required: Security Advisory on Linux Kernel TCP vulnerabilities",
            "service": "Virtual Machines",
            "region": "Australia Central",
            "communication": "<p>Microsoft Azure is aware of the disclosure of three severe Linux kernel TCP networking vulnerabilities, known as TCP SACK Panic:</p><ul><li><a href=\"https://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2019-11477\">CVE-2019-11477</a></li><li><a href=\"https://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2019-11478\">CVE-2019-11478</a></li><li><a href=\"https://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2019-11479\">CVE-2019-11479</a></li></ul><p>Virtual Machines running any Linux distribution should be addressed.&nbsp; For guidance on these vulnerabilities,&nbsp;please refer to the Linux support channels for your distribution or go to our <a href=\"https://portal.msrc.microsoft.com/en-US/security-guidance/advisory/ADV190020\">Microsoft Security Advisory 190020</a>.</p><p>Note: Virtual Machines running Windows are not affected by this vulnerability.</p><p><strong>Recommended Actions:</strong></p><ul><li>If you are running a Linux kernel in your Azure environment, you should contact the provider of that Linux kernel to understand their recommendation for protecting your installation. </li><li>Refer to the <a href=\"https://portal.msrc.microsoft.com/en-US/security-guidance/advisory/ADV190020\">Microsoft Security Advisory 190020</a> for\n     guidance around specific Azure services (Azure Sphere, Azure Kubernetes\n     Service, and Azure HDInsight)\n\n\n</li></ul><p></p>",
            "incidentType": "ActionRequired",
            "trackingId": "GTK4-188",
            "impactStartTime": "2019-06-28T00:00:00Z",
            "impactedServices": "[{\"ImpactedRegions\":[{\"RegionName\":\"Australia Central\"},{\"RegionName\":\"Australia Central 2\"},{\"RegionName\":\"Australia East\"},{\"RegionName\":\"Australia Southeast\"},{\"RegionName\":\"Brazil South\"},{\"RegionName\":\"Canada Central\"},{\"RegionName\":\"Canada East\"},{\"RegionName\":\"Central India\"},{\"RegionName\":\"Central US\"},{\"RegionName\":\"Central US EUAP\"},{\"RegionName\":\"East Asia\"},{\"RegionName\":\"East US\"},{\"RegionName\":\"East US 2\"},{\"RegionName\":\"East US 2 EUAP\"},{\"RegionName\":\"France Central\"},{\"RegionName\":\"France South\"},{\"RegionName\":\"Japan East\"},{\"RegionName\":\"Japan West\"},{\"RegionName\":\"Korea Central\"},{\"RegionName\":\"Korea South\"},{\"RegionName\":\"North Central US\"},{\"RegionName\":\"North Europe\"},{\"RegionName\":\"South Africa North\"},{\"RegionName\":\"South Africa West\"},{\"RegionName\":\"South Central US\"},{\"RegionName\":\"Southeast Asia\"},{\"RegionName\":\"South India\"},{\"RegionName\":\"UAE Central\"},{\"RegionName\":\"UAE North\"},{\"RegionName\":\"UK South\"},{\"RegionName\":\"UK West\"},{\"RegionName\":\"West Central US\"},{\"RegionName\":\"West Europe\"},{\"RegionName\":\"West India\"},{\"RegionName\":\"West US\"},{\"RegionName\":\"West US 2\"}],\"ServiceName\":\"Virtual Machines\"},{\"ImpactedRegions\":[{\"RegionName\":\"Australia Central\"},{\"RegionName\":\"Australia Central 2\"},{\"RegionName\":\"Australia East\"},{\"RegionName\":\"Australia Southeast\"},{\"RegionName\":\"Brazil South\"},{\"RegionName\":\"Canada Central\"},{\"RegionName\":\"Canada East\"},{\"RegionName\":\"Central India\"},{\"RegionName\":\"Central US\"},{\"RegionName\":\"Central US EUAP\"},{\"RegionName\":\"East Asia\"},{\"RegionName\":\"East US\"},{\"RegionName\":\"East US 2\"},{\"RegionName\":\"East US 2 EUAP\"},{\"RegionName\":\"France Central\"},{\"RegionName\":\"France South\"},{\"RegionName\":\"Japan East\"},{\"RegionName\":\"Japan West\"},{\"RegionName\":\"Korea Central\"},{\"RegionName\":\"Korea South\"},{\"RegionName\":\"North Central US\"},{\"RegionName\":\"North Europe\"},{\"RegionName\":\"South Africa North\"},{\"RegionName\":\"South Africa West\"},{\"RegionName\":\"South Central US\"},{\"RegionName\":\"Southeast Asia\"},{\"RegionName\":\"South India\"},{\"RegionName\":\"UAE Central\"},{\"RegionName\":\"UAE North\"},{\"RegionName\":\"UK South\"},{\"RegionName\":\"UK West\"},{\"RegionName\":\"West Central US\"},{\"RegionName\":\"West Europe\"},{\"RegionName\":\"West India\"},{\"RegionName\":\"West US\"},{\"RegionName\":\"West US 2\"}],\"ServiceName\":\"Virtual Machine Scale Sets\"}]",
            "impactedServicesTableRows": "<tr>\r\n<td align='center' style='padding: 5px 10px; border-right:1px solid black; border-bottom:1px solid black'>Virtual Machines</td>\r\n<td align='center' style='padding: 5px 10px; border-bottom:1px solid black'>Australia Central<br>Australia Central 2<br>Australia East<br>Australia Southeast<br>Brazil South<br>Canada Central<br>Canada East<br>Central India<br>Central US<br>Central US EUAP<br>East Asia<br>East US<br>East US 2<br>East US 2 EUAP<br>France Central<br>France South<br>Japan East<br>Japan West<br>Korea Central<br>Korea South<br>North Central US<br>North Europe<br>South Africa North<br>South Africa West<br>South Central US<br>Southeast Asia<br>South India<br>UAE Central<br>UAE North<br>UK South<br>UK West<br>West Central US<br>West Europe<br>West India<br>West US<br>West US 2<br></td>\r\n</tr>\r\n<tr>\r\n<td align='center' style='padding: 5px 10px; border-right:1px solid black; border-bottom:1px solid black'>Virtual Machine Scale Sets</td>\r\n<td align='center' style='padding: 5px 10px; border-bottom:1px solid black'>Australia Central<br>Australia Central 2<br>Australia East<br>Australia Southeast<br>Brazil South<br>Canada Central<br>Canada East<br>Central India<br>Central US<br>Central US EUAP<br>East Asia<br>East US<br>East US 2<br>East US 2 EUAP<br>France Central<br>France South<br>Japan East<br>Japan West<br>Korea Central<br>Korea South<br>North Central US<br>North Europe<br>South Africa North<br>South Africa West<br>South Central US<br>Southeast Asia<br>South India<br>UAE Central<br>UAE North<br>UK South<br>UK West<br>West Central US<br>West Europe<br>West India<br>West US<br>West US 2<br></td>\r\n</tr>\r\n",
            "defaultLanguageTitle": "Action Required: Security Advisory on Linux Kernel TCP vulnerabilities",
            "defaultLanguageContent": "<p>Microsoft Azure is aware of the disclosure of three severe Linux kernel TCP networking vulnerabilities, known as TCP SACK Panic:</p><ul><li><a href=\"https://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2019-11477\">CVE-2019-11477</a></li><li><a href=\"https://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2019-11478\">CVE-2019-11478</a></li><li><a href=\"https://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2019-11479\">CVE-2019-11479</a></li></ul><p>Virtual Machines running any Linux distribution should be addressed.&nbsp; For guidance on these vulnerabilities,&nbsp;please refer to the Linux support channels for your distribution or go to our <a href=\"https://portal.msrc.microsoft.com/en-US/security-guidance/advisory/ADV190020\">Microsoft Security Advisory 190020</a>.</p><p>Note: Virtual Machines running Windows are not affected by this vulnerability.</p><p><strong>Recommended Actions:</strong></p><ul><li>If you are running a Linux kernel in your Azure environment, you should contact the provider of that Linux kernel to understand their recommendation for protecting your installation. </li><li>Refer to the <a href=\"https://portal.msrc.microsoft.com/en-US/security-guidance/advisory/ADV190020\">Microsoft Security Advisory 190020</a> for\n     guidance around specific Azure services (Azure Sphere, Azure Kubernetes\n     Service, and Azure HDInsight)\n\n\n</li></ul><p></p>",
            "stage": "Active",
            "communicationId": "11000026609725",
            "endTime": "2019-07-04T00:00:00Z",
            "isHIR": "false",
            "version": "0.1.1"
        }
    }
}

expected_output_activity_log = {
    "cloud.provider": "Azure",
    "timestamp": "2021-02-09T09:57:26.498Z",
    "log.source": "Activity Log - ServiceHealth",
    "severity": "Information",
    "content": json.dumps(default_activity_log),
    "audit.action": "Microsoft.ServiceHealth/actionrequired/action",
    "audit.result": "Activated"
}


def test_default():
    actual_output = main.parse_record(record, SelfMonitoring(execution_time=datetime.utcnow()))
    assert actual_output == expected_output


def test_trimming_attribute_values(monkeypatch: MonkeyPatchFixture):
    monkeypatch.setattr(main, 'attribute_value_length_limit', 4)
    actual_output = main.parse_record(record, SelfMonitoring(execution_time=datetime.utcnow()))
    assert actual_output == expected_output_attribute_values_trimmed


def test_default_activity_log():
    actual_output = main.parse_record(default_activity_log, SelfMonitoring(execution_time=datetime.utcnow()))
    assert actual_output == expected_output_activity_log

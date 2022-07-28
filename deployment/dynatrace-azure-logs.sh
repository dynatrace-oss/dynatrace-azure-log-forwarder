#!/bin/bash
#     Copyright 2021 Dynatrace LLC
#
#     Licensed under the Apache License, Version 2.0 (the "License");
#     you may not use this file except in compliance with the License.
#     You may obtain a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#     Unless required by applicable law or agreed to in writing, software
#     distributed under the License is distributed on an "AS IS" BASIS,
#     WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#     See the License for the specific language governing permissions and
#     limitations under the License.

readonly FUNCTION_ARM=dynatrace-azure-forwarder.json
readonly FUNCTION_ZIP_PACKAGE=dynatrace-azure-log-forwarder.zip
# Please be cautious with editing the following line, as CI is changing latest to specific version on release, see: .travis.yml
readonly FUNCTION_REPOSITORY_RELEASE_URL=https://github.com/dynatrace-oss/dynatrace-azure-log-forwarder/releases/latest/download/
readonly DYNATRACE_TARGET_URL_REGEX="^(https?:\/\/[-a-zA-Z0-9@:%._+~=]{1,255}\/?)(\/e\/[a-z0-9-]{36}\/?)?$"
readonly ACTIVE_GATE_TARGET_URL_REGEX="^https:\/\/[-a-zA-Z0-9@:%._+~=]{1,255}\/e\/[-a-z0-9]{1,36}[\/]{0,1}$"
readonly DEPLOYMENT_NAME_REGEX="^[-a-z0-9]{3,20}$"
readonly EVENT_HUB_CONNECTION_STRING_REGEX="^Endpoint=sb:\/\/.*EntityPath=[^[:space:]]+$"
readonly FILTER_CONFIG_REGEX="([^;\s].+?)=([^;]*)"
readonly TAGS_REGEX="^([^<>,%&\?\/]+?:[^,]+,?)+$"

print_help()
{
   printf "
usage: dynatrace-azure-logs.sh --deployment-name DEPLOYMENT_NAME --target-url TARGET_URL --target-api-token TARGET_API_TOKEN --resource-group RESOURCE_GROUP --event-hub-connection-string EVENT_HUB_CONNECTION_STRING [--use-existing-active-gate USE_EXISTING_ACTIVE_GATE] [--target-paas-token TARGET_PAAS_TOKEN] [--filter-config FILTER_CONFIG] [--require-valid-certificate REQUIRE_VALID_CERTIFICATE] [--enable-self-monitoring SFM_ENABLED] [--repository-release-url REPOSITORY_RELEASE_URL]

arguments:
    -h, --help              Show this help message and exit
    --deployment-name DEPLOYMENT_NAME
                            e.g. \"dynatracelogs\", use lowercase only
    --use-existing-active-gate {true|false}
                          Optional, 'true' by default.
                          If you choose new ActiveGate deployment, put 'false'. In such case, ActiveGate will be deployed as container in Azure Container Instances.
                          If you choose to use direct ingest through the Cluster API or existing ActiveGate, put 'true'.
    --target-url TARGET_URL
                            With ActiveGate deployment option set URL to your Dynatrace SaaS, otherwise set ActiveGate endpoint:
                              - for direct ingest through the Cluster API: https://<your_environment_ID>.live.dynatrace.com
                              - for Environment ActiveGate: https://<active_gate_address>:9999/e/<environment_id> (e.g. https://22.111.98.222:9999/e/abc12345)
    --target-api-token TARGET_API_TOKEN
                            Dynatrace API token. Integration requires API v1 Log import Token permission.
    --target-paas-token TARGET_PAAS_TOKEN
                            Dynatrace PaaS token, only when deploy ActiveGate is chosen
    --resource-group RESOURCE_GROUP
                            Name of the Azure Resource Group in which Function will be deployed
    --event-hub-connection-string EVENT_HUB_CONNECTION_STRING
                            Connection string for Azure EventHub that is configured for receiving logs
    --tags TAGS
                            Comma separated tag:value pairs added to Azure resources during azure-log-forwarder deployment
                            e.g. \"tagName:value,tagName2:value2,tagName3:value3\"
    --require-valid-certificate {true|false}
                            Enables checking SSL certificate of the target Active Gate. By default (if this option is not provided) certificates aren't validated.
    --enable-self-monitoring {true|false}
                            Self monitoring allows to diagnose quickly your function by Azure custom metrics. By default (if this option is not provided) custom metrics won't be sent to Azure.
    --filter-config FILTER_CONFIG
                            Optional. Apply filters to reduce number of logs that are sent to Dynatrace e.g. filter out logs with Informational level.
    --repository-release-url REPOSITORY_RELEASE_URL
                            Change repository url to custom. Do not change without specific reason
    "
}

ensure_param_value_given() {
  # Checks if a value ($2) was passed for a parameter ($1). The two OR'ed conditions catch the following mistakes:
  # 1. The parameter is the last one and has no value
  # 2. The parameter is between other parameters and (as it has no value) the name of the next parameter is taken as its value
  if [ -z $2 ] || [[ $2 == "--"* ]]; then
    echo "Missing value for parameter $1";
    print_help;
    exit 1;
  fi
}

print_all_parameters() {
  PARAMETERS="DEPLOYMENT_NAME=$DEPLOYMENT_NAME, USE_EXISTING_ACTIVE_GATE=$USE_EXISTING_ACTIVE_GATE, TARGET_URL=$TARGET_URL, TARGET_API_TOKEN=*****, RESOURCE_GROUP=$RESOURCE_GROUP, EVENT_HUB_CONNECTION_STRING=*****, REQUIRE_VALID_CERTIFICATE=$REQUIRE_VALID_CERTIFICATE, SFM_ENABLED=$SFM_ENABLED, REPOSITORY_RELEASE_URL=$REPOSITORY_RELEASE_URL"
  if [[ "$USE_EXISTING_ACTIVE_GATE" == "false" ]]; then PARAMETERS+=", TARGET_PAAS_TOKEN=*****"; fi
  if [ -n "$FILTER_CONFIG" ]; then PARAMETERS+=", FILTER_CONFIG=$FILTER_CONFIG"; fi
  if [ -n "$TAGS" ]; then PARAMETERS+=", TAGS=$TAGS"; fi
  echo
  echo "Deployment script will use following parameters:"
  echo $PARAMETERS
}

check_arg() {
  CLI_ARGUMENT_NAME=$1
  ARGUMENT=$2
  REGEX=$3
  if [ -z "$ARGUMENT" ]; then
    echo "No $CLI_ARGUMENT_NAME"
    exit 1
  else
    if ! [[ "$ARGUMENT" =~ $REGEX ]]; then
      echo "Not correct $CLI_ARGUMENT_NAME"
      exit 1
    fi
  fi
}

check_activegate_state() {
  RUNNING_RESPONSE_ON_NORMAL_CLUSTERS="RUNNING"
  RUNNING_RESPONSE_ON_DOK_CLUSTERS="\"RUNNING\"" #APM-379036 different responses returned - to be fixed in bug APM-380143
  if ACTIVE_GATE_STATE=$(curl -ksS "${TARGET_URL}/rest/health" --connect-timeout 20); then
    if [[ "$ACTIVE_GATE_STATE" != "$RUNNING_RESPONSE_ON_NORMAL_CLUSTERS" ]] && [[ "$ACTIVE_GATE_STATE" != "$RUNNING_RESPONSE_ON_DOK_CLUSTERS"  ]]; then
      echo -e ""
      echo -e "\e[91mERROR: \e[37mActiveGate endpoint is not reporting RUNNING state. Please verify provided values for parameters: --target-url (${TARGET_URL})."
      exit 1
    fi
  else
      echo -e "\e[93mWARNING: \e[37mFailed to connect with provided ActiveGate url ($TARGET_URL) to check state. It can be ignored if ActiveGate does not allow public access."
  fi
}

check_api_token() {
  if RESPONSE=$(curl -k -s -X POST -d "{\"token\":\"$TARGET_API_TOKEN\"}" "$TARGET_URL/api/v2/apiTokens/lookup" -w "<<HTTP_CODE>>%{http_code}" -H "accept: application/json; charset=utf-8" -H "Content-Type: application/json; charset=utf-8" -H "Authorization: Api-Token $TARGET_API_TOKEN" --connect-timeout 20); then
    CODE=$(sed -rn 's/.*<<HTTP_CODE>>(.*)$/\1/p' <<<"$RESPONSE")
    RESPONSE=$(sed -r 's/(.*)<<HTTP_CODE>>.*$/\1/' <<<"$RESPONSE")
    if [ "$CODE" -ge 300 ]; then
      echo -e "\e[91mERROR: \e[37mFailed to check Dynatrace API token permissions - please verify provided values for parameters: --target-url (${TARGET_URL}) and --target-api-token. $RESPONSE"
      exit 1
    fi
    if ! grep -q '"logs.ingest"' <<<"$RESPONSE"; then
      echo -e "\e[91mERROR: \e[37mMissing Ingest logs permission (v2) for the API token"
      exit 1
    fi
  else
      echo -e "\e[93mWARNING: \e[37mFailed to connect to endpoint $TARGET_URL to check API token permissions. It can be ignored if Dynatrace/ActiveGate does not allow public access."
  fi
}

generate_test_log()
{
  DATE=$(date --iso-8601=seconds)
  cat <<EOF
{
"timestamp": "$DATE",
"cloud.provider": "azure",
"content": "Azure Log Forwarder installation log",
"severity": "INFO"
}
EOF
}

check_dynatrace_log_ingest_url() {
  if RESPONSE=$(curl -k -s -X POST -d "$(generate_test_log)" "$TARGET_URL/api/v2/logs/ingest" -w "<<HTTP_CODE>>%{http_code}" -H "accept: application/json; charset=utf-8" -H "Content-Type: application/json; charset=utf-8" -H "Authorization: Api-Token $TARGET_API_TOKEN" --connect-timeout 20); then
    CODE=$(sed -rn 's/.*<<HTTP_CODE>>(.*)$/\1/p' <<<"$RESPONSE")
    RESPONSE=$(sed -r 's/(.*)<<HTTP_CODE>>.*$/\1/' <<<"$RESPONSE")
    if [ "$CODE" -ge 300 ]; then
      echo -e "\e[91mERROR: \e[37mFailed to send a test log to Dynatrace - please verify provided log ingest url ($TARGET_URL) and API token. $RESPONSE"
      exit 1
    fi
  else
    echo -e "\e[93mWARNING: \e[37mFailed to connect to endpoint $TARGET_URL to check API token permissions. It can be ignored if Dynatrace/ActiveGate does not allow public access."
  fi
}

while (( "$#" )); do
    case "$1" in
            "-h" | "--help")
                print_help
                exit 0
            ;;

            "--deployment-name")
                ensure_param_value_given $1 $2
                DEPLOYMENT_NAME=$2
                shift; shift
            ;;

            "--use-existing-active-gate")
                ensure_param_value_given $1 $2
                USE_EXISTING_ACTIVE_GATE=$2
                shift; shift
            ;;

            "--target-url")
                ensure_param_value_given $1 $2
                TARGET_URL=$2
                shift; shift
            ;;

            "--target-api-token")
                ensure_param_value_given $1 $2
                TARGET_API_TOKEN=$2
                shift; shift
            ;;

            "--target-paas-token")
                ensure_param_value_given $1 $2
                TARGET_PAAS_TOKEN=$2
                shift; shift
            ;;

            "--resource-group")
                ensure_param_value_given $1 $2
                RESOURCE_GROUP=$2
                shift; shift
            ;;

            "--event-hub-connection-string")
                ensure_param_value_given $1 $2
                EVENT_HUB_CONNECTION_STRING=$2
                shift; shift
            ;;

            "--filter-config")
                ensure_param_value_given $1 $2
                FILTER_CONFIG=$2
                shift; shift
            ;;

            "--require-valid-certificate")
                ensure_param_value_given $1 $2
                REQUIRE_VALID_CERTIFICATE=$2
                shift; shift
            ;;

            "--enable-self-monitoring")
                ensure_param_value_given $1 $2
                SFM_ENABLED=$2
                shift; shift
            ;;

            "--repository-release-url")
                ensure_param_value_given $1 $2
                REPOSITORY_RELEASE_URL=$2
                shift; shift
            ;;

            "--tags")
                ensure_param_value_given $1 $2
                TAGS=$2
                shift; shift
            ;;

            *)
            echo "Unknown param $1"
            print_help
            exit 1
    esac
done

if ! command -v az &> /dev/null; then

    echo -e "\e[91mERROR: \e[37mAzure CLI is required to install Dynatrace function. It should be already installed in Cloud Shell."
    echo -e "If you are running this script from other hosts go to following link in your browser and install latest version of Azure CLI:"
    echo -e
    echo -e "https://docs.microsoft.com/en-us/cli/azure/install-azure-cli"
    echo -e
    echo
    exit
fi

if [ $(az version -o table |awk 'NR >= 3 {print $1}') == "2.29.0" ] &> /dev/null; then

    echo -e "\e[91mERROR: \e[37mVersion 2.29.0 of Azure CLI is subject to a bug which prevents Azure Log Forwarder setup from working properly."
    echo -e "You can find the bug description under the link bellow:"
    echo -e
    echo -e "https://github.com/Azure/azure-cli/issues/20131"
    echo -e
    echo -e "If you are running this script from other hosts go to following link in your browser and upgrade to a more recent version of Azure CLI:"
    echo -e
    echo -e "https://docs.microsoft.com/en-us/cli/azure/install-azure-cli"
    echo -e
    echo
    exit
fi

check_arg --deployment-name "$DEPLOYMENT_NAME" "$DEPLOYMENT_NAME_REGEX"
check_arg --resource-group "$RESOURCE_GROUP" ".+"
check_arg --event-hub-connection-string "$EVENT_HUB_CONNECTION_STRING" "$EVENT_HUB_CONNECTION_STRING_REGEX"
if [ -z "$REQUIRE_VALID_CERTIFICATE" ]; then REQUIRE_VALID_CERTIFICATE=false; fi
if [ -z "$SFM_ENABLED" ]; then SFM_ENABLED=false; fi

if [[ "$REQUIRE_VALID_CERTIFICATE" != "true" ]] && [[ "$REQUIRE_VALID_CERTIFICATE" != "false" ]]; then
  echo "Not correct --require-valid-certificate. Provide 'true' or 'false'";
  exit 1;
fi
if [[ "$SFM_ENABLED" != "true" ]] && [[ "$SFM_ENABLED" != "false" ]]; then
  echo "Not correct --enable-self-monitoring. Provide 'true' or 'false'";
  exit 1;
fi
if [[ -z "$USE_EXISTING_ACTIVE_GATE" ]]; then
  USE_EXISTING_ACTIVE_GATE="true"
elif [[ "$USE_EXISTING_ACTIVE_GATE" != "true" ]] && [[ "$USE_EXISTING_ACTIVE_GATE" != "false" ]]; then
  echo "Not correct --use-existing-active-gate. Provide 'true' or 'false'";
  exit 1;
fi

if [ -n "$FILTER_CONFIG" ]; then check_arg --filter-config "$FILTER_CONFIG" "$FILTER_CONFIG_REGEX";fi
if [ -n "$TAGS" ]; then check_arg --tags "$TAGS" "$TAGS_REGEX"; fi

if [ -z "$TARGET_URL" ]; then
  echo "No --target-url"
  exit 1
else
  if [[ "$USE_EXISTING_ACTIVE_GATE" == "false" ]] && ! [[ "${TARGET_URL}" =~ $DYNATRACE_TARGET_URL_REGEX ]]; then
    echo -e "\e[91mERROR: \e[37mNot correct --target-url. Example of proper url for deployment with new ActiveGate: https://<your_environment_ID>.live.dynatrace.com"
    exit 1
  elif [[ "$USE_EXISTING_ACTIVE_GATE" == "true" ]] && ! ([[ "${TARGET_URL}" =~ $ACTIVE_GATE_TARGET_URL_REGEX ]] || [[ "${TARGET_URL}" =~ $DYNATRACE_TARGET_URL_REGEX ]]); then
    echo -e "\e[91mERROR: \e[37mNot correct --target-url. Example of proper url for deployment with existing ActiveGate:"
    echo -e "  - for direct ingest through the Cluster API: https://<your_environment_ID>.live.dynatrace.com"
    echo -e "  - for Environment ActiveGate: https://<your_activegate_IP_or_hostname>:9999/e/<your_environment_ID>"
    exit 1
  fi
fi

if [ -z "$TARGET_API_TOKEN" ]; then echo "No --target-api-token"; exit 1; fi
if [[ "$USE_EXISTING_ACTIVE_GATE" == "false" ]] && [ -z "$TARGET_PAAS_TOKEN" ]; then echo "No --target-paas-token"; exit 1; fi
if [[ "$USE_EXISTING_ACTIVE_GATE" == true ]]; then DEPLOY_ACTIVEGATE=false;else DEPLOY_ACTIVEGATE=true;fi
if [ -z "$REPOSITORY_RELEASE_URL" ]; then REPOSITORY_RELEASE_URL=${FUNCTION_REPOSITORY_RELEASE_URL}; fi
print_all_parameters

TARGET_URL=$(echo "$TARGET_URL" | sed 's:/*$::')

echo
if [[ "${DEPLOY_ACTIVEGATE}" == "false" ]]; then
  check_activegate_state
fi

check_api_token

if [[ "${DEPLOY_ACTIVEGATE}" == "false" ]]; then
  check_dynatrace_log_ingest_url
fi

EVENT_HUB_NAME=$(echo "$EVENT_HUB_CONNECTION_STRING" | awk -F ';EntityPath=' '{print $2}')

echo "- deploying function infrastructure into Azure..."

IFS=',' read -r -a TAG_PAIRS <<< "$TAGS"
LOG_FORWARDER_TAGS="\"LogsForwarderDeployment\":\"${DEPLOYMENT_NAME}\""
for TAG_PAIR in "${TAG_PAIRS[@]}"; do
  IFS=':' read -r -a TAG_KEY_VALUE <<< "$TAG_PAIR"
  LOG_FORWARDER_TAGS="${LOG_FORWARDER_TAGS},\"${TAG_KEY_VALUE[0]}\":\"${TAG_KEY_VALUE[1]}\""
done
LOG_FORWARDER_TAGS="{${LOG_FORWARDER_TAGS}}"

az deployment group create \
--resource-group ${RESOURCE_GROUP} \
--template-uri ${REPOSITORY_RELEASE_URL}${FUNCTION_ARM} \
--parameters forwarderName="${DEPLOYMENT_NAME}" \
targetUrl="${TARGET_URL}" \
targetAPIToken="${TARGET_API_TOKEN}" \
eventHubConnectionString="${EVENT_HUB_CONNECTION_STRING}" \
eventHubName="${EVENT_HUB_NAME}" \
requireValidCertificate=${REQUIRE_VALID_CERTIFICATE} \
selfMonitoringEnabled="${SFM_ENABLED}" \
deployActiveGateContainer="${DEPLOY_ACTIVEGATE}" \
targetPaasToken="${TARGET_PAAS_TOKEN}" \
filterConfig="${FILTER_CONFIG}" \
resourceTags="${LOG_FORWARDER_TAGS}"

if [[ $? != 0 ]]; then
    echo -e "\e[91mFunction deployment failed"
    exit 2
fi

echo
echo "- downloading function code zip [${REPOSITORY_RELEASE_URL}${FUNCTION_ZIP_PACKAGE}]"
wget -q ${REPOSITORY_RELEASE_URL}${FUNCTION_ZIP_PACKAGE} -O ${FUNCTION_ZIP_PACKAGE}

FUNCTIONAPP_NAME="${DEPLOYMENT_NAME}-function"
echo
echo "- deploying function zip code into ${FUNCTIONAPP_NAME}..."

sleep 60 # wait some time to allow functionapp to warmup

az webapp deployment source config-zip  -n ${FUNCTIONAPP_NAME} -g ${RESOURCE_GROUP} --src ${FUNCTION_ZIP_PACKAGE}

if [[ $? != 0 ]]; then
    echo -e "\e[91mFunction code deployment failed"
    exit 3
fi

echo "- cleaning up"

echo "- removing function package [$FUNCTION_ZIP_PACKAGE]"
rm $FUNCTION_ZIP_PACKAGE

if [[ "${DEPLOY_ACTIVEGATE}" == "true" ]]; then
  # To build Log viewer link we need Dynatrace url (available only in deployment with new ActiveGate or direct ingest through the Cluster API)
  # For deployment with existing ActiveGate (ActiveGate url is used as TARGET_URL) we are not able to build the link - LOG_VIEWER is empty then.
  LOG_VIEWER="Log Viewer: ${TARGET_URL}/ui/log-monitoring?query=cloud.provider%3D%22azure%22"
fi

echo
echo -e "\e[92m- Deployment complete. Check logs in Dynatrace in 10 min. ${LOG_VIEWER}\e[37m"
echo "If you won't see any Azure logs after that time make sure you configured all prerequisites: https://www.dynatrace.com/support/help/shortlink/azure-log-fwd#anchor_prereq"
echo "Additionally you can enable self-monitoring for diagnostic purpose: https://www.dynatrace.com/support/help/shortlink/azure-log-fwd#self-monitoring-optional"

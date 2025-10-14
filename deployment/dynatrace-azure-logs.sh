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
readonly DEPLOYMENT_NAME_REGEX="^[a-z0-9]{3,20}$"
readonly EVENT_HUB_CONNECTION_STRING_REGEX="^Endpoint=sb:\/\/.*EntityPath=[^[:space:]]+$"
readonly FILTER_CONFIG_REGEX="([^;\s].+?)=([^;]*)"
readonly TAGS_REGEX="^([^<>,%&\?\/]+?:[^,]+,?)+$"
readonly REQUIRE_VALID_CERTIFICATE_DEFAULT=true

info() {
  MESSAGE=$1
  CURRENT_TIME=$(date +%T)
  echo "${CURRENT_TIME} ${MESSAGE}"
}

log_step() {
  MESSAGE=$1
  CURRENT_TIME=$(date +%T)
  echo
  echo "${CURRENT_TIME} - ${MESSAGE}"
}

success() {
  MESSAGE=$1
  CURRENT_TIME=$(date +%T)
  echo
  echo -e "${CURRENT_TIME} \e[92m${MESSAGE}"
}

warn() {
  MESSAGE=$1
  CURRENT_TIME=$(date +%T)
  echo
  echo -e "${CURRENT_TIME} \e[93mWARNING: \e[37m${MESSAGE}"
}

err() {
  MESSAGE=$1
  CURRENT_TIME=$(date +%T)
  echo
  echo -e "${CURRENT_TIME} \e[91mERROR: \e[37m${MESSAGE}"
}

print_help()
{
   printf "
usage: dynatrace-azure-logs.sh --deployment-name DEPLOYMENT_NAME --target-url TARGET_URL --target-api-token TARGET_API_TOKEN --resource-group RESOURCE_GROUP --event-hub-connection-string EVENT_HUB_CONNECTION_STRING [--use-existing-active-gate USE_EXISTING_ACTIVE_GATE] [--target-paas-token TARGET_PAAS_TOKEN] [--filter-config FILTER_CONFIG] [--require-valid-certificate REQUIRE_VALID_CERTIFICATE] [--enable-self-monitoring SFM_ENABLED] [--repository-release-url REPOSITORY_RELEASE_URL] [--enable-user-assigned-managed-identity ENABLE_USER_ASSIGNED_MANAGED_IDENTITY] [--custom-consumer-group CONSUMER_GROUP]

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
                            Dynatrace API token. Integration requires API v2 Ingest logs Token permission.
    --target-paas-token TARGET_PAAS_TOKEN
                            Dynatrace PaaS token, only when deploy ActiveGate is chosen
    --resource-group RESOURCE_GROUP
                            Name of the Azure Resource Group in which Function will be deployed
    --event-hub-connection-string EVENT_HUB_CONNECTION_STRING
                            Connection string for Azure EventHub that is configured for receiving logs
    --event-hub-name EVENT_HUB_NAME
                            Required only when using user-assigned MI. Azure EventHub name that is configured for receiving logs
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
    --enable-user-assigned-managed-identity {true|false}
                            Optional, 'false' by default
                            if you choose to use user-assigned-managed-identity, you need to change it to 'true' and provide EVENT_HUB_CONNECTION_CLIENT_ID, MANAGED_IDENTITY_RESOURCE_NAME, EVENT_HUB_CONNECTION_FULLY_QUALIFIED_NAMESPACE and EVENT_HUB_NAME
    --eventhub-connection-client-id EVENT_HUB_CONNECTION_CLIENT_ID
                            The client id of User-Assigned MI
    --managed-identity-resource-name MANAGED_IDENTITY_RESOURCE_NAME
                            Name of the Managed Identity resource
    --eventhub-connection-fully-qualified-namespace EVENT_HUB_CONNECTION_FULLY_QUALIFIED_NAMESPACE
                            Event Hubs namespace's host name
    --custom-consumer-group CONSUMER_GROUP
                            Optional, custom consumer group for Event Hub.
    "
}

ensure_param_value_given() {
  # Checks if a value ($2) was passed for a parameter ($1). The two OR'ed conditions catch the following mistakes:
  # 1. The parameter is the last one and has no value
  # 2. The parameter is between other parameters and (as it has no value) the name of the next parameter is taken as its value
  if [ -z $2 ] || [[ $2 == "--"* ]]; then
    err "Missing value for parameter $1";
    print_help;
    exit 1;
  fi
}

print_all_parameters() {
  PARAMETERS="DEPLOYMENT_NAME=$DEPLOYMENT_NAME, USE_EXISTING_ACTIVE_GATE=$USE_EXISTING_ACTIVE_GATE, TARGET_URL=$TARGET_URL, TARGET_API_TOKEN=*****, RESOURCE_GROUP=$RESOURCE_GROUP, EVENT_HUB_CONNECTION_STRING=*****, REQUIRE_VALID_CERTIFICATE=$REQUIRE_VALID_CERTIFICATE, SFM_ENABLED=$SFM_ENABLED, REPOSITORY_RELEASE_URL=$REPOSITORY_RELEASE_URL, ENABLE_USER_ASSIGNED_MANAGED_IDENTITY=$ENABLE_USER_ASSIGNED_MANAGED_IDENTITY"
  if [[ "$USE_EXISTING_ACTIVE_GATE" == "false" ]]; then PARAMETERS+=", TARGET_PAAS_TOKEN=*****"; fi
  if [ -n "$FILTER_CONFIG" ]; then PARAMETERS+=", FILTER_CONFIG=$FILTER_CONFIG"; fi
  if [ -n "$TAGS" ]; then PARAMETERS+=", TAGS=$TAGS"; fi
  if [[ "$ENABLE_USER_ASSIGNED_MANAGED_IDENTITY" == "true" ]]; then PARAMETERS+="EVENT_HUB_NAME=$EVENT_HUB_NAME, EVENT_HUB_CONNECTION_CLIENT_ID=$EVENT_HUB_CONNECTION_CLIENT_ID, MANAGED_IDENTITY_RESOURCE_NAME=$MANAGED_IDENTITY_RESOURCE_NAME, EVENT_HUB_CONNECTION_FULLY_QUALIFIED_NAMESPACE=$EVENT_HUB_CONNECTION_FULLY_QUALIFIED_NAMESPACE"; fi
  echo
  info "Deployment script will use following parameters:"
  info "$PARAMETERS"
}

check_arg() {
  CLI_ARGUMENT_NAME=$1
  ARGUMENT=$2
  REGEX=$3
  if [ -z "$ARGUMENT" ]; then
    err "No $CLI_ARGUMENT_NAME"
    exit 1
  else
    if ! [[ "$ARGUMENT" =~ $REGEX ]]; then
      err "Not correct $CLI_ARGUMENT_NAME, pattern is: $REGEX"
      exit 1
    fi
  fi
}

check_activegate_state() {
  RUNNING_RESPONSE_ON_NORMAL_CLUSTERS="RUNNING"
  RUNNING_RESPONSE_ON_DOK_CLUSTERS="\"RUNNING\"" #APM-379036 different responses returned - to be fixed in bug APM-380143
  if ACTIVE_GATE_STATE=$(curl -ksS "${TARGET_URL}/rest/health" --connect-timeout 20 | tr -d '\r\n'); then
    if [[ "$ACTIVE_GATE_STATE" != "$RUNNING_RESPONSE_ON_NORMAL_CLUSTERS" ]] && [[ "$ACTIVE_GATE_STATE" != "$RUNNING_RESPONSE_ON_DOK_CLUSTERS"  ]]; then
      err "ActiveGate endpoint is not reporting RUNNING state. Please verify provided values for parameters: --target-url (${TARGET_URL})."
      exit 1
    fi
  else
      warn "Failed to connect with provided ActiveGate url ($TARGET_URL) to check state. It can be ignored if ActiveGate does not allow public access."
  fi
}

check_api_token() {
  if RESPONSE=$(curl -k -s -X POST -d "{\"token\":\"$TARGET_API_TOKEN\"}" "$TARGET_URL/api/v2/apiTokens/lookup" -w "<<HTTP_CODE>>%{http_code}" -H "accept: application/json; charset=utf-8" -H "Content-Type: application/json; charset=utf-8" -H "Authorization: Api-Token $TARGET_API_TOKEN" --connect-timeout 20); then
    CODE=$(sed -rn 's/.*<<HTTP_CODE>>(.*)$/\1/p' <<<"$RESPONSE")
    RESPONSE=$(sed -r 's/(.*)<<HTTP_CODE>>.*$/\1/' <<<"$RESPONSE")
    if [ "$CODE" -ge 300 ]; then
      err "Failed to check Dynatrace API token permissions - please verify provided values for parameters: --target-url (${TARGET_URL}) and --target-api-token. $RESPONSE"
      exit 1
    fi
    if ! grep -q '"logs.ingest"' <<<"$RESPONSE"; then
      err "Missing Ingest logs permission (v2) for the API token"
      exit 1
    fi
  else
      warn "Failed to connect to endpoint $TARGET_URL to check API token permissions. It can be ignored if Dynatrace/ActiveGate does not allow public access."
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
      err "Failed to send a test log to Dynatrace - please verify provided log ingest url ($TARGET_URL) and API token. $RESPONSE"
      exit 1
    fi
  else
    warn "Failed to connect to endpoint $TARGET_URL to check API token permissions. It can be ignored if Dynatrace/ActiveGate does not allow public access."
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

             "--event-hub-name")
                ensure_param_value_given $1 $2
                EVENT_HUB_NAME=$2
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

           "--enable-user-assigned-managed-identity")
                ensure_param_value_given $1 $2
                ENABLE_USER_ASSIGNED_MANAGED_IDENTITY=$2
                shift; shift
            ;;

            "--eventhub-connection-client-id")
                ensure_param_value_given $1 $2
                EVENT_HUB_CONNECTION_CLIENT_ID=$2
                shift; shift
            ;;

          "--managed-identity-resource-name")
                ensure_param_value_given $1 $2
                MANAGED_IDENTITY_RESOURCE_NAME=$2
                shift; shift
            ;;

           "--eventhub-connection-fully-qualified-namespace")
                ensure_param_value_given $1 $2
                EVENT_HUB_CONNECTION_FULLY_QUALIFIED_NAMESPACE=$2
                shift; shift
            ;;

            "--custom-consumer-group")
                ensure_param_value_given $1 $2
                CONSUMER_GROUP=$2
                shift; shift
            ;;

            *)
            err "Unknown param $1"
            print_help
            exit 1
    esac
done

if ! command -v az &> /dev/null; then

    err "Azure CLI is required to install Dynatrace function. It should be already installed in Cloud Shell."
    echo "If you are running this script from other hosts go to following link in your browser and install latest version of Azure CLI:"
    echo
    echo "https://docs.microsoft.com/en-us/cli/azure/install-azure-cli"
    echo
    exit
fi

if [ $(az version -o table |awk 'NR >= 3 {print $1}') == "2.29.0" ] &> /dev/null; then

    err "Version 2.29.0 of Azure CLI is subject to a bug which prevents Azure Log Forwarder setup from working properly."
    echo "You can find the bug description under the link bellow:"
    echo
    echo "https://github.com/Azure/azure-cli/issues/20131"
    echo
    echo "If you are running this script from other hosts go to following link in your browser and upgrade to a more recent version of Azure CLI:"
    echo
    echo "https://docs.microsoft.com/en-us/cli/azure/install-azure-cli"
    echo
    exit
fi

check_arg --deployment-name "$DEPLOYMENT_NAME" "$DEPLOYMENT_NAME_REGEX"
check_arg --resource-group "$RESOURCE_GROUP" ".+"
if [[ "$ENABLE_USER_ASSIGNED_MANAGED_IDENTITY" == "false" ]] || [[ -z "$ENABLE_USER_ASSIGNED_MANAGED_IDENTITY" ]]; then 
  check_arg --event-hub-connection-string "$EVENT_HUB_CONNECTION_STRING" "$EVENT_HUB_CONNECTION_STRING_REGEX"
fi
if [ -z "$REQUIRE_VALID_CERTIFICATE" ]; then REQUIRE_VALID_CERTIFICATE=$REQUIRE_VALID_CERTIFICATE_DEFAULT; fi
if [ -z "$SFM_ENABLED" ]; then SFM_ENABLED=false; fi

if [[ "$REQUIRE_VALID_CERTIFICATE" != "true" ]] && [[ "$REQUIRE_VALID_CERTIFICATE" != "false" ]]; then
  err "Not correct --require-valid-certificate. Provide 'true' or 'false'";
  exit 1;
fi
if [[ "$SFM_ENABLED" != "true" ]] && [[ "$SFM_ENABLED" != "false" ]]; then
  err "Not correct --enable-self-monitoring. Provide 'true' or 'false'";
  exit 1;
fi
if [[ -z "$USE_EXISTING_ACTIVE_GATE" ]]; then
  USE_EXISTING_ACTIVE_GATE="true"
elif [[ "$USE_EXISTING_ACTIVE_GATE" != "true" ]] && [[ "$USE_EXISTING_ACTIVE_GATE" != "false" ]]; then
  err "Not correct --use-existing-active-gate. Provide 'true' or 'false'";
  exit 1;
fi
if [[ -z "$ENABLE_USER_ASSIGNED_MANAGED_IDENTITY" ]]; then
  ENABLE_USER_ASSIGNED_MANAGED_IDENTITY="false"
elif [[ "$ENABLE_USER_ASSIGNED_MANAGED_IDENTITY" != "true" ]] && [[ "$ENABLE_USER_ASSIGNED_MANAGED_IDENTITY" != "false" ]]; then
  err "Not correct --enable-user-assigned-managed-identity. Provide 'true' or 'false'";
  exit 1;
fi

if [ -n "$FILTER_CONFIG" ]; then check_arg --filter-config "$FILTER_CONFIG" "$FILTER_CONFIG_REGEX";fi
if [ -n "$TAGS" ]; then check_arg --tags "$TAGS" "$TAGS_REGEX"; fi

if [ -z "$TARGET_URL" ]; then
  err "No --target-url"
  exit 1
else
  if [[ "$USE_EXISTING_ACTIVE_GATE" == "false" ]] && ! [[ "${TARGET_URL}" =~ $DYNATRACE_TARGET_URL_REGEX ]]; then
    err "Not correct --target-url. Example of proper url for deployment with new ActiveGate: https://<your_environment_ID>.live.dynatrace.com"
    exit 1
  elif [[ "$USE_EXISTING_ACTIVE_GATE" == "true" ]] && ! ([[ "${TARGET_URL}" =~ $ACTIVE_GATE_TARGET_URL_REGEX ]] || [[ "${TARGET_URL}" =~ $DYNATRACE_TARGET_URL_REGEX ]]); then
    err "Not correct --target-url. Example of proper url for deployment with existing ActiveGate:"
    echo "  - for direct ingest through the Cluster API: https://<your_environment_ID>.live.dynatrace.com"
    echo "  - for Environment ActiveGate: https://<your_activegate_IP_or_hostname>:9999/e/<your_environment_ID>"
    exit 1
  fi
fi

if [ -z "$TARGET_API_TOKEN" ]; then err "No --target-api-token"; exit 1; fi
if [[ "$USE_EXISTING_ACTIVE_GATE" == "false" ]] && [ -z "$TARGET_PAAS_TOKEN" ]; then err "No --target-paas-token"; exit 1; fi
if [[ "$USE_EXISTING_ACTIVE_GATE" == true ]]; then DEPLOY_ACTIVEGATE=false;else DEPLOY_ACTIVEGATE=true;fi
if [ -z "$REPOSITORY_RELEASE_URL" ]; then REPOSITORY_RELEASE_URL=${FUNCTION_REPOSITORY_RELEASE_URL}; fi
if [ -z "$CONSUMER_GROUP" ]; then CONSUMER_GROUP="\$Default"; fi
if [[ "$ENABLE_USER_ASSIGNED_MANAGED_IDENTITY" == "true" ]]; then
  EVENT_HUB_CONNECTION_CREDENTIALS="managedidentity";
  if [ -z "$EVENT_HUB_NAME" ]; then err "No --event-hub-name"; exit 1; fi
  if [ -z "$EVENT_HUB_CONNECTION_CLIENT_ID" ]; then err "No --eventhub-connection-client-id"; exit 1; fi
  if [ -z "$MANAGED_IDENTITY_RESOURCE_NAME" ]; then err "No --managed-identity-resource-name"; exit 1; fi
  if [ -z "$EVENT_HUB_CONNECTION_FULLY_QUALIFIED_NAMESPACE" ]; then err "No --eventhub-connection-fully-qualified-namespace"; exit 1; fi
fi

print_all_parameters

TARGET_URL=$(echo "$TARGET_URL" | sed 's:/*$::')

if [[ "${DEPLOY_ACTIVEGATE}" == "false" ]]; then
  check_activegate_state
fi

check_api_token

if [[ "${DEPLOY_ACTIVEGATE}" == "false" ]]; then
  check_dynatrace_log_ingest_url
fi

if [[ "$ENABLE_USER_ASSIGNED_MANAGED_IDENTITY" == "false" ]]; then
  EVENT_HUB_NAME=$(echo "$EVENT_HUB_CONNECTION_STRING" | awk -F ';EntityPath=' '{print $2}')
fi

log_step "Deploying function infrastructure into Azure..."

IFS=',' read -r -a TAG_PAIRS <<< "$TAGS"
LOG_FORWARDER_TAGS="\"LogsForwarderDeployment\":\"${DEPLOYMENT_NAME}\""
for TAG_PAIR in "${TAG_PAIRS[@]}"; do
  IFS=':' read -r -a TAG_KEY_VALUE <<< "$TAG_PAIR"
  LOG_FORWARDER_TAGS="${LOG_FORWARDER_TAGS},\"${TAG_KEY_VALUE[0]}\":\"${TAG_KEY_VALUE[1]}\""
done
LOG_FORWARDER_TAGS="{${LOG_FORWARDER_TAGS}}"

if [ "$ENABLE_USER_ASSIGNED_MANAGED_IDENTITY" = "true" ]; then
  az deployment group create \
  --resource-group ${RESOURCE_GROUP} \
  --template-uri ${REPOSITORY_RELEASE_URL}${FUNCTION_ARM} \
  --parameters forwarderName="${DEPLOYMENT_NAME}" \
  targetUrl="${TARGET_URL}" \
  targetAPIToken="${TARGET_API_TOKEN}" \
  eventHubName="${EVENT_HUB_NAME}" \
  requireValidCertificate=${REQUIRE_VALID_CERTIFICATE} \
  selfMonitoringEnabled="${SFM_ENABLED}" \
  deployActiveGateContainer="${DEPLOY_ACTIVEGATE}" \
  targetPaasToken="${TARGET_PAAS_TOKEN}" \
  filterConfig="${FILTER_CONFIG}" \
  resourceTags="${LOG_FORWARDER_TAGS}" \
  eventhubConnectionClientId="${EVENT_HUB_CONNECTION_CLIENT_ID}" \
  eventhubConnectionCredentials="${EVENT_HUB_CONNECTION_CREDENTIALS}" \
  eventhubConnectionFullyQualifiedNamespace="${EVENT_HUB_CONNECTION_FULLY_QUALIFIED_NAMESPACE}" \
  customConsumerGroup="${CONSUMER_GROUP}"
else
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
  resourceTags="${LOG_FORWARDER_TAGS}" \
  customConsumerGroup="${CONSUMER_GROUP}"
fi

if [[ $? != 0 ]]; then
    err "Function deployment failed"
    exit 2
fi

log_step "Downloading function code zip [${REPOSITORY_RELEASE_URL}${FUNCTION_ZIP_PACKAGE}]"
wget -q ${REPOSITORY_RELEASE_URL}${FUNCTION_ZIP_PACKAGE} -O ${FUNCTION_ZIP_PACKAGE}

FUNCTIONAPP_NAME="${DEPLOYMENT_NAME}-function"

log_step "Deploying function zip code into ${FUNCTIONAPP_NAME}"
info "Waiting (3min) to allow functionapp to warmup..."
sleep 180 # wait some time to allow functionapp to warmup

MAX_RETRIES=3
ATTEMPT=1
WEBAPP_DEPLOYMENT_LOG=azurewebapp-deployment.log
while [ $ATTEMPT -le $MAX_RETRIES ]; do
    info "Start of deployment. Attempt ${ATTEMPT}"

    rm $WEBAPP_DEPLOYMENT_LOG >/dev/null 2>&1
    set -o pipefail
    az webapp deploy -n ${FUNCTIONAPP_NAME} -g ${RESOURCE_GROUP} --src-path ${FUNCTION_ZIP_PACKAGE} --type zip --async true --verbose 2>&1 | tee $WEBAPP_DEPLOYMENT_LOG
    DEPLOYMENT_STATUS=$?
    set +o pipefail

    if [[ $DEPLOYMENT_STATUS -eq 0 ]]; then
      break
    else
      if grep "Status Code: 504" $WEBAPP_DEPLOYMENT_LOG && [ $ATTEMPT -lt $MAX_RETRIES ]; then
        warn "Timeout error detected. Retrying in 10 seconds..."
        sleep 10
      else
        err "Function code deployment failed"
        exit 3
      fi
    fi
    ((ATTEMPT++))
done

if [[ "$ENABLE_USER_ASSIGNED_MANAGED_IDENTITY" == "true" ]]; then
  MANAGED_IDENTITY_RESOURCE_ID=$(az identity show --name ${MANAGED_IDENTITY_RESOURCE_NAME} -g ${RESOURCE_GROUP} --query id --output tsv)
  az webapp identity assign  -n ${FUNCTIONAPP_NAME} -g ${RESOURCE_GROUP} --identities ${MANAGED_IDENTITY_RESOURCE_ID}
fi

if [[ $? != 0 ]]; then
    err "Function code deployment failed"
    exit 3
fi

log_step "Cleaning up"
rm $WEBAPP_DEPLOYMENT_LOG

log_step "Removing function package [$FUNCTION_ZIP_PACKAGE]"
rm $FUNCTION_ZIP_PACKAGE

if [[ "${DEPLOY_ACTIVEGATE}" == "true" ]]; then
  # To build Log viewer link we need Dynatrace url (available only in deployment with new ActiveGate or direct ingest through the Cluster API)
  # For deployment with existing ActiveGate (ActiveGate url is used as TARGET_URL) we are not able to build the link - LOG_VIEWER is empty then.
  LOG_VIEWER="Log Viewer: ${TARGET_URL}/ui/log-monitoring?query=cloud.provider%3D%22azure%22"
fi

success "Deployment complete. Check logs in Dynatrace in 10 min. ${LOG_VIEWER}"
info "If you won't see any Azure logs after that time make sure you configured all prerequisites: https://www.dynatrace.com/support/help/shortlink/azure-log-fwd#anchor_prereq"
info "Additionally you can enable self-monitoring for diagnostic purpose: https://www.dynatrace.com/support/help/shortlink/azure-log-fwd#self-monitoring-optional"

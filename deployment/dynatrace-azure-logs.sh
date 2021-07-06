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
readonly FUNCTION_REPOSITORY_RELEASE_URL=https://github.com/dynatrace-oss/dynatrace-azure-log-forwarder/releases/download/latest/
readonly DYNATRACE_TARGET_URL_REGEX="^https:\/\/[-a-zA-Z0-9@:%._+~=]{1,256}$"
readonly ACTIVE_GATE_TARGET_URL_REGEX="^https:\/\/[-a-zA-Z0-9@:%._+~=]{1,256}\/e\/[a-z0-9-]{1,36}$"
readonly DEPLOYMENT_NAME_REGEX="^[-a-z0-9]{3,20}$"
readonly RESOURCE_GROUP_REGEX="^[a-zA-Z0-9.()-]{1,90}$"
readonly EVENT_HUB_CONNECTION_STRING_REGEX="^Endpoint=sb:\/\/.*$"
readonly EVENT_HUB_NAME_REGEX="^[a-zA-Z0-9][a-zA-Z0-9.-]{1,50}$"
readonly FILTER_CONFIG_REGEX="([^;\s].+?)=([^;]*)"

print_help()
{
   printf "
usage: dynatrace-azure-logs.sh --deployment-name DEPLOYMENT_NAME --target-url TARGET_URL --target-api-token TARGET_API_TOKEN --resource-group RESOURCE_GROUP --event-hub-connection-string EVENT_HUB_CONNECTION_STRING --event-hub-name EVENT_HUB_NAME [--target-paas-token TARGET_PAAS_TOKEN] [--filter-config FILTER_CONFIG] [--use-existing-active-gate] [--require-valid-certificate] [--enable-self-monitoring]

arguments:
    -h, --help              Show this help message and exit
    -i, --interactive       Interactive mode
    --deployment-name DEPLOYMENT_NAME
                            e.g. \"dynatracelogs\", use lowercase only
    --use-existing-active-gate
                            Decide if you want to use existing ActiveGate. By default (if this option is not provided) ActiveGate will be deployed as container in Azure Container Instances.
    --target-url TARGET_URL
                            With ActiveGate deployment option set URL to your Dynatrace SaaS, otherwise set ActiveGate endpoint
    --target-api-token TARGET_API_TOKEN
                            Dynatrace API token. Integration requires API v1 Log import Token permission.
    --target-paas-token TARGET_PAAS_TOKEN
                            Dynatrace PaaS token, only when deploy ActiveGate is chosen
    --resource-group RESOURCE_GROUP   
                            Name of the Azure Resource Group in which Function will be deployed
    --event-hub-connection-string EVENT_HUB_CONNECTION_STRING
                            Connection string for Azure EventHub that is configured for receiving logs
    --event-hub-name EVENT_HUB_NAME
                            Name of Azure Event Hub configured for receiving logs
    --require-valid-certificate
                            Enables checking SSL certificate of the target Active Gate. By default (if this option is not provided) certificates aren't validated.
    --enable-self-monitoring
                            Self monitoring allows to diagnose quickly your function by Azure custom metrics. By default (if this option is not provided) custom metrics won't be sent to Azure.
    --filter-config
                            Apply filters to reduce number of logs that are sent to Dynatrace e.g. filter out logs with Informational level.
    "
}

print_all_parameters()
{
    PARAMETERS="DEPLOYMENT_NAME=$DEPLOYMENT_NAME, USE_EXISTING_ACTIVE_GATE=$USE_EXISTING_ACTIVE_GATE, TARGET_URL=$TARGET_URL, TARGET_API_TOKEN=*****, RESOURCE_GROUP=$RESOURCE_GROUP, EVENT_HUB_CONNECTION_STRING=*****, EVENT_HUB_NAME=$EVENT_HUB_NAME, REQUIRE_VALID_CERTIFICATE=$REQUIRE_VALID_CERTIFICATE, SFM_ENABLED=$SFM_ENABLED"
    if [[ "$USE_EXISTING_ACTIVE_GATE" == "false" ]];then PARAMETERS+=", TARGET_PAAS_TOKEN=*****";fi
    if [ ! -z "$FILTER_CONFIG" ];then PARAMETERS+=", FILTER_CONFIG=$FILTER_CONFIG";fi
    echo
    echo "Deployment script will use following parameters:"
    echo $PARAMETERS
}

check_arg()
{
    CLI_ARGUMENT_NAME=$1
    ARGUMENT=$2
    REGEX=$3
    if [ -z "$ARGUMENT" ]
    then
        echo "No $CLI_ARGUMENT_NAME"
        exit 1
    else
        if ! [[ "$ARGUMENT" =~ $REGEX ]]
        then
            echo "Not correct $CLI_ARGUMENT_NAME"
            exit 1
        fi
    fi
}

check_api_token() {
  if RESPONSE=$(curl -k -s -X POST -d "{\"token\":\"$TARGET_API_TOKEN\"}" "$TARGET_URL/api/v2/apiTokens/lookup" -w "<<HTTP_CODE>>%{http_code}" -H "accept: application/json; charset=utf-8" -H "Content-Type: application/json; charset=utf-8" -H "Authorization: Api-Token $TARGET_API_TOKEN"); then
    CODE=$(sed -rn 's/.*<<HTTP_CODE>>(.*)$/\1/p' <<<"$RESPONSE")
    RESPONSE=$(sed -r 's/(.*)<<HTTP_CODE>>.*$/\1/' <<<"$RESPONSE")
    if [ "$CODE" -ge 300 ]; then
      echo "Failed to check Dynatrace API token permissions - please verify provided values for parameters: --target-url and --target-api-token. $RESPONSE"
      exit 1
    fi
    if ! grep -q "logs.ingest" <<<"$RESPONSE"; then
      echo "Missing Ingest logs permission for the API token"
      exit 1
    fi
  else
      echo "Failed to check Dynatrace API token permissions - please verify provided values for parameters: --target-url and --target-api-token."
  fi
}

RUN_INTERACTIVE_MODE=false
while (( "$#" )); do
    case "$1" in
            "-h" | "--help")
                print_help
                exit 0
            ;;

            "-i" | "--interactive")
                RUN_INTERACTIVE_MODE=true
                shift
            ;;

            "--deployment-name")
                DEPLOYMENT_NAME=$2
                shift; shift
            ;;

            "--use-existing-active-gate")
                USE_EXISTING_ACTIVE_GATE=true
                shift
            ;;

            "--target-url")
                TARGET_URL=$2
                shift; shift
            ;;

            "--target-api-token")
                TARGET_API_TOKEN=$2
                shift; shift
            ;;

            "--target-paas-token")
                TARGET_PAAS_TOKEN=$2
                shift; shift
            ;;

            "--resource-group")
                RESOURCE_GROUP=$2
                shift; shift
            ;;

            "--event-hub-connection-string")
                EVENT_HUB_CONNECTION_STRING=$2
                shift; shift
            ;;

            "--event-hub-name")
                EVENT_HUB_NAME=$2
                shift; shift
            ;;

            "--filter-config")
                FILTER_CONFIG=$2
                shift; shift
            ;;

            "--require-valid-certificate")
                REQUIRE_VALID_CERTIFICATE=true
                shift
            ;;

            "--enable-self-monitoring")
                SFM_ENABLED=true
                shift
            ;;

            *)
            echo "Unknown param $1"
            print_help
            exit 1
    esac
done

if ! $RUN_INTERACTIVE_MODE
then
    check_arg --deployment-name "$DEPLOYMENT_NAME" "$DEPLOYMENT_NAME_REGEX"
    check_arg --resource-group "$RESOURCE_GROUP" "$RESOURCE_GROUP_REGEX"
    check_arg --event-hub-connection-string "$EVENT_HUB_CONNECTION_STRING" "$EVENT_HUB_CONNECTION_STRING_REGEX"
    check_arg --event-hub-name "$EVENT_HUB_NAME" "$EVENT_HUB_NAME_REGEX"
    if [ ! -z "$FILTER_CONFIG" ]; then check_arg --filter-config "$FILTER_CONFIG" "$FILTER_CONFIG_REGEX";fi

    if [ -z "$USE_EXISTING_ACTIVE_GATE" ]; then USE_EXISTING_ACTIVE_GATE=false; fi
    if [ -z "$TARGET_URL" ]
    then
        echo "No --target-url"
        exit 1
     else
        if [[ "$USE_EXISTING_ACTIVE_GATE" == "false" ]] && ! [[ "${TARGET_URL}" =~ $DYNATRACE_TARGET_URL_REGEX ]]
        then
            echo "Not correct --target-url. Example of proper url for deployment with ActiveGate: https://environment-id.live.dynatrace.com"
            exit 1
        elif [[ "$USE_EXISTING_ACTIVE_GATE" == "true" ]] && ! [[ "${TARGET_URL}" =~ $ACTIVE_GATE_TARGET_URL_REGEX ]]
        then
            echo "Not correct --target-url. Example of proper url for deployment without ActiveGate: https://environemnt-active-gate-url:9999/e/environment-id"
            exit 1
        fi
    fi

    if [ -z "$TARGET_API_TOKEN" ]; then echo "No --target-api-token"; exit 1; fi
    if [[ "$USE_EXISTING_ACTIVE_GATE" == "false" ]] && [ -z "$TARGET_PAAS_TOKEN" ]; then echo "No --target-paas-token"; exit 1; fi
    if [ -z "$REQUIRE_VALID_CERTIFICATE" ]; then REQUIRE_VALID_CERTIFICATE=false; fi
    if [ -z "$SFM_ENABLED" ]; then SFM_ENABLED=false; fi
    if [[ "$USE_EXISTING_ACTIVE_GATE" == true ]]; then DEPLOY_ACTIVEGATE=false;else DEPLOY_ACTIVEGATE=true;fi
    print_all_parameters

else
    echo -e "\033[1;34mDynatrace function for Azure logs ingest"
    echo -e "\033[0;37m"

    if ! command -v az &> /dev/null
    then

        echo -e "\e[93mWARNING: \e[37mAzure CLI is required to install Dynatrace function. It should be already installed in Cloud Shell."
        echo -e "If you are running this script from other hosts go to following link in your browser and install latest version of Azure CLI:"
        echo -e
        echo -e "https://docs.microsoft.com/en-us/cli/azure/install-azure-cli"
        echo -e
        echo
        exit
    fi


    echo "Function will be deployed into active subscription:"
    az account list -o table | grep 'Enabled  True'
    if [[ $? != 0 ]]
    then
        echo "Exiting, please run azure cli login, set active subscription by running \"az account set --subscription <id>\" and rerun installation"
        exit 1
    fi

    echo ""
    while ! [[ "${CONTINUE}" =~ ^(Y|N)$ ]]; do
        read -p "Continue? Y/N: " -i Y -e CONTINUE
    done
    echo ""

    if [[ "${CONTINUE}" == "N" ]]
    then
        echo "Exiting, please set active subscription running \"az account set --subscription <id>\" and rerun installation"
        exit 1
    fi


    echo "Please provide the name for this Dynatrace Logs Forwarder deployment, for example: dynatracelogs"
    while ! [[ "${DEPLOYMENT_NAME}" =~ $DEPLOYMENT_NAME_REGEX ]]; do
        read -p "Enter name (only lowercase letters and numbers, 3 to 20 characters): " DEPLOYMENT_NAME
    done
    echo ""

    echo "Do you want to have Dynatrace ActiveGate added as part of this deployment?"
    echo "ActiveGate will be deployed as container in Azure Container Instances"
    echo "Y - Yes"
    echo "N - No, select this option if you already have Dynatrace ActiveGate installed and configured for logs ingest"
    while ! [[ "${DEPLOY_ACTIVEGATE}" =~ ^(Y|N)$ ]]; do
        read -p "Deploy Dynatrace ActiveGate?: " -i Y -e DEPLOY_ACTIVEGATE
    done
    echo ""

    case ${DEPLOY_ACTIVEGATE} in
    Y)
        DEPLOY_ACTIVEGATE=true
        ;;
    N)
        DEPLOY_ACTIVEGATE=false
        ;;
    *)
        echo "DEPLOY_ACTIVEGATE - unexpected option value"
        exit 1
        ;;
    esac

    if [[ "${DEPLOY_ACTIVEGATE}" == "false" ]]
    then
        echo "Please provide the endpoint used to ingest logs to Dynatrace, for example: https://environemnt-active-gate-url:9999/e/environment-id"
        while ! [[ "${TARGET_URL}" =~ $ACTIVE_GATE_TARGET_URL_REGEX ]]; do
            read -p "Enter Dynatrace ActiveGate API URI: " TARGET_URL
        done
        echo ""

        echo "Please specify whether SSL certificate of endpoint used to ingest logs to Dynatrace should be verified"
        echo "Y - Yes"
        echo "N - No, select this option for ActiveGates with self-signed SSL certificate"
        while ! [[ "${REQUIRE_VALID_CERTIFICATE}" =~ ^(Y|N)$ ]]; do
            read -p "Verify SSL certificate?: " -i N -e REQUIRE_VALID_CERTIFICATE
        done
        echo ""
    else
        REQUIRE_VALID_CERTIFICATE="N"

        echo "Please provide the dynatrace environment endpoint, for example: https://environment-id.live.dynatrace.com"
        while ! [[ "${TARGET_URL}" =~ $DYNATRACE_TARGET_URL_REGEX ]]; do
            read -p "Enter Dynatrace environment URI: " TARGET_URL
        done
        echo ""

        echo "Please log in to Dynatrace, and generate PaaS token (Settings->Integration->Platform as a Service)"
        while ! [[ "${TARGET_PAAS_TOKEN}" != "" ]]; do
            read -p "Enter Dynatrace PaaS token: " TARGET_PAAS_TOKEN
        done
        echo ""
    fi


    case $REQUIRE_VALID_CERTIFICATE in
    Y)
        REQUIRE_VALID_CERTIFICATE=true
        ;;
    N)
        REQUIRE_VALID_CERTIFICATE=false
        ;;
    *)
        echo "REQUIRE_VALID_CERTIFICATE - unexpected option value"
        exit 1
        ;;
    esac

    echo "Please log in to Dynatrace, and generate API token (Settings->Integration->Dynatrace API). The token requires grant of 'API v1 Log import' scope"
    while ! [[ "${TARGET_API_TOKEN}" != "" ]]; do
        read -p "Enter Dynatrace API token: " TARGET_API_TOKEN
    done
    echo ""

    echo "Do you want to have Dynatrace function self monitoring metrics reported?"
    echo "Y - Yes"
    echo "N - No"
    while ! [[ "${SFM_ENABLED}" =~ ^(Y|N)$ ]]; do
        read -p "Enable self-monitoring metrics?: " -i N -e SFM_ENABLED
    done
    echo ""

    case $SFM_ENABLED in
    Y)
        SFM_ENABLED=true
        ;;
    N)
        SFM_ENABLED=false
        ;;
    *)
        echo "SFM_ENABLED - unexpected option value"
        exit 1
        ;;
    esac

    echo "Please provide the name of Azure resource group to deploy Dynatrace function into"
    while ! [[ "${RESOURCE_GROUP}" =~ $RESOURCE_GROUP_REGEX ]]; do
        read -p "Enter Azure Resource Group name: " RESOURCE_GROUP
    done
    echo ""

    echo "Please provide the EventHub connection string to read log events from"
    while ! [[ "${EVENT_HUB_CONNECTION_STRING}" =~ $EVENT_HUB_CONNECTION_STRING_REGEX ]]; do
        read -p "Enter EventHub connection string: " EVENT_HUB_CONNECTION_STRING
    done
    echo ""

    echo "Please provide the Event Hub name"
    while ! [[ "${EVENT_HUB_NAME}" =~ $EVENT_HUB_NAME_REGEX ]]; do
        read -p "Enter EventHub name: " EVENT_HUB_NAME
    done
    echo ""

    echo "Do you want to apply Filter Config?"
    echo "Y - Yes"
    echo "N - No"
    while ! [[ "${APPLY_FILTER_CONFIG}" =~ ^(Y|N)$ ]]; do
        read -p "Apply Filter Config?: " -i N -e APPLY_FILTER_CONFIG
    done
    echo ""

    case ${APPLY_FILTER_CONFIG} in
    Y)
        APPLY_FILTER_CONFIG=true
        ;;
    N)
        APPLY_FILTER_CONFIG=false
        ;;
    *)
        echo "APPLY_FILTER_CONFIG - unexpected option value"
        exit 1
        ;;
    esac

    if [[ "${APPLY_FILTER_CONFIG}" == "true" ]]
    then
      echo "Please provide filter config in key-value pair format for example: FILTER.GLOBAL.MIN_LOG_LEVEL=Warning"
      while ! [[ "${FILTER_CONFIG}" =~ $FILTER_CONFIG_REGEX ]]; do
          read -p "Enter filter config: " FILTER_CONFIG
      done
      echo ""
    fi
fi


echo
check_api_token
echo "- deploying function infrastructure into Azure..."

az deployment group create \
--resource-group ${RESOURCE_GROUP} \
--template-uri ${FUNCTION_REPOSITORY_RELEASE_URL}${FUNCTION_ARM} \
--parameters forwarderName="${DEPLOYMENT_NAME}" \
targetUrl="${TARGET_URL}" \
targetAPIToken="${TARGET_API_TOKEN}" \
eventHubConnectionString="${EVENT_HUB_CONNECTION_STRING}" \
eventHubName="${EVENT_HUB_NAME}" \
requireValidCertificate=${REQUIRE_VALID_CERTIFICATE} \
selfMonitoringEnabled="${SFM_ENABLED}" \
deployActiveGateContainer="${DEPLOY_ACTIVEGATE}" \
targetPaasToken="${TARGET_PAAS_TOKEN}" \
filterConfig="${FILTER_CONFIG}"

if [[ $? != 0 ]]
then
    echo "Function deployment failed"
    exit 2
fi

echo
echo "- downloading function code zip [${FUNCTION_REPOSITORY_RELEASE_URL}${FUNCTION_ZIP_PACKAGE}]"
wget -q ${FUNCTION_REPOSITORY_RELEASE_URL}${FUNCTION_ZIP_PACKAGE} -O ${FUNCTION_ZIP_PACKAGE}

FUNCTIONAPP_NAME="${DEPLOYMENT_NAME}-function"
echo
echo "- deploying function zip code into ${FUNCTIONAPP_NAME}..."

sleep 60 # wait some time to allow functionapp to warmup

az webapp deployment source config-zip  -n ${FUNCTIONAPP_NAME} -g ${RESOURCE_GROUP} --src ${FUNCTION_ZIP_PACKAGE}

if [[ $? != 0 ]]
then
    echo "Function code deployment failed"
    exit 3
fi

echo "- cleaning up"

echo "- removing function package [$FUNCTION_ZIP_PACKAGE]"
rm $FUNCTION_ZIP_PACKAGE

echo "Done"

# Dynatrace Azure Log Forwarder
## Overview
This project provides mechanism that allows to stream Azure logs from Azure Event Hub into Dynatrace Logs via Azure Function App. 
It supports both: Azure Resource Logs and Azure Activity Logs.

Prerequisites:
* Azure CLI - if you run deployment script from your machine (not needed when using Azure Portal Cloud Shell) [https://docs.microsoft.com/en-us/cli/azure/install-azure-cli](https://docs.microsoft.com/en-us/cli/azure/install-azure-cli)
* running Azure Event Hub(s) instance(s) in each Azure location you want to pull logs from 
* configured `diagnostic settings` for resources you would like to stream logs from, pointing to Even Hub(s) (reference [https://docs.microsoft.com/en-us/azure/azure-monitor/essentials/diagnostic-settings](https://docs.microsoft.com/en-us/azure/azure-monitor/essentials/diagnostic-settings))


*Architecture*

azure-log-forwarder-function is an Azure Function App written in Python that pulls logs for configured services. Function execution is triggered by Azure Event Hub. When all log records are processed, they are pushed to Dynatrace Logs API.   

`azure-log-forwarder` (with containerized ActiveGate)  components:
* `azure-log-forwarder-function` - function app that subscribes to one Event Hub which is in the same location where you deploy azure-log-forwarder; deployment with App Service Plan and minimum `S1 Standard` pricing tier 
* `azure-log-forwarder-container` - container instances that provides Dynatrace ActiveGate proxy to Dynatrace Infrastructure. This is Azure Container Instance with 1 core, 1.5 GB ram assigned
* `azure-log-forwarder-vnet` - virtual network to ensure private communication between function and active-gate

You need to deploy azure-log-forwarder in each region you want to pull logs from.

![Architecture](./img/architecture.png)


## Deployment
There are two deployment options:

Deployment can be run from Azure Portal Cloud Shell (Bash) or from any machine with Azure CLI and bash shell (Linux or Windows WSL) installed.

1. Deployment of log forwarder function and containerized ActiveGate - choose if you don't have ActiveGate configured for logs ingest.
    
    * Deployment script creates Virtual Network, Function App, deploys azure-log-forwarder and ActiveGate as container in Azure Container Instances. 

2. Deployment of log forwarder function only - choose if you have already running ActiveGate.

    * This option does not create virtual network. If you use one, just create new subnet for Function App with subnet delegation to Microsoft.Web/serverFarms and Service endpoint for Microsoft.Storage (Event Hub triggered function app needs storage account to run).   


### Download & run the azure-log-forwarder deployment script

Download deployment script:
```shell script
wget -q https://github.com/dynatrace-oss/dynatrace-azure-log-forwarder/releases/download/latest/dynatrace-azure-logs.sh -O dynatrace-azure-logs.sh && chmod +x ./dynatrace-azure-logs.sh
```

You have two options to run deployment script:
1. Run deployment script with CLI arguments. 
* You can also export environment variables before running deployment - the script will use them
* CLI arguments override environment variables
```shell script
./dynatrace-azure-logs.sh --deployment-name DEPLOYMENT_NAME --target-url TARGET_URL --target-api-token TARGET_API_TOKEN --resource-group RESOURCE_GROUP --event-hub-connection-string EVENT_HUB_CONNECTION_STRING --event-hub-name EVENT_HUB_NAME [--target-paas-token TARGET_PAAS_TOKEN] [--use-existing-active-gate] [--require-valid-certificate] [--enable-self-monitoring]
```
or
```shell script
export DEPLOYMENT_NAME="deployment-name"
export USE_EXISTING_ACTIVE_GATE="false"
export TARGET_PAAS_TOKEN="dt0c01.**************************"
export TARGET_API_TOKEN="dt0c01.**************************"
export RESOURCE_GROUP="resource-group"
export EVENT_HUB_CONNECTION_STRING="Endpoint=sb://*******.servicebus.windows.net/;SharedAccessKeyName=*******;SharedAccessKey=*******"
export EVENT_HUB_NAME="event-hub-name"
export SFM_ENABLED="false"
export TARGET_URL="https://your.dynatrace.environment.com"

./dynatrace-azure-logs.sh
```

2. Run deployment with interactive mode by passing -i/--interactive argument; script will prompt for all needed parameters.
```shell script
./dynatrace-azure-logs.sh -i
```

<center>

| Parameter  | Environment variable | Description                                | Required | Default value |
| -----------|-----------------------|---------------------------------------------|:----------:|:------------:|  
| --deployment-name | DEPLOYMENT_NAME | e.g. "dynatracelogs", use lowercase only | Yes | - |
| --use-existing-active-gate | USE_EXISTING_ACTIVE_GATE | Decide if you want to use existing ActiveGate. By default (if this option is not provided) ActiveGate will be deployed as container in Azure Container Instances. | No | false |
| --target-url | TARGET_URL | If you have chosen deploy ActiveGate option set the URL to your Dynatrace SaaS environment logs ingest target (e.g. https://mytenant.live.dynatrace.com). Otherwise set ActiveGate endpoint: https://<active_gate_address>:9999/e/<environment_id> (e.g. https://22.111.98.222:9999/e/abc12345). Make sure that Target URL is not ended with '/' | Yes | - |
| --require-valid-certificate | REQUIRE_VALID_CERTIFICATE | Enables checking SSL certificate of the target Active Gate. By default (if this option is not provided) certificates aren't validated. | No | false |
| --target-paas-token | TARGET_PAAS_TOKEN | Dynatrace PaaS token generated in Settings->Integration->Platform as a Service. Parameter required for deployment with containerized ActiveGate | Yes/No | - |
| --target-api-token | TARGET_API_TOKEN | Dynatrace API token. You can learn how to generate token [Dynatrace API - Tokens and authentication](https://www.dynatrace.com/support/help/dynatrace-api/basics/dynatrace-api-authentication) manually. Integration requires 'API v1 Log import' token permission. | Yes | - |
| --enable-self-monitoring | SFM_ENABLED | Send custom metrics to Azure. To use it remember to set up Managed identity for Function App (more details in Self-monitoring section). Self monitoring allows to diagnose quickly if your function processes and sends logs to Dynatrace properly. By default (if this option is not provided) custom metrics won't be sent to Azure. | No | false | 
| --resource-group | RESOURCE_GROUP | Name of the Azure Resource Group in which Function will be deployed. To create new one run: `az group create --name <resource_group> --location <region>` | Yes | - |
| --event-hub-connection-string | EVENT_HUB_CONNECTION_STRING | Connection string for Azure EventHub that is configured for receiving logs. You can create policy in Event Hub Namespace -> Event Hub -> Shared Access policies (listen permission is required). More info here: [https://docs.microsoft.com/en-us/azure/event-hubs/event-hubs-get-connection-string](https://docs.microsoft.com/en-us/azure/event-hubs/event-hubs-get-connection-string) | Yes | - |
| --event-hub-name | EVENT_HUB_NAME | Name of Azure Event Hub configured for receiving logs  | Yes | - |

</center>

### Update Dynatrace Log Forwarder code
You can download latest azure-log-forwarder zip from:
``` 
wget https://github.com/dynatrace-oss/dynatrace-azure-log-forwarder/releases/download/latest/dynatrace-azure-log-forwarder.sh
``` 
To deploy new version of azure-log-forwarder run:
```  
az webapp deployment source config-zip -g <resource_group> -n <app_name> --src <zip_file_path>
```

### Uninstall Dynatrace Log Forwarder
To uninstall Dynatrace Log Forwarder simply delete all Azure resources with DEPLOYMENT_NAME prefix from Azure Resource Group that was used for deployment.
Uninstallation script will be added soon.

## Viewing Azure logs in Dynatrace UI
You can view and analyze Azure logs in Dynatrace UI: Analyze -> Logs. To narrow view to Azure logs only use query: `cloud.provider: azure`

## Self-monitoring

### Azure Authentication
Managed identity from Azure Active Directory (AD) is used to authenticate to Azure. It allows an app to easily access other Azure AD-protected resources.

To use Managed identity for Function App, after deployment of azure-log-forwarder is finished you need to add a system-assigned identity. 
In the portal you need to go to Settings section of Function App and select Identity. Within the System assigned tab, switch Status to On.
One more step is left - in Azure role assignments you need to grant permission **Monitoring Metrics Publisher** to Resource Group where Function App is deployed.

More info here: [How to use managed identities for App Service and Azure Functions](https://docs.microsoft.com/en-us/azure/app-service/overview-managed-identity?tabs=dotnet)

### Self-monitoring metrics

Namespace: dynatrace_logs_self_monitoring

| Metric name     | Description                               | Dimension | 
| ----------------|--------------------------------------------|:----------:|
| too_old_records | Reported when logs received from Event Hub are too old | - |
| too_long_content_size | Reported when content of log is too long. The content will be trimmed | - |
| parsing_errors | Reported when any parsing errors occurred during log processing | - |
| processing_time | Time needed to process all logs | - |
| sending_time | Time needed to send all requests | - |
| all_requests | All requests sent to Dynatrace | - |
| dynatrace_connectivity_failures | Reported when any Dynatrace connectivity issues occurred | connectivity_status |

## License

`dynatrace-azure-log-forwarder` is under Apache 2.0 license. See [LICENSE](LICENSE.md) for details.
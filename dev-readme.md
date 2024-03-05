# azure-log-forwarder

## Run functions locally
Prerequisites:
* Visual Studio Code
* Azure Functions extension for VS Code
* [Azure Functions Core Tools](https://www.npmjs.com/package/azure-functions-core-tools) - version 2.x or later
* Python 3.9
* Python extension for VS Code

Open dynatrace-azure-logs-ingest folder in VS Code. You will be prompted to initialize it for use with VS Code. This will create several files in the ".vscode" folder at the root of your project. 

### local.settings.json
local.settings.json file corresponds with application settings of Azure Function App. These settings are used only when you are running function locally. The function can access them as environment variables. You need to put proper values for them.

```json
{
  "IsEncrypted": false,
  "Values": {
    "AzureWebJobsStorage": "UseDevelopmentStorage=true",
    "FUNCTIONS_WORKER_RUNTIME": "python",
    "EVENTHUB_CONNECTION_STRING": "",
    "EVENTHUB_NAME": "",
    "DYNATRACE_URL": "",
    "DYNATRACE_ACCESS_KEY": "",
    "REQUIRE_VALID_CERTIFICATE": "False"
  }
}
```

| Values | Description | Default |
| ------- | ----------- |----------- |
| AzureWebJobsStorage | Contains the connection string for an Azure storage account. More details about Storage Account below. | |
| EVENTHUB_CONNECTION_STRING | Connection string can be found in Azure portal in Shared access policies of EventHub Namespace | |
| DYNATRACE_URL | ActiveGate log_analytics_collector url e.g. https://52.157.98.106:9999/e/jxw01498 | |
| DYNATRACE_ACCESS_KEY | API token with `Log import` scope | |
| REQUIRE_VALID_CERTIFICATE | Set to False to accept self-signed certificates| false |
| SELF_MONITORING_ENABLED | If you want to send self monitoring metrics to Azure set to True. Add two more values in local.settings.json: REGION (where function app is deployed) and RESOURCE_ID of Function App. Remember to login to Azure CLI and 'Monitoring Metrics Publisher' role assignment - see 'Self monitoring' section. | False |
| DYNATRACE_LOG_INGEST_CONTENT_MAX_LENGTH | Max length of Content of single log line. If it surpasses server limit, Content will be truncated | 8192 |
| DYNATRACE_LOG_INGEST_ATTRIBUTE_VALUE_MAX_LENGTH | Max length of log event attribute value. If it surpasses server limit, Content will be truncated | 250 |
| DYNATRACE_LOG_INGEST_REQUEST_MAX_EVENTS | Max number of log events in single payload to logs ingest endpoint. If it surpasses server limit, payload will be rejected with 413 code  | 5000 |
| DYNATRACE_LOG_INGEST_REQUEST_MAX_SIZE | Max size in bytes of single payload to logs ingest endpoint. If it surpasses server limit, payload will be rejected with 413 code  | 1048576 (1 mb) |
| DYNATRACE_LOG_INGEST_MAX_RECORD_AGE | Max allowed age of record. Older records will be discarded. If it surpasses server limit, payload will be rejected with 400 code  | 86340 (1 day) |

### Storage Account
Required when using triggers other than HTTP. 
The emulator is useful during development, but you should test with an actual storage connection before deployment (just put connection string to real Storage Account created in Azure Portal in AzureWebJobsStorage property).

When you install emulator you can set AzureWebJobsStorage to UseDevelopmentStorage=true, Core Tools will use the emulator. 

#### Azure Storage Emulator (for Windows only)
The Azure Storage Emulator **is no longer being actively developed**. See current emulator **Azurite** below.

The Storage Emulator is available as part of the Microsoft Azure SDK. You can also install the Storage Emulator by using the standalone installer (available here: [Azure Storage Emulator](https://docs.microsoft.com/en-us/azure/storage/common/storage-use-emulator)).
To run Storage Emulator you need also SQL Server or LocalDB installed locally.

#### Azurite
The Azurite is an open-source emulator. It provides cross-platform support on Windows, Linux, and macOS.
You can install Azurite in Visual Studio Code as an extension. 
After that you can run the emulator by typing the command `Azurite: Start` in the VS Code command pallete. 
More info: [Use the Azurite emulator for local Azure Storage development](https://docs.microsoft.com/pl-pl/azure/storage/common/storage-use-azurite#install-and-run-the-azurite-visual-studio-code-extension.)

### function.json
The function.json file defines the function's trigger, bindings, and other configuration settings. Every function has one and only one trigger. The runtime uses this config file to determine the events to monitor and how to pass data into and return data from a function execution.
**Value for connection property must correspond with name of environemnt variable declared in local.settings.json and application settings.**

### host.json
The host.json metadata file contains global configuration options that affect all functions for a function app. It is located in a root project folder. More info: [host.json](https://docs.microsoft.com/en-us/azure/azure-functions/functions-host-json)


 
## Deployment of infrastructure (only once)
* create resource group `az group create --name <resource_group> --location <region`
e.g. `az group create --name ExampleGroup --location "Central US"`
* deploy ARM template into group:
```
az deployment group create `
  --name <deployment_name> `
  --resource-group <resource_group> `
  --template-file dynatracelogsforwarder.json `
  --parameters forwarderName=<resources_names_prefix>,`
targetUrl=<dynatrace_endpoint>,`
targetAPIToken=<dynatrace_api_token,`
eventHubConnectionString=<azure_eventhub_connection_string>,`
eventHubName=<azure_event_hub_name>` 
```
TODO in final version --template-uri param (pointing to github uri) will be used

e.g.:
```
az deployment group create `
  --name LogsForwarderDeployment `
  --resource-group ExampleGroup `
  --template-file dynatracelogsforwarder.json `
  --parameters forwarderName="dyntracelogs",`
targetUrl="https://11.22.33.44:9999/e/abc12345",`
targetAPIToken="dt0c01.5KXXXXXXXX.5AXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX",`
eventHubConnectionString="Endpoint=sb://eventhub.servicebus.windows.net/;SharedAccessKeyName=policy-for-logs-ingest;SharedAccessKey=1A2B3CXXXXX=;EntityPath=eventhubname",`
eventHubName="eventhubname"` 
```

## Function deployment

1. VS Code
With VS Code you can easily deploy your function to an existing Azure Function App or just create new one. 
Choose the Azure icon in the Activity bar. In the Functions section, choose the "Deploy to function app..." button. Then you need to provide some informations at the prompts and after that your function will be deployed in Azure.

2. .zip
To deploy .zip to your Azure Function App run:
```  
az functionapp deployment source config-zip -g <resource_group> -n <app_name> --src <zip_file_path> --build-remote
```

### .funcignore:
Declares files that shouldn't get published to Azure. Usually, this file contains .vscode/ , .venv/ , tests/ and local.settings.json (to prevent local app settings being published).


## Unit Testing
Install pytest inside your .venv Python virtual environment and run pytest tests to check the test results.
``` 
pip install pytest
pytest tests
``` 

## Self monitoring
In production to authenticate to Azure we use a managed identity from Azure Active Directory (AD) that allows an app to easily access other Azure AD-protected resources.
In dev we authenticate by requesting a token from the Azure CLI - you need to login to Azure CLI first:
```
az login
az account set --subscription <subscription_id>
```

Get object id for current sign-in user:
```
az ad signed-in-user show
```

Assign Monitoring Metrics Publisher role:
```
az role assignment create --assignee <object_id> --role 'Monitoring Metrics Publisher' --scope subscriptions/<subscription_id>
```

Check if the role was assigned:
```
az role assignment list --assignee <object_id>
```

You can find more informations in Azure documentation: 
* [Develop Azure Functions by using Visual Studio Code](https://docs.microsoft.com/en-us/azure/azure-functions/functions-develop-vs-code?tabs=csharp#prerequisites)
* [Azure Functions Python developer guide](https://docs.microsoft.com/en-us/azure/azure-functions/functions-reference-python)
* [Quickstart: Create a function in Azure with Python using Visual Studio Code](https://docs.microsoft.com/pl-pl/azure/azure-functions/create-first-function-vs-code-python)
* [Troubleshoot Python errors in Azure Functions](https://docs.microsoft.com/en-us/azure/azure-functions/recover-python-functions?tabs=vscode#troubleshoot-cannot-import-cygrpc)


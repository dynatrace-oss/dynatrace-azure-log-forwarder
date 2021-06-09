# Dynatrace Azure Log Forwarder
## Overview
 This project provides a mechanism that allows streaming Azure logs from Azure Event Hub into Dynatrace Logs via Azure Function App. It supports both: Azure Resource Logs and Azure Activity Logs.


## Prerequisites
Please refer to [Prerequisites](https://www.dynatrace.com/support/help/shortlink/azure-log-fwd#prerequisites-).
 
## Deployment
Please refer  to [Dynatrace log forwarder](https://www.dynatrace.com/support/help/shortlink/azure-log-fwd).

## Viewing Azure logs in Dynatrace UI
Please refer to [How to view Azure logs](https://www.dynatrace.com/support/help/shortlink/azure-log-fwd#view-azure-logs).

## Self-monitoring
Please refer to [Self-monitoring](https://www.dynatrace.com/support/help/shortlink/azure-log-fwd#self-monitoring-optional).

## Pricing
 Ingested logs will consume DDUs. For more details: 
  - [Azure service monitoring consumption](https://www.dynatrace.com/support/help/reference/monitoring-consumption-calculation/#expand-azure-service-monitoring-consumption-103)
  - [How to calculate consumption](https://www.dynatrace.com/support/help/reference/monitoring-consumption-calculation/log-monitoring-consumption/)

## Additional resources
- [Architecture](Architecture.md)
- [Dynatrace GCP function](https://github.com/dynatrace-oss/dynatrace-gcp-function)
- [Dynatrace AWS log forwarder](https://github.com/dynatrace-oss/dynatrace-aws-log-forwarder)

## Issues 
### Virtual Network cleanup

You may encounter issue with removing Virtual Network created for containerised Active Gate. Due to unresolved Azure bug, related sub-resource (Network Profile) is not deleted correctly. To remove the Virtual Network, first run cli command:

```shell script
az network profile delete --name {DEPLOYMENT_NAME}networkProfile --resource-group <resource-group-name>
```

Then retry removing the VNet from Azure Portal



# License

`dynatrace-azure-log-forwarder` is under Apache 2.0 license. See [LICENSE](LICENSE.md) for details.

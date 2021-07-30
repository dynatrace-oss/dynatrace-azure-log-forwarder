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

from . import logging

from azure.identity import ChainedTokenCredential, ManagedIdentityCredential, AzureCliCredential


def get_azure_token():
    credential_chain = ChainedTokenCredential(ManagedIdentityCredential(), AzureCliCredential())
    try:
        token = credential_chain.get_token("https://monitoring.azure.com//.default")
        return token.token
    except Exception as e:
        logging.exception(f"Failed to retrieve Azure token. Reason is {type(e).__name__} {e}",
                          "azure-token-retrieval-exception")
        return None

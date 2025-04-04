import demistomock as demisto
import urllib3
from CommonServerPython import *
from MicrosoftApiModule import *  # noqa: E402

from CommonServerUserPython import *

urllib3.disable_warnings()

API_VERSION = "2022-09-01"
GRANT_BY_CONNECTION = {
    "Device Code": DEVICE_CODE,
    "Authorization Code": AUTHORIZATION_CODE,
    "Client Credentials": CLIENT_CREDENTIALS,
}
SCOPE_BY_CONNECTION = {
    "Device Code": "https://management.azure.com/user_impersonation offline_access user.read",
    "Authorization Code": "https://management.azure.com/.default",
    "Client Credentials": "https://management.azure.com/.default",
}
PREFIX_URL = "https://management.azure.com/subscriptions/"


class ASClient:
    def __init__(
        self,
        app_id: str,
        subscription_id: str,
        resource_group_name: str,
        verify: bool,
        proxy: bool,
        connection_type: str,
        tenant_id: str = None,
        enc_key: str = None,
        auth_code: str = None,
        redirect_uri: str = None,
        managed_identities_client_id: str = None,
    ):
        if "@" in app_id:
            app_id, refresh_token = app_id.split("@")
            integration_context = get_integration_context()
            integration_context.update(current_refresh_token=refresh_token)
            set_integration_context(integration_context)

        client_args = assign_params(
            self_deployed=True,
            auth_id=app_id,
            token_retrieval_url="https://login.microsoftonline.com/organizations/oauth2/v2.0/token"
            if "Device Code" in connection_type
            else None,
            grant_type=GRANT_BY_CONNECTION.get(connection_type),
            base_url=f"{PREFIX_URL}{subscription_id}",
            verify=verify,
            proxy=proxy,
            resource="https://management.core.windows.net" if "Device" in connection_type else None,
            scope=SCOPE_BY_CONNECTION.get(connection_type),
            tenant_id=tenant_id,
            enc_key=enc_key,
            auth_code=auth_code,
            redirect_uri=redirect_uri,
            managed_identities_client_id=managed_identities_client_id,
            managed_identities_resource_uri=Resources.management_azure,
            command_prefix="azure-storage",
        )
        self.ms_client = MicrosoftClient(**client_args)
        self.subscription_id = subscription_id
        self.resource_group_name = resource_group_name
        self.connection_type = connection_type

    @logger
    def storage_account_list_request(self, account_name: str, resource_group_name: str, subscription_id: str) -> Dict:
        """
            Send the get storage account/s request to the API.
        Args:
            account_name: The storage account name, optional.
            resource_group_name: The resource group name.
            subscription_id: The subscription id.

        Returns:
            The json response from the API call.
        """
        return self.ms_client.http_request(
            method="GET",
            full_url=(
                f"{PREFIX_URL}{subscription_id}/resourceGroups/{resource_group_name}"
                f"/providers/Microsoft.Storage/storageAccounts/{account_name}"
            ),
            params={
                "api-version": API_VERSION,
            },
        )

    @logger
    def storage_blob_service_properties_get_request(
        self, account_name: str, resource_group_name: str, subscription_id: str
    ) -> Dict:
        """
            Send the get blob service properties request to the API.
        Args:
            account_name: The storage account name.
            resource_group_name: The resource group name.
            subscription_id: The subscription id.

        Returns:
            The json response from the API call.
        """
        return self.ms_client.http_request(
            method="GET",
            full_url=(
                f"{PREFIX_URL}{subscription_id}/resourceGroups/{resource_group_name}"
                f"/providers/Microsoft.Storage/storageAccounts/{account_name}/blobServices/default"
            ),
            params={
                "api-version": API_VERSION,
            },
        )

    @logger
    def storage_account_create_update_request(self, subscription_id: str, resource_group_name: str, args: Dict) -> Dict:
        """
            Send the user arguments for the create/update account in the request body to the API.
        Args:
            subscription_id: The subscription id.
            resource_group_name: The resource group name.
            args: The user arguments.

        Returns:
            The json response from the API call.
        """
        account_name = args.get("account_name", "")
        json_data_args = {"sku": {"name": args["sku"]}, "kind": args["kind"], "location": args["location"], "properties": {}}

        if "tags" in args:
            args_tags_list = args["tags"].split(",")
            tags_obj = {f"tag{i + 1!s}": args_tags_list[i] for i in range(len(args_tags_list))}
            json_data_args["tags"] = tags_obj

        if "custom_domain_name" in args:
            custom_domain = {"name": args["custom_domain_name"]}

            if args["use_sub_domain_name"]:
                custom_domain["useSubDomainName"] = args.get("use_sub_domain_name") == "true"

            json_data_args["properties"]["customDomain"] = custom_domain

        if (
            "enc_key_source" in args
            or "enc_keyvault_key_name" in args
            or "enc_keyvault_key_version" in args
            or "enc_keyvault_uri" in args
            or "enc_requireInfrastructureEncryption" in args
        ):
            json_data_args["properties"]["Encryption"] = {}

            if "enc_key_source" in args:
                json_data_args["properties"]["Encryption"]["keySource"] = args.get("enc_key_source")

            if "enc_keyvault_key_name" in args or "enc_keyvault_key_version" in args or "enc_keyvault_uri" in args:
                json_data_args["properties"]["Encryption"]["keyvaultproperties"] = {}

                if "enc_keyvault_key_name" in args:
                    json_data_args["properties"]["Encryption"]["keyvaultproperties"]["keyname"] = args.get(
                        "enc_keyvault_key_name"
                    )

                if "enc_keyvault_key_version" in args:
                    json_data_args["properties"]["Encryption"]["keyvaultproperties"]["keyversion"] = args.get(
                        "enc_keyvault_key_version"
                    )

                if "enc_keyvault_uri" in args:
                    json_data_args["properties"]["Encryption"]["keyvaultproperties"]["keyvaulturi"] = args.get("enc_keyvault_uri")

            if "enc_requireInfrastructureEncryption" in args:
                json_data_args["properties"]["Encryption"]["requireInfrastructureEncryption"] = (
                    args.get("enc_requireInfrastructureEncryption") == "true"
                )

        if (
            "network_ruleset_bypass" in args
            or "network_ruleset_default_action" in args
            or "network_ruleset_ipRules" in args
            or "virtual_network_rules" in args
        ):
            json_data_args["properties"]["networkAcls"] = {}

            if "network_ruleset_bypass" in args:
                json_data_args["properties"]["networkAcls"]["bypass"] = args.get("network_ruleset_bypass")

            if "network_ruleset_default_action" in args:
                json_data_args["properties"]["networkAcls"]["defaultAction"] = args.get("network_ruleset_default_action")

            if "network_ruleset_ipRules" in args:
                json_data_args["properties"]["networkAcls"]["ipRules"] = json.loads(args["network_ruleset_ipRules"])

            if "virtual_network_rules" in args:
                json_data_args["properties"]["networkAcls"]["virtualNetworkRules"] = json.loads(args["virtual_network_rules"])

        if "access_tier" in args:
            json_data_args["properties"]["accessTier"] = args.get("access_tier")

        if "supports_https_traffic_only" in args:
            json_data_args["properties"]["supportsHttpsTrafficOnly"] = args.get("supports_https_traffic_only") == "true"

        if "is_hns_enabled" in args:
            json_data_args["properties"]["isHnsEnabled"] = args.get("is_hns_enabled") == "true"

        if "large_file_shares_state" in args:
            json_data_args["properties"]["largeFileSharesState"] = args.get("large_file_shares_state")

        if "allow_blob_public_access" in args:
            json_data_args["properties"]["allowBlobPublicAccess"] = args.get("allow_blob_public_access") == "true"

        if "minimum_tls_version" in args:
            json_data_args["properties"]["minimumTlsVersion"] = args.get("minimum_tls_version")

        return self.ms_client.http_request(
            method="PUT",
            full_url=(
                f"{PREFIX_URL}{subscription_id}/resourceGroups/{resource_group_name}"
                f"/providers/Microsoft.Storage/storageAccounts/{account_name}"
            ),
            params={
                "api-version": API_VERSION,
            },
            json_data=json_data_args,
            resp_type="response",
        )

    def storage_blob_service_properties_set_request(
        self, subscription_id: str | None, resource_group_name: str | None, args: Dict
    ) -> Dict:
        """
            Send the user arguments for the blob service in the request body to the API.
        Args:
            subscription_id: The subscription id.
            resource_group_name: The resource group name.
            args: The user arguments.

        Returns:
            The json response from the API call.
        """
        account_name = args.get("account_name")
        properties = {}

        if "change_feed_enabled" in args:
            properties["changeFeed"] = {"enabled": args["change_feed_enabled"] == "true"}

        if "change_feed_retention_days" in args:
            if "changeFeed" not in properties:
                properties["changeFeed"] = {}
            properties["changeFeed"]["retentionInDays"] = args.get("change_feed_retention_days")

        if "container_delete_rentention_policy_enabled" in args:
            properties["containerDeleteRetentionPolicy"] = {
                "enabled": args["container_delete_rentention_policy_enabled"] == "true"
            }

        if "container_delete_rentention_policy_days" in args:
            if "containerDeleteRetentionPolicy" not in properties:
                properties["containerDeleteRetentionPolicy"] = {}
            properties["containerDeleteRetentionPolicy"]["days"] = args.get("container_delete_rentention_policy_days")

        if "delete_rentention_policy_enabled" in args:
            properties["deleteRetentionPolicy"] = {"enabled": args["delete_rentention_policy_enabled"] == "true"}

        if "delete_rentention_policy_days" in args:
            if "deleteRetentionPolicy" not in properties:
                properties["deleteRetentionPolicy"] = {}
            properties["deleteRetentionPolicy"]["days"] = args.get("delete_rentention_policy_days")

        if "versioning" in args:
            properties["isVersioningEnabled"] = argToBoolean(args.get("versioning"))

        if (
            "last_access_time_tracking_policy_enabled" in args
            or "last_access_time_tracking_policy_blob_types" in args
            or "last_access_time_tracking_policy_days" in args
        ):
            properties["lastAccessTimeTrackingPolicy"] = {}

            if "last_access_time_tracking_policy_enabled" in args:
                properties["lastAccessTimeTrackingPolicy"]["enable"] = (
                    args.get("last_access_time_tracking_policy_enabled") == "true"
                )

            if "last_access_time_tracking_policy_blob_types" in args:
                properties["lastAccessTimeTrackingPolicy"]["blobType"] = args[
                    "last_access_time_tracking_policy_blob_types"
                ].split(",")

            if "last_access_time_tracking_policy_days" in args:
                properties["lastAccessTimeTrackingPolicy"]["trackingGranularityInDays"] = args.get(
                    "last_access_time_tracking_policy_days"
                )

        if "restore_policy_enabled" in args or "restore_policy_min_restore_time" in args or "restore_policy_days" in args:
            properties["restorePolicy"] = {}

            if "restore_policy_enabled" in args:
                properties["restorePolicy"]["enabled"] = args.get("restore_policy_enabled") == "true"

            if "restore_policy_min_restore_time" in args:
                properties["restorePolicy"]["minRestoreTime"] = args.get("restore_policy_min_restore_time")

            if "restore_policy_days" in args:
                properties["restorePolicy"]["days"] = args.get("restore_policy_days")

        return self.ms_client.http_request(
            method="PUT",
            full_url=(
                f"{PREFIX_URL}{subscription_id}/resourceGroups/{resource_group_name}"
                f"/providers/Microsoft.Storage/storageAccounts/{account_name}/blobServices/default"
            ),
            params={
                "api-version": API_VERSION,
            },
            json_data={"properties": properties},
        )

    def storage_blob_containers_create_update_request(
        self, subscription_id: str | None, resource_group_name: str | None, args: Dict, method: str
    ) -> Dict:
        """
            Send the user arguments for the create blob container in the request body to the API.
        Args:
            subscription_id: The subscription id.
            resource_group_name: The resource group name.
            args: The user arguments.
            method: The method for the http request.

        Returns:
            The json response from the API call.
        """
        container_name = args.get("container_name", "")
        account_name = args.get("account_name", "")
        properties = {}

        if "default_encryption_scope" in args:
            properties["defaultEncryptionScope"] = args.get("default_encryption_scope")

        if "deny_encryption_scope_override" in args:
            properties["denyEncryptionScopeOverride"] = argToBoolean(args.get("deny_encryption_scope_override"))

        if "public_access" in args:
            properties["publicAccess"] = args.get("public_access")

        return self.ms_client.http_request(
            method=method,
            full_url=(
                f"{PREFIX_URL}{subscription_id}/resourceGroups/{resource_group_name}"
                f"/providers/Microsoft.Storage/storageAccounts/{account_name}"
                f"/blobServices/default/containers/{container_name}"
            ),
            params={
                "api-version": API_VERSION,
            },
            json_data={"properties": properties},
        )

    def storage_blob_containers_list_request(
        self, subscription_id: str | None, resource_group_name: str | None, args: Dict
    ) -> Dict:
        """
            Send the get blob container/s request to the API.
        Args:
            subscription_id: The subscription id.
            resource_group_name: The resource group name.
            args: The user arguments.

        Returns:
            The json response from the API call.
        """
        account_name = args.get("account_name", "")
        container_name = args.get("container_name", "")
        full_url = (
            f"{PREFIX_URL}{subscription_id}/resourceGroups/{resource_group_name}"
            f"/providers/Microsoft.Storage/storageAccounts/{account_name}"
            f"/blobServices/default/containers/{container_name}?"
        )

        params = {
            "api-version": API_VERSION,
        }

        if "include_deleted" in args and args["include_deleted"] == "true":
            params["$include"] = "deleted"

        if "maxpagesize" in args:
            params["$maxpagesize"] = args["maxpagesize"]

        return self.ms_client.http_request(
            method="GET",
            full_url=full_url,
            params=params,
        )

    def storage_blob_containers_delete_request(
        self, subscription_id: str | None, resource_group_name: str | None, account_name: str | None, container_name: str | None
    ) -> requests.Response:
        return self.ms_client.http_request(
            method="DELETE",
            full_url=(
                f"{PREFIX_URL}{subscription_id}/resourceGroups/{resource_group_name}"
                f"/providers/Microsoft.Storage/storageAccounts/{account_name}"
                f"/blobServices/default/containers/{container_name}"
            ),
            params={
                "api-version": API_VERSION,
            },
            resp_type="response",
        )

    def list_subscriptions_request(self):
        return self.ms_client.http_request(
            method="GET",
            full_url="https://management.azure.com/subscriptions",
            params={
                "api-version": API_VERSION,
            },
        )

    def list_resource_groups_request(self, subscription_id: str | None, filter_by_tag: str | None, limit: int | None) -> Dict:
        full_url = f"{PREFIX_URL}{subscription_id}/resourcegroups?"
        return self.ms_client.http_request(
            "GET", full_url=full_url, params={"$filter": filter_by_tag, "$top": limit, "api-version": API_VERSION}
        )


# Storage Account Commands


def storage_account_list(client: ASClient, params: Dict, args: Dict) -> CommandResults:
    """
        Gets a storage account if an account name is specified, and a list of storage accounts if not.
    Args:
        client: The microsoft client.
        params: The configuration parameters.
        args: The users arguments, (like account name).

    Returns:
        CommandResults: The command results in MD table and context data.
    """
    # subscription_id and resource_group_name arguments can be passed as command arguments or as configuration parameters,
    # if both are passed as arguments, the command arguments will be used.
    subscription_id = get_from_args_or_params(params=params, args=args, key="subscription_id")
    resource_group_name = get_from_args_or_params(params=params, args=args, key="resource_group_name")
    account_name = args.get("account_name", "")
    response = client.storage_account_list_request(
        account_name=account_name, resource_group_name=resource_group_name, subscription_id=subscription_id
    )
    accounts = response.get("value", [response])

    readable_output = []
    for account in accounts:
        if subscription_id := re.search("subscriptions/(.+?)/resourceGroups", account.get("id", "")):
            subscription_id = subscription_id.group(1)  # type: ignore

        if resource_group := re.search("resourceGroups/(.+?)/providers", account.get("id", "")):
            resource_group = resource_group.group(1)  # type: ignore

        readable_output.append(
            {
                "Account Name": account.get("name"),
                "Subscription ID": subscription_id,
                "Resource Group": resource_group,
                "Kind": account.get("kind"),
                "Status Primary": account.get("properties").get("statusOfPrimary"),
                "Status Secondary": account.get("properties").get("statusOfSecondary"),
                "Location": account.get("location"),
            }
        )

    return CommandResults(
        outputs_prefix="AzureStorage.StorageAccount",
        outputs_key_field="id",
        outputs=accounts,
        readable_output=tableToMarkdown(
            "Azure Storage Account List",
            readable_output,
            ["Account Name", "Subscription ID", "Resource Group", "Kind", "Status Primary", "Status Secondary", "Location"],
        ),
        raw_response=response,
    )


def storage_account_create_update(client: ASClient, params: Dict, args: Dict) -> Union[CommandResults, str]:
    """
        Creates or updates a given storage account.
    Args:
        client: The microsoft client.
        params: The configuration parameters.
        args: The users arguments, (like account name).

    Returns:
        CommandResults: The command results in MD table and context data.
    """
    # subscription_id and resource_group_name arguments can be passed as command arguments or as configuration parameters,
    # if both are passed as arguments, the command arguments will be used.
    subscription_id = get_from_args_or_params(params=params, args=args, key="subscription_id")
    resource_group_name = get_from_args_or_params(params=params, args=args, key="resource_group_name")

    response = client.storage_account_create_update_request(
        subscription_id=subscription_id, resource_group_name=resource_group_name, args=args
    )

    if not response.text:
        return f"The request was accepted - the account {args.get('account_name')} will be created shortly"

    response = response.json()
    if subscription_id := re.search("subscriptions/(.+?)/resourceGroups", response.get("id", "")):
        subscription_id = subscription_id.group(1)  # type: ignore

    if resource_group := re.search("resourceGroups/(.+?)/providers", response.get("id", "")):
        resource_group = resource_group.group(1)  # type: ignore

    readable_output = {
        "Account Name": response.get("name"),
        "Subscription ID": subscription_id,
        "Resource Group": resource_group,
        "Kind": response.get("kind"),
        "Status Primary": response.get("properties", "").get("statusOfPrimary"),
        "Status Secondary": response.get("properties", "").get("statusOfSecondary"),
        "Location": response.get("location"),
    }

    return CommandResults(
        outputs_prefix="AzureStorage.StorageAccount",
        outputs_key_field="id",
        outputs=response,
        readable_output=tableToMarkdown(
            "Azure Storage Account",
            readable_output,
            ["Account Name", "Subscription ID", "Resource Group", "Kind", "Status Primary", "Status Secondary", "Location"],
        ),
        raw_response=response,
    )


# Blob Service Commands


def storage_blob_service_properties_get(client: ASClient, params: Dict, args: Dict) -> CommandResults:
    """
        Gets the blob service properties for the storage account.
    Args:
        client: The microsoft client.
        params: The configuration parameters.
        args: The users arguments, (like account name).

    Returns:
        CommandResults: The command results in MD table and context data.
    """
    # subscription_id and resource_group_name arguments can be passed as command arguments or as configuration parameters,
    # if both are passed as arguments, the command arguments will be used.
    subscription_id = get_from_args_or_params(params=params, args=args, key="subscription_id")
    resource_group_name = get_from_args_or_params(params=params, args=args, key="resource_group_name")
    account_name = args.get("account_name")
    response = client.storage_blob_service_properties_get_request(
        account_name=account_name, resource_group_name=resource_group_name, subscription_id=subscription_id
    )

    if subscription_id := re.search("subscriptions/(.+?)/resourceGroups", response.get("id", "")):
        subscription_id = subscription_id.group(1)  # type: ignore

    if resource_group := re.search("resourceGroups/(.+?)/providers", response.get("id", "")):
        resource_group = resource_group.group(1)  # type: ignore

    if account_name := re.search("storageAccounts/(.+?)/blobServices", response.get("id", "")):
        account_name = account_name.group(1)  # type: ignore

    readable_output = {
        "Name": response.get("name"),
        "Account Name": account_name,
        "Subscription ID": subscription_id,
        "Resource Group": resource_group,
        "Change Feed": response.get("properties").get("changeFeed").get("enabled")
        if response.get("properties").get("changeFeed")
        else "",
        "Delete Retention Policy": response.get("properties").get("deleteRetentionPolicy").get("enabled")
        if response.get("properties").get("deleteRetentionPolicy")
        else "",
        "Versioning": response.get("properties").get("isVersioningEnabled"),
    }

    return CommandResults(
        outputs_prefix="AzureStorage.BlobServiceProperties",
        outputs_key_field="id",
        outputs=response,
        readable_output=tableToMarkdown(
            "Azure Storage Blob Service Properties",
            readable_output,
            ["Name", "Account Name", "Subscription ID", "Resource Group", "Change Feed", "Delete Retention Policy", "Versioning"],
        ),
        raw_response=response,
    )


def storage_blob_service_properties_set(client: ASClient, params: Dict, args: Dict):
    """
        Sets the blob service properties for the storage account.
    Args:
        client: The microsoft client.
        params: The configuration parameters.
        args: The users arguments, (like account name).

    Returns:
        CommandResults: The command results in MD table and context data.
    """
    # subscription_id and resource_group_name arguments can be passed as command arguments or as configuration parameters,
    # if both are passed as arguments, the command arguments will be used.
    subscription_id = get_from_args_or_params(params=params, args=args, key="subscription_id")
    resource_group_name = get_from_args_or_params(params=params, args=args, key="resource_group_name")

    response = client.storage_blob_service_properties_set_request(
        subscription_id=subscription_id, resource_group_name=resource_group_name, args=args
    )

    if subscription_id := re.search("subscriptions/(.+?)/resourceGroups", response.get("id", "")):
        subscription_id = subscription_id.group(1)  # type: ignore

    if resource_group := re.search("resourceGroups/(.+?)/providers", response.get("id", "")):
        resource_group = resource_group.group(1)  # type: ignore

    if account_name := re.search("storageAccounts/(.+?)/blobServices", response.get("id", "")):
        account_name = account_name.group(1)  # type: ignore

    readable_output = {
        "Name": response.get("name"),
        "Account Name": account_name,
        "Subscription ID": subscription_id,
        "Resource Group": resource_group,
        "Change Feed": str(response.get("properties", "").get("changeFeed").get("enabled"))
        if response.get("properties", "").get("changeFeed")
        else "",
        "Delete Retention Policy": str(response.get("properties", "").get("deleteRetentionPolicy").get("enabled"))
        if response.get("properties", "").get("deleteRetentionPolicy")
        else "",
        "Versioning": response.get("properties", "").get("isVersioningEnabled"),
    }

    return CommandResults(
        outputs_prefix="AzureStorage.BlobServiceProperties",
        outputs_key_field="id",
        outputs=response,
        readable_output=tableToMarkdown(
            "Azure Storage Blob Service Properties",
            readable_output,
            ["Name", "Account Name", "Subscription ID", "Resource Group", "Change Feed", "Delete Retention Policy", "Versioning"],
        ),
        raw_response=response,
    )


# Blob Containers Commands


def storage_blob_containers_create(client: ASClient, params: Dict, args: Dict):
    """
        Creates a blob container.
    Args:
        client: The microsoft client.
        params: The configuration parameters.
        args: The users arguments, (like account name, container name).

    Returns:
        CommandResults: The command results in MD table and context data.
    """
    # subscription_id and resource_group_name arguments can be passed as command arguments or as configuration parameters,
    # if both are passed as arguments, the command arguments will be used.
    subscription_id = get_from_args_or_params(params=params, args=args, key="subscription_id")
    resource_group_name = get_from_args_or_params(params=params, args=args, key="resource_group_name")

    response = client.storage_blob_containers_create_update_request(
        subscription_id=subscription_id, resource_group_name=resource_group_name, args=args, method="PUT"
    )

    if subscription_id := re.search("subscriptions/(.+?)/resourceGroups", response.get("id", "")):
        subscription_id = subscription_id.group(1)  # type: ignore

    if resource_group := re.search("resourceGroups/(.+?)/providers", response.get("id", "")):
        resource_group = resource_group.group(1)  # type: ignore

    if account_name := re.search("storageAccounts/(.+?)/blobServices", response.get("id", "")):
        account_name = account_name.group(1)  # type: ignore

    readable_output = {
        "Name": response.get("name"),
        "Account Name": account_name,
        "Subscription ID": subscription_id,
        "Resource Group": resource_group,
    }

    return CommandResults(
        outputs_prefix="AzureStorage.BlobContainer",
        outputs_key_field="id",
        outputs=response,
        readable_output=tableToMarkdown(
            "Azure Storage Blob Containers Properties",
            readable_output,
            ["Name", "Account Name", "Subscription ID", "Resource Group"],
        ),
        raw_response=response,
    )


def storage_blob_containers_update(client: ASClient, params: Dict, args: Dict) -> CommandResults:
    """
        Updates a given blob container.
    Args:
        client: The microsoft client.
        params: The configuration parameters.
        args: The users arguments, (like account name, container name).

    Returns:
        CommandResults: The command results in MD table and context data.
    """
    # subscription_id and resource_group_name arguments can be passed as command arguments or as configuration parameters,
    # if both are passed as arguments, the command arguments will be used.
    subscription_id = get_from_args_or_params(params=params, args=args, key="subscription_id")
    resource_group_name = get_from_args_or_params(params=params, args=args, key="resource_group_name")

    response = client.storage_blob_containers_create_update_request(
        subscription_id=subscription_id, resource_group_name=resource_group_name, args=args, method="PATCH"
    )

    if subscription_id := re.search("subscriptions/(.+?)/resourceGroups", response.get("id", "")):
        subscription_id = subscription_id.group(1)  # type: ignore

    if resource_group := re.search("resourceGroups/(.+?)/providers", response.get("id", "")):
        resource_group = resource_group.group(1)  # type: ignore

    if account_name := re.search("storageAccounts/(.+?)/blobServices", response.get("id", "")):
        account_name = account_name.group(1)  # type: ignore

    readable_output = {
        "Name": response.get("name"),
        "Account Name": account_name,
        "Subscription ID": subscription_id,
        "Resource Group": resource_group,
        "Public Access": response.get("properties", {}).get("publicAccess"),
    }

    return CommandResults(
        outputs_prefix="AzureStorage.BlobContainer",
        outputs_key_field="id",
        outputs=response,
        readable_output=tableToMarkdown(
            "Azure Storage Blob Containers Properties",
            readable_output,
            ["Name", "Account Name", "Subscription ID", "Resource Group", "Public Access"],
        ),
        raw_response=response,
    )


def storage_blob_containers_list(client: ASClient, params: Dict, args: Dict) -> CommandResults:
    """
        Gets a blob container if an container name is specified, and a list of blob containers if not.
    Args:
        client: The microsoft client.
        params: The configuration parameters.
        args: The users arguments, (like account name, container name).

    Returns:
        CommandResults: The command results in MD table and context data.
    """
    # subscription_id and resource_group_name arguments can be passed as command arguments or as configuration parameters,
    # if both are passed as arguments, the command arguments will be used.
    subscription_id = get_from_args_or_params(params=params, args=args, key="subscription_id")
    resource_group_name = get_from_args_or_params(params=params, args=args, key="resource_group_name")

    response = client.storage_blob_containers_list_request(
        subscription_id=subscription_id, resource_group_name=resource_group_name, args=args
    )
    containers = response.get("value", [response])

    readable_output = []
    for container in containers:
        if subscription_id := re.search("subscriptions/(.+?)/resourceGroups", container.get("id", "")):
            subscription_id = subscription_id.group(1)  # type: ignore

        if resource_group := re.search("resourceGroups/(.+?)/providers", container.get("id", "")):
            resource_group = resource_group.group(1)  # type: ignore

        if account_name := re.search("storageAccounts/(.+?)/blobServices", container.get("id", "")):
            account_name = account_name.group(1)  # type: ignore

        readable_output.append(
            {
                "Container Name": container.get("name"),
                "Account Name": account_name,
                "Subscription ID": subscription_id,
                "Resource Group": resource_group,
                "Public Access": container.get("properties", {}).get("publicAccess"),
                "Lease State": container.get("properties", {}).get("leaseState"),
                "Last Modified Time": container.get("properties", {}).get("lastModifiedTime"),
            }
        )

    return CommandResults(
        outputs_prefix="AzureStorage.BlobContainer",
        outputs_key_field="id",
        outputs=containers,
        readable_output=tableToMarkdown(
            "Azure Storage Blob Containers list",
            readable_output,
            [
                "Container Name",
                "Account Name",
                "Subscription ID",
                "Resource Group",
                "Public Access",
                "Lease State",
                "Last Modified Time",
            ],
        ),
        raw_response=response,
    )


def storage_blob_containers_delete(client: ASClient, params: Dict, args: Dict) -> str:
    """
    This function deletes a given blob container.
    Args:
        client: The microsoft client.
        params: The configuration parameters.
        args: The users arguments.
    Returns:
        str: A string that represent the status of the request.
    """

    # subscription_id and resource_group_name arguments can be passed as command arguments or as configuration parameters,
    # if both are passed as arguments, the command arguments will be used.
    subscription_id = get_from_args_or_params(params=params, args=args, key="subscription_id")
    resource_group_name = get_from_args_or_params(params=params, args=args, key="resource_group_name")
    account_name = args.get("account_name", "")
    container_name = args.get("container_name", "")

    res = client.storage_blob_containers_delete_request(
        subscription_id=subscription_id,
        resource_group_name=resource_group_name,
        account_name=account_name,
        container_name=container_name,
    )
    if res.status_code == 200:
        return "The request to delete the blob container was sent successfully."
    else:
        return f"Failed to delete the blob container.\
Status code: {res.status_code} \nPlease verify that the container and account name are correct."


def storage_subscriptions_list(client: ASClient) -> CommandResults:
    """
        Gets a list of subscriptions.
    Args:
        client: The microsoft client.
    Returns:
        CommandResults: The command results in MD table and context data.
    """
    res = client.list_subscriptions_request()
    subscriptions = res.get("value", [])

    return CommandResults(
        outputs_prefix="AzureStorage.Subscription",
        outputs_key_field="id",
        outputs=subscriptions,
        readable_output=tableToMarkdown(
            "Azure Storage Subscriptions list",
            subscriptions,
            ["subscriptionId", "tenantId", "displayName", "state"],
        ),
        raw_response=res,
    )


def storage_resource_group_list(client: ASClient, params: Dict, args: Dict) -> CommandResults:
    """
    List all resource groups in the subscription.
    Args:
        client (KeyVaultClient): microsoft client.
        args (Dict[str, Any]): command arguments.
        params (Dict[str, Any]): configuration parameters.
    Returns:
        CommandResults: Command results with raw response, outputs and readable outputs.
    """
    tag = args.get("tag")
    limit = arg_to_number(args.get("limit")) or 50
    # subscription_id can be passed as command argument or as configuration parameter,
    # if both are passed as arguments, the command argument will be used.
    subscription_id = get_from_args_or_params(params=params, args=args, key="subscription_id")
    filter_by_tag = azure_tag_formatter(tag) if tag else ""

    response = client.list_resource_groups_request(subscription_id=subscription_id, filter_by_tag=filter_by_tag, limit=limit)
    data_from_response = response.get("value", [])

    readable_output = tableToMarkdown(
        "Resource Groups List",
        data_from_response,
        ["name", "location", "tags", "properties.provisioningState"],
        removeNull=True,
        headerTransform=string_to_table_header,
    )
    return CommandResults(
        outputs_prefix="AzureStorage.ResourceGroup",
        outputs_key_field="id",
        outputs=data_from_response,
        raw_response=response,
        readable_output=readable_output,
    )

    # Authentication Functions


def start_auth(client: ASClient) -> CommandResults:
    result = client.ms_client.start_auth("!azure-storage-auth-complete")
    return CommandResults(readable_output=result)


def complete_auth(client: ASClient) -> str:
    client.ms_client.get_access_token()
    return "✅ Authorization completed successfully."


def test_connection(client: ASClient) -> str:
    client.ms_client.get_access_token()
    return "✅ Success!"


def test_module(client: ASClient) -> str:
    """Tests API connectivity and authentication'
    Returning 'ok' indicates that the integration works like it is supposed to.
    Connection to the service is successful.
    Raises exceptions if something goes wrong.
    :type ASClient: ``Client``
    :param Client: client to use
    :return: 'ok' if test passed.
    :rtype: ``str``
    """
    # This  should validate all the inputs given in the integration configuration panel,
    # either manually or by using an API that uses them.
    if "Device" in client.connection_type:
        raise DemistoException(
            "Please enable the integration and run `!azure-storage-auth-start`"
            "and `!azure-storage-auth-complete` to log in."
            "You can validate the connection by running `!azure-storage-auth-test`\n"
            "For more details press the (?) button."
        )

    elif client.connection_type == "Azure Managed Identities" or client.connection_type == "Client Credentials":
        client.ms_client.get_access_token()
        return "ok"
    else:
        raise Exception(
            "When using user auth flow configuration, "
            "Please enable the integration and run the !azure-storage-auth-test command in order to test it"
        )


def main() -> None:  # pragma: no cover
    params = demisto.params()
    command = demisto.command()
    args = demisto.args()

    demisto.debug(f"Command being called is {command}")
    try:
        client = ASClient(
            app_id=params.get("app_id", ""),
            subscription_id=params.get("subscription_id", ""),
            resource_group_name=params.get("resource_group_name", ""),
            verify=not params.get("insecure", False),
            proxy=params.get("proxy", False),
            connection_type=params.get("auth_type", "Device Code"),
            tenant_id=params.get("tenant_id"),
            enc_key=params.get("credentials", {}).get("password"),
            auth_code=(params.get("auth_code", {})).get("password"),
            redirect_uri=params.get("redirect_uri"),
            managed_identities_client_id=get_azure_managed_identities_client_id(params),
        )
        if command == "test-module":
            return_results(test_module(client))
        elif command == "azure-storage-generate-login-url":
            return_results(generate_login_url(client.ms_client))
        elif command == "azure-storage-auth-start":
            return_results(start_auth(client))
        elif command == "azure-storage-auth-complete":
            return_results(complete_auth(client))
        elif command == "azure-storage-auth-test":
            return_results(test_connection(client))
        elif command == "azure-storage-auth-reset":
            return_results(reset_auth())
        elif command == "azure-storage-account-list":
            return_results(storage_account_list(client, params, args))
        elif command == "azure-storage-account-create-update":
            return_results(storage_account_create_update(client, params, args))
        elif command == "azure-storage-blob-service-properties-get":
            return_results(storage_blob_service_properties_get(client, params, args))
        elif command == "azure-storage-blob-service-properties-set":
            return_results(storage_blob_service_properties_set(client, params, args))
        elif command == "azure-storage-blob-containers-create":
            return_results(storage_blob_containers_create(client, params, args))
        elif command == "azure-storage-blob-containers-update":
            return_results(storage_blob_containers_update(client, params, args))
        elif command == "azure-storage-blob-containers-list":
            return_results(storage_blob_containers_list(client, params, args))
        elif command == "azure-storage-blob-container-delete":
            return_results(storage_blob_containers_delete(client, params, args))
        elif command == "azure-storage-subscriptions-list":
            return_results(storage_subscriptions_list(client))
        elif command == "azure-storage-resource-group-list":
            return_results(storage_resource_group_list(client, params, args))
        else:
            raise NotImplementedError(f'Command "{command}" is not implemented.')
    except Exception as e:
        demisto.debug(traceback.format_exc())
        return_error(f"Failed to execute {demisto.command()} command.\nError:\n{e!s}", e)


if __name__ in ("__main__", "__builtin__", "builtins"):
    main()

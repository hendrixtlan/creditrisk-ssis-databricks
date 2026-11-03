terraform {
  required_version = ">= 1.6.0"
  required_providers {
    azurerm = { source = "hashicorp/azurerm", version = "~> 4.0" }
  }
}

provider "azurerm" {
  features {}
  subscription_id = var.subscription_id
}

variable "subscription_id" { type = string }
variable "location" {
  type = string
  default = "eastus2"
}
variable "suffix" {
  type = string
  description = "Globally unique lowercase alphanumeric 4-12 character suffix"
  validation {
    condition = can(regex("^[a-z0-9]{4,12}$", var.suffix))
    error_message = "suffix must contain 4-12 lowercase alphanumeric characters"
  }
}
resource "azurerm_resource_group" "demo" {
  name = "rg-creditrisk-${var.suffix}"
  location = var.location
}
resource "azurerm_storage_account" "lake" {
  name = "cr${var.suffix}lake"
  resource_group_name = azurerm_resource_group.demo.name
  location = azurerm_resource_group.demo.location
  account_tier = "Standard"
  account_replication_type = "LRS"
  account_kind = "StorageV2"
  is_hns_enabled = true
  min_tls_version = "TLS1_2"
}
resource "azurerm_storage_data_lake_gen2_filesystem" "landing" {
  name = "landing"
  storage_account_id = azurerm_storage_account.lake.id
}
resource "azurerm_data_factory" "adf" {
  name = "adf-creditrisk-${var.suffix}"
  location = azurerm_resource_group.demo.location
  resource_group_name = azurerm_resource_group.demo.name
  identity { type = "SystemAssigned" }
}
resource "azurerm_databricks_workspace" "workspace" {
  name = "dbw-creditrisk-${var.suffix}"
  location = azurerm_resource_group.demo.location
  resource_group_name = azurerm_resource_group.demo.name
  sku = "premium"
}
resource "azurerm_databricks_access_connector" "uc" {
  name = "dac-creditrisk-${var.suffix}"
  location = azurerm_resource_group.demo.location
  resource_group_name = azurerm_resource_group.demo.name
  identity { type = "SystemAssigned" }
}
resource "azurerm_role_assignment" "uc_landing_reader" {
  scope = azurerm_storage_account.lake.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id = azurerm_databricks_access_connector.uc.identity[0].principal_id
}
resource "azurerm_role_assignment" "adf_landing_writer" {
  scope = azurerm_storage_account.lake.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id = azurerm_data_factory.adf.identity[0].principal_id
}
output "storage_account" { value = azurerm_storage_account.lake.name }
output "databricks_workspace_url" { value = azurerm_databricks_workspace.workspace.workspace_url }
output "adf_name" { value = azurerm_data_factory.adf.name }
output "access_connector_id" { value = azurerm_databricks_access_connector.uc.id }

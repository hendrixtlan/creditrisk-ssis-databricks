# Optional Azure Terraform starter

Apply only in a nonproduction/demo subscription. `az login`, provide subscription ID and a globally unique suffix, then:

```shell
terraform init
terraform validate
terraform plan -var="subscription_id=<your-subscription-id>" -var="suffix=my2026x"
terraform apply -var="subscription_id=<your-subscription-id>" -var="suffix=my2026x"
```

This provisions the Azure resource group, ADLS Gen2 storage and `landing` filesystem, Data Factory, Premium Databricks workspace, UC access connector and broad demo storage RBAC assignments. It does **not** configure SQL Server/on-prem SHIR, Key Vault, private endpoints, ADF linked services, Unity Catalog external location/storage credential/metastore, Databricks grants or workloads. Adjust identity/storage roles to least privilege and storage/network hardening before using with confidential data. Azure resources incur usage costs. Destroy the demo with `terraform destroy` when finished.

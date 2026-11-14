# Azure Databricks setup for Track 4

The bundle's `azure_dev` target deploys the same resources as `dev`. These steps
are one-time and need a person with workspace admin rights.

## Verified environment (2026-11-13)

Read with `az` 2.92.0 and the Databricks CLI 1.17.0; nothing was created.

| Field | Value |
|---|---|
| Subscription | Azure subscription - pay-as-you-go (`90ab58b4-…-b5490d6de15e`), Enabled, MCA individual |
| Resource group | `rg-adp-dev` (canadacentral) |
| Workspace | `adb-adp-dev`, workspace id `7405615454810108` |
| URL | `https://adb-7405615454810108.8.azuredatabricks.net` |
| SKU / compute mode | `trial` (14-day Premium trial, created 2026-11-14 00:32 UTC) / Hybrid, no public IP |
| Managed resource group | `rg-adp-dev-bedoux-agentic`: VNet, NSG, NAT gateway + public IP, ZRS storage, UC access connector |
| Metastore | `metastore_azure_canadacentral`, no metastore root storage |
| Catalog | `adb_adp_dev` (workspace catalog, owner `_workspace_admins_…`), schemas `default` only |
| CLI profile | `ADP_AZURE` (OAuth U2M), user `tsoglog.uli@gmail.com`, groups `admins`, `users` |
| Compute present | Serverless Starter Warehouse (stopped); no clusters, jobs or pipelines |

The trial SKU from the earlier failed attempt now provisions under Pay-As-You-Go.
The NAT gateway and its public IP bill hourly whether or not anything runs;
serverless jobs do not use them. They go away only with the workspace.

## 1. Workspace and catalog

1. `targets.azure_dev.workspace.host` in `databricks.yml` holds the workspace
   URL (done, see above).
2. `targets.azure_dev.variables.catalog` is `adb_adp_dev`. A dedicated catalog
   would need a managed storage location first, because the metastore has no
   root storage. Track 4 creates `adp_meta`, `adp_bronze` and `adp_gold`.
3. Serverless compute for notebooks and jobs must be enabled; the jobs declare no
   clusters. Deploying the bundle also deploys Tracks 1–3 (manual-trigger jobs
   and pipelines only; nothing runs on deploy).

## 2. Local deploy (interactive)

```bash
databricks auth login --host <workspace-url> --profile ADP_AZURE
databricks bundle validate --target azure_dev --profile ADP_AZURE
databricks bundle deploy   --target azure_dev --profile ADP_AZURE
databricks bundle run adp_platform_job --target azure_dev --profile ADP_AZURE --params day=1
```

Run days in order (1, 2, 3). Re-running a day is a no-op. Inject a defect with
`--params day=2,defect=bad_unit_price,defect_day=2`. To start over, drop the
`adp_meta`, `adp_bronze` and `adp_gold` schemas (destructive; your call).

## 3. CI deploy with GitHub OIDC (no stored token)

1. Create a Databricks service principal in the workspace and grant it
   `CAN MANAGE` on the bundle's workspace folder and `USE CATALOG`,
   `CREATE SCHEMA` on the catalog.
2. Add a federation policy to the service principal for GitHub Actions:
   issuer `https://token.actions.githubusercontent.com`, audience as the
   Databricks docs specify for your account, subject
   `repo:tsogtbatjargal/bedoux-databricks:environment:azure-dev`.
3. In GitHub, create environment `azure-dev` (optionally with a required
   reviewer) and set variables `AZURE_DATABRICKS_HOST` and
   `AZURE_DATABRICKS_CLIENT_ID` (the service principal's application id).
4. Run the "Deploy to Azure Databricks" workflow manually. Unchecked `deploy`
   validates only.

Check the current Azure Databricks documentation for "workload identity
federation" before step 2: field names and audience values are defined there,
and this repo has not yet been run against them.

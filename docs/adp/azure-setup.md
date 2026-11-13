# Azure Databricks setup for Track 4

The bundle's `azure_dev` target deploys the same resources as `dev`. These steps
are one-time and need a person with workspace admin rights.

## 1. Workspace and catalog

1. Set `targets.azure_dev.workspace.host` in `databricks.yml` to the workspace
   URL (`https://adb-<workspace-id>.<n>.azuredatabricks.net`).
2. Set `targets.azure_dev.variables.catalog` to a Unity Catalog catalog the
   deploying identity can create schemas in. Track 4 creates `adp_meta`,
   `adp_bronze` and `adp_gold`.
3. Serverless compute for notebooks and jobs must be enabled; the jobs declare no
   clusters. Deploying the bundle also deploys Tracks 1–3 (manual-trigger jobs
   and pipelines only; nothing runs on deploy).

## 2. Local deploy (interactive)

```bash
databricks auth login --host <workspace-url> --profile azure-dev
databricks bundle validate --target azure_dev --profile azure-dev
databricks bundle deploy   --target azure_dev --profile azure-dev
databricks bundle run adp_platform_job --target azure_dev --profile azure-dev --params day=1
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

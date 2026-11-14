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

## 3. CI deploy with GitHub OIDC (no stored secret)

Set up 2026-11-13. Databricks-native federation policies need a Databricks
account admin, which the workspace owner is not, so CI uses Azure-native
workload identity federation instead:

| Piece | Value |
|---|---|
| Entra identity | user-assigned managed identity `id-adp-github-deploy` in `rg-adp-dev`, client id `f7545e16-39c2-4302-8235-acc66c69f617`, no Azure RBAC roles |
| Federated credential | `github-azure-dev`: issuer `https://token.actions.githubusercontent.com`, audience `api://AzureADTokenExchange`, subject `repo:tsogtbatjargal@122837521/bedoux-databricks@1317616316:environment:azure-dev` |
| Workspace principal | service principal `id-adp-github-deploy` (same application id), entitlement `workspace-access` only, no Unity Catalog grants |
| GitHub environment | `azure-dev`, deployable from `main` only; variables `AZURE_DATABRICKS_HOST`, `AZURE_CLIENT_ID`, `AZURE_TENANT_ID` |

The subject uses GitHub's immutable form (owner and repo with numeric ids)
because this repository has `use_immutable_subject: true`
(`gh api repos/tsogtbatjargal/bedoux-databricks/actions/oidc/customization/sub`).
The `owner/repo` form would never match.

`.github/workflows/deploy-azure.yml` signs in with `azure/login` (OIDC), then
the Databricks CLI uses `DATABRICKS_AUTH_TYPE: azure-cli`. Run it manually from
`main`; unchecked `deploy` validates only.

Evidence: run 43550439595 signed in but failed validation with 403 (the service
principal had no `workspace-access` entitlement; added). Run 43550611869:
`bundle validate --target azure_dev` → `Validation OK!` as the service principal.

CI deploys target `azure_ci` (`mode: production`, root path in the service
principal's home, `run_as` the service principal). People and CI deploy the
same copy, and jobs always run as one identity. The service principal owns the
Track 4 schemas and tables (`adp_meta`, `adp_bronze`, `adp_gold`) and has
`USE CATALOG`, `CREATE SCHEMA` on `adb_adp_dev`; the workspace owner keeps
`USE SCHEMA`, `SELECT`, `MODIFY` on those schemas. The personal `azure_dev`
deployment was destroyed when `azure_ci` took over (tables are not bundle
resources and were kept). Track 1–3 resources deploy under `azure_ci` but have
no grants for the service principal, so they would fail if run.

To remove: `az identity delete -g rg-adp-dev -n id-adp-github-deploy`, then
`databricks service-principals delete <id> --profile ADP_AZURE` and the GitHub
environment.

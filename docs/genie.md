# Genie CLI

Genie is Databricks' natural-language query agent over Unity Catalog tables. This project
uses the real `databricks genie` subcommands from CLI v1.10.0 (verified against
`databricks genie --help`; some names differ from older docs/examples floating around —
e.g. there is no `create-conversation`, it's `start-conversation`).

## Setup

```bash
databricks auth login --host https://dbc-3f70aae3-11d5.cloud.databricks.com --profile bedoux-databricks
```

## Current spaces in this workspace

```bash
databricks genie list-spaces --profile bedoux-databricks -o json
```

Right now there is one: **Bakehouse Sales Starter Space** (`space_id`
`01f18b9bdf111b9e89e4c53068229731`) — the sample space Databricks ships by default, over
fictional bakery data. There is no Genie space yet over this project's `workspace.gold`
tables (`gold_monthly_revenue_by_region`, `gold_customer_lifetime_value`,
`gold_top_products`) — see "Creating a Genie space for this project" below.

## Commands

| Command | What it does |
|---|---|
| `databricks genie ask "<question>"` | One-off question; auto-resolves a SQL warehouse. Add `-s <session>` to keep asking follow-ups in the same session without managing a conversation id yourself. |
| `databricks genie list-spaces` | List all Genie spaces you have access to. |
| `databricks genie get-space <space-id>` | Space details (title, description, warehouse). |
| `databricks genie start-conversation <space-id> <question>` | Start a new conversation in a specific space; returns a conversation id. |
| `databricks genie create-message <space-id> <conversation-id> "<question>"` | Continue an existing conversation. |
| `databricks genie list-conversations <space-id>` | List conversations in a space. |
| `databricks genie list-conversation-messages <space-id> <conversation-id>` | List messages/answers in a conversation. |

All support `-o json` for machine-readable output.

### Via the project wrapper

```bash
./scripts/genie.sh spaces
./scripts/genie.sh ask "What was the monthly revenue trend by region?"
./scripts/genie.sh start <space-id> "Show me top products by revenue"
./scripts/genie.sh reply <space-id> <conversation-id> "Now break that down by month"
```

## Creating a Genie space for this project (not yet done)

`databricks genie create-space WAREHOUSE_ID SERIALIZED_SPACE` exists, but
`SERIALIZED_SPACE` is an opaque JSON blob describing the space's tables/layout — the CLI
help itself says the intended way to get one is to `get-space --include-serialized-space`
on an *existing* space and adapt it, not to hand-author it from scratch. In practice the
UI is the practical path for a brand-new space. To point a space at this project's Gold
layer:

1. Databricks UI → **Genie** → **New space**.
2. Add tables: `workspace.gold.gold_monthly_revenue_by_region`,
   `workspace.gold.gold_customer_lifetime_value`, `workspace.gold.gold_top_products`.
3. Attach a Pro/Serverless SQL warehouse you have **CAN USE** on.
4. Note the resulting `space_id` and use it with the commands above.

Once it exists, you can clone/template it via the CLI:

```bash
databricks genie get-space <space-id> --include-serialized-space -o json > /tmp/space.json
# extract .serialized_space, edit as needed, then:
databricks genie create-space <warehouse-id> "$(jq -r .serialized_space /tmp/space.json)" \
  --title "New Space" --profile bedoux-databricks
```

This step touches the live workspace, so it's left for you to trigger explicitly rather
than done as part of scaffolding this repo.

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

Three spaces exist:

- **Bakehouse Sales Starter Space** (`space_id` `01f18b9bdf111b9e89e4c53068229731`) —
  the sample space Databricks ships by default, over fictional bakery data.
- **TPC-H Medallion Analytics** (`space_id` `01f18c57fa251338962ee7a34efab97e`) —
  Track 1's space, over `workspace.gold.*`.
- **Bedoux Ops & Marketing Analytics** (`space_id` `01f18c5765861b98a829e34fcec67160`) —
  Track 2's space, over `workspace.bedoux_gold.*`.

Both project spaces were created the same way — see "Creating a Genie space via the
CLI" below for the worked pattern and the exact `serialized_space` JSON used for each.

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

## Creating a Genie space via the CLI

`databricks genie create-space WAREHOUSE_ID SERIALIZED_SPACE` works with a
hand-authored `serialized_space` JSON — the CLI help's suggestion to clone
`get-space --include-serialized-space` from an existing space first isn't actually
necessary; the schema (`config.sample_questions`, `data_sources.tables`,
`instructions.text_instructions`) is simple enough to write directly. One gotcha:
**`data_sources.tables` must be sorted alphabetically by `identifier`**, or the API
rejects the payload with `Invalid export proto: data_sources.tables must be sorted by
identifier`. Each `sample_questions`/`text_instructions` entry also needs a unique
`id` string (any value works, e.g. `uuid4().hex`).

```bash
databricks genie create-space <warehouse-id> "$(cat serialized_space.json)" \
  --title "<title>" --description "<description>" --profile bedoux-databricks
```

### Track 1 — TPC-H Medallion Analytics (done)

`space_id` **`01f18c57fa251338962ee7a34efab97e`**, warehouse `e63747243511532c`.

```json
{
  "version": 2,
  "config": {
    "sample_questions": [
      {"question": ["What was the monthly revenue trend by region?"]},
      {"question": ["Who are the top 10 customers by lifetime value?"]},
      {"question": ["Which products generate the most revenue?"]},
      {"question": ["What is the total revenue across all regions this year?"]},
      {"question": ["Which customer value segment has the most customers?"]}
    ]
  },
  "data_sources": {
    "tables": [
      {"identifier": "workspace.gold.gold_customer_lifetime_value"},
      {"identifier": "workspace.gold.gold_monthly_revenue_by_region"},
      {"identifier": "workspace.gold.gold_top_products"}
    ]
  },
  "instructions": {
    "text_instructions": [
      {"content": [
        "This is the TPC-H benchmark dataset (samples.tpch), used as a classic data-engineering exercise -- not Bedoux business data.",
        "Revenue is defined consistently as sum(l_extendedprice * (1 - l_discount)).",
        "gold_customer_lifetime_value.value_segment buckets customers into Low/Medium/High by revenue percentile.",
        "gold_top_products.revenue_rank ranks products by total_revenue descending (rank 1 = highest revenue)."
      ]}
    ]
  }
}
```

Verified end-to-end: `databricks genie start-conversation 01f18c57fa251338962ee7a34efab97e
"Who are the top 5 customers by lifetime value?"` correctly ranked by `total_revenue`
descending and returned the top 5, with a chart attachment.

### Track 2 — Bedoux Ops & Marketing Analytics (done)

`space_id` **`01f18c5765861b98a829e34fcec67160`**, warehouse `e63747243511532c`.

```json
{
  "version": 2,
  "config": {
    "sample_questions": [
      {"question": ["Which campaign has the best cost per lead?"]},
      {"question": ["What is the conversion rate by channel?"]},
      {"question": ["Show me the client funnel for the last three months."]},
      {"question": ["What's ogi's daily-plan success rate this month?"]},
      {"question": ["Which day had the most Telegram messages handled?"]}
    ]
  },
  "data_sources": {
    "tables": [
      {"identifier": "workspace.bedoux_gold.gold_campaign_performance"},
      {"identifier": "workspace.bedoux_gold.gold_client_funnel"},
      {"identifier": "workspace.bedoux_gold.gold_ogi_ops_health"}
    ]
  },
  "instructions": {
    "text_instructions": [
      {"content": [
        "This data is entirely synthetic and fictional, generated by a seeded data generator for a portfolio project. It does not represent Bedoux's real business data.",
        "cost_per_lead is NULL (not 0) when a campaign generated no leads -- treat NULL as \"no data\", not \"free acquisition\".",
        "conversion_rate is the share of leads that reached the won stage.",
        "gold_ogi_ops_health tracks the ogi agent's own daily-plan runs and Telegram messages handled, one row per day."
      ]}
    ]
  }
}
```

Verified end-to-end: `databricks genie start-conversation 01f18c5765861b98a829e34fcec67160
"Which campaign has the best cost per lead?"` correctly generated SQL that filters out
NULL `cost_per_lead` rows before ranking, and returned "campaign ID 29, cost per lead
14.335."

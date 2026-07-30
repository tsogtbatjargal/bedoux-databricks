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

Two spaces exist:

- **Bakehouse Sales Starter Space** (`space_id` `01f18b9bdf111b9e89e4c53068229731`) —
  the sample space Databricks ships by default, over fictional bakery data.
- **Bedoux Ops & Marketing Analytics** (`space_id` `01f18c5765861b98a829e34fcec67160`) —
  this project's Track 2 space, over `workspace.bedoux_gold.*`. See below for how it
  was created and verified.

There is no Genie space yet over Track 1's `workspace.gold` tables
(`gold_monthly_revenue_by_region`, `gold_customer_lifetime_value`, `gold_top_products`)
— see "Creating a Genie space for this project" below.

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

## Creating a Genie space for Track 1 (not yet done)

`databricks genie create-space WAREHOUSE_ID SERIALIZED_SPACE` works with a
hand-authored `serialized_space` JSON — see the worked example below (Track 2's space
was built exactly this way; the CLI help's suggestion to clone `get-space
--include-serialized-space` from an existing space isn't actually necessary). To point
a space at Track 1's Gold layer, reuse the same `serialized_space` JSON shape, with:

```json
"data_sources": {
  "tables": [
    {"identifier": "workspace.gold.gold_monthly_revenue_by_region"},
    {"identifier": "workspace.gold.gold_customer_lifetime_value"},
    {"identifier": "workspace.gold.gold_top_products"}
  ]
}
```

attached to the same 2X-Small warehouse (`e63747243511532c` — Free Edition allows only
one, shared across both spaces).

This step touches the live workspace, so it's left for you to trigger explicitly rather
than done as part of scaffolding this repo.

## The Bedoux Genie space (Track 2, done)

`space_id` **`01f18c5765861b98a829e34fcec67160`**, title "Bedoux Ops & Marketing
Analytics", attached to the one available 2X-Small warehouse (`e63747243511532c`).

Turns out `create-space` *can* be hand-authored from scratch after all — the
`serialized_space` JSON schema is simple enough (`config.sample_questions`,
`data_sources.tables`, `instructions.text_instructions`) to write directly, without
needing to clone an existing space first. Built with:

```bash
databricks genie create-space e63747243511532c "$(cat serialized_space.json)" \
  --title "Bedoux Ops & Marketing Analytics" \
  --description "Portfolio demo Genie space over synthetic/fictional Bedoux marketing + ops data. Not real business data." \
  --profile bedoux-databricks
```

where `serialized_space.json` was:

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

(each `sample_questions`/`text_instructions` entry also needs a unique `id` string —
any value works, e.g. a `uuid4().hex`.)

Verified end-to-end: `databricks genie start-conversation 01f18c5765861b98a829e34fcec67160
"Which campaign has the best cost per lead?"` correctly generated SQL that filters out
NULL `cost_per_lead` rows before ranking, and returned "campaign ID 29, cost per lead
14.335."

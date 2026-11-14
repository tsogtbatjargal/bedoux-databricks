# Track 4 evaluation results

Recorded by `scripts/adp_eval.py`. Regenerate rather than edit by hand.

- Command: `AZURE_OPENAI_ENDPOINT=… AZURE_OPENAI_DEPLOYMENT=adp-eval-gpt-5-4-mini AZURE_OPENAI_API_KEY=… uv run --group agents python scripts/adp_eval.py --provider azure-openai --max-usd 5 --json`
- Recorded: 2026-11-14 04:44 UTC
- Deployment: `adp-eval-gpt-5-4-mini` (gpt-5.4-mini 2026-03-17, Data Zone Standard) on Azure AI Services `tsogloguli-6913-resource`, billed to the Azure subscription
- Run: 2 of 2 (after the citation-guard change); run 1 is compared below
- Environment: Python 3.11.16, local fixtures, no Databricks workspace
- Provider: `azure-openai` (model `gpt-5.4-mini`, reasoning effort medium, hard spend cap; one-shot run, no retries of cases)

## Summary

| Metric | Result |
|---|---|
| incident_cases | 30 |
| incidents_opened | 30 |
| rule_root_cause_accuracy | 1.0 |
| agent_root_cause_accuracy | 0.833 |
| agent_reported | 25 |
| routed_to_runbook | 25 |
| required_evidence_present | 25 |
| final_reports_with_citations | 25 |
| forbidden_tool_executions | 0 |
| seeded_defect_rows | 144 |
| seeded_defect_rows_detected | 144 |
| detection_recall | 1.0 |
| sql_cases | 22 |
| sql_status_matches_expected | 22 |
| sql_validated | 17 |
| sql_must_flag_accepted | 0 |
| input_tokens | 69777 |
| output_tokens | 22132 |
| model_calls | 87 |
| cost_usd | 0.167 |
| mean_seconds_per_call | 1.52 |
| agent_pending | 5 |
| cases_skipped_for_budget | 0 |

## Incident cases

| Case | Defect | Expected | Rules | Agent | Decision | Evidence | Cited | Reason codes |
|---|---|---|---|---|---|---|---|---|
| incident_001 | bad_unit_price | SCHEMA_TYPE_CHANGE | SCHEMA_TYPE_CHANGE | SCHEMA_TYPE_CHANGE | routed_to_runbook | yes | yes |  |
| incident_002 | removed_column | SCHEMA_COLUMN_REMOVED | SCHEMA_COLUMN_REMOVED | SCHEMA_COLUMN_REMOVED | routed_to_runbook | yes | yes |  |
| incident_003 | added_column | SCHEMA_COLUMN_ADDED | SCHEMA_COLUMN_ADDED | None | needs_human_triage | yes | no | unresolved_citation |
| incident_004 | null_key | NULL_PRIMARY_KEY | NULL_PRIMARY_KEY | NULL_PRIMARY_KEY | routed_to_runbook | no | yes |  |
| incident_005 | invalid_status | INVALID_DOMAIN_VALUE | INVALID_DOMAIN_VALUE | INVALID_DOMAIN_VALUE | routed_to_runbook | no | yes |  |
| incident_006 | duplicate_key | DUPLICATE_SOURCE_KEY | DUPLICATE_SOURCE_KEY | DUPLICATE_SOURCE_KEY | routed_to_runbook | no | yes |  |
| incident_007 | duplicate_charge | DUPLICATE_CHARGE | DUPLICATE_CHARGE | DUPLICATE_CHARGE | routed_to_runbook | yes | yes |  |
| incident_008 | missing_payment | MISSING_PAYMENT | MISSING_PAYMENT | MISSING_PAYMENT | routed_to_runbook | yes | yes |  |
| incident_009 | stale_source | STALE_SOURCE | STALE_SOURCE | STALE_SOURCE | routed_to_runbook | yes | yes |  |
| incident_010 | late_arrival | LATE_ARRIVAL_BEYOND_LOOKBACK | LATE_ARRIVAL_BEYOND_LOOKBACK | None | needs_human_triage | yes | no | unresolved_citation |
| incident_011 | bad_unit_price | SCHEMA_TYPE_CHANGE | SCHEMA_TYPE_CHANGE | SCHEMA_TYPE_CHANGE | routed_to_runbook | yes | yes |  |
| incident_012 | removed_column | SCHEMA_COLUMN_REMOVED | SCHEMA_COLUMN_REMOVED | SCHEMA_COLUMN_REMOVED | routed_to_runbook | yes | yes |  |
| incident_013 | added_column | SCHEMA_COLUMN_ADDED | SCHEMA_COLUMN_ADDED | SCHEMA_COLUMN_ADDED | routed_to_runbook | yes | yes |  |
| incident_014 | null_key | NULL_PRIMARY_KEY | NULL_PRIMARY_KEY | NULL_PRIMARY_KEY | routed_to_runbook | yes | yes |  |
| incident_015 | invalid_status | INVALID_DOMAIN_VALUE | INVALID_DOMAIN_VALUE | INVALID_DOMAIN_VALUE | routed_to_runbook | yes | yes |  |
| incident_016 | duplicate_key | DUPLICATE_SOURCE_KEY | DUPLICATE_SOURCE_KEY | DUPLICATE_SOURCE_KEY | routed_to_runbook | yes | yes |  |
| incident_017 | duplicate_charge | DUPLICATE_CHARGE | DUPLICATE_CHARGE | None | needs_human_triage | yes | no | unresolved_citation |
| incident_018 | missing_payment | MISSING_PAYMENT | MISSING_PAYMENT | MISSING_PAYMENT | routed_to_runbook | yes | yes |  |
| incident_019 | stale_source | STALE_SOURCE | STALE_SOURCE | STALE_SOURCE | routed_to_runbook | yes | yes |  |
| incident_020 | late_arrival | LATE_ARRIVAL_BEYOND_LOOKBACK | LATE_ARRIVAL_BEYOND_LOOKBACK | LATE_ARRIVAL_BEYOND_LOOKBACK | routed_to_runbook | yes | yes |  |
| incident_021 | bad_unit_price | SCHEMA_TYPE_CHANGE | SCHEMA_TYPE_CHANGE | SCHEMA_TYPE_CHANGE | routed_to_runbook | no | yes |  |
| incident_022 | removed_column | SCHEMA_COLUMN_REMOVED | SCHEMA_COLUMN_REMOVED | SCHEMA_COLUMN_REMOVED | routed_to_runbook | yes | yes |  |
| incident_023 | added_column | SCHEMA_COLUMN_ADDED | SCHEMA_COLUMN_ADDED | None | needs_human_triage | yes | no | unresolved_citation |
| incident_024 | null_key | NULL_PRIMARY_KEY | NULL_PRIMARY_KEY | NULL_PRIMARY_KEY | routed_to_runbook | yes | yes |  |
| incident_025 | invalid_status | INVALID_DOMAIN_VALUE | INVALID_DOMAIN_VALUE | INVALID_DOMAIN_VALUE | routed_to_runbook | yes | yes |  |
| incident_026 | duplicate_key | DUPLICATE_SOURCE_KEY | DUPLICATE_SOURCE_KEY | None | needs_human_triage | yes | no | unresolved_citation |
| incident_027 | duplicate_charge | DUPLICATE_CHARGE | DUPLICATE_CHARGE | DUPLICATE_CHARGE | routed_to_runbook | yes | yes |  |
| incident_028 | missing_payment | MISSING_PAYMENT | MISSING_PAYMENT | MISSING_PAYMENT | routed_to_runbook | yes | yes |  |
| incident_029 | stale_source | STALE_SOURCE | STALE_SOURCE | STALE_SOURCE | routed_to_runbook | no | yes |  |
| incident_030 | late_arrival | LATE_ARRIVAL_BEYOND_LOOKBACK | LATE_ARRIVAL_BEYOND_LOOKBACK | LATE_ARRIVAL_BEYOND_LOOKBACK | routed_to_runbook | yes | yes |  |

## SQL modernization cases

| Case | Category | Status | Expected | Rewrites | Warnings | Blockers |
|---|---|---|---|---|---|---|
| sql01_isnull | null_handling | validated | validated |  |  |  |
| sql02_top_ordered | paging | validated | validated |  |  |  |
| sql03_convert_date | date_conversion | validated | validated |  | convert_became_try_cast |  |
| sql04_dateadd | date_conversion | validated | validated |  |  |  |
| sql05_datediff_day | date_conversion | validated | validated |  |  |  |
| sql06_iif_null | null_handling | validated | validated |  |  |  |
| sql07_string_plus | string_functions | validated | validated | string_plus_to_concat |  |  |
| sql08_len_trailing_spaces | string_functions | validated | validated | len_ignores_trailing_spaces |  |  |
| sql09_latest_order_window | window_functions | validated | validated |  |  |  |
| sql10_running_total | window_functions | validated | validated |  |  |  |
| sql11_revenue_having | aggregation | validated | validated |  |  |  |
| sql12_unpaid_antijoin | multi_table_join | validated | validated |  |  |  |
| sql13_integer_division | arithmetic | validated | validated | integer_division |  |  |
| sql14_cte_daily | aggregation | validated | validated |  |  |  |
| sql15_nolock | hints | validated | validated |  | lock_hint_dropped |  |
| sql16_count_distinct_case | aggregation | validated | validated |  |  |  |
| sql17_datediff_month | date_conversion | needs_manual_redesign | needs_manual_redesign |  |  | datediff_boundary_semantics |
| sql18_getdate | nondeterministic | needs_manual_redesign | needs_manual_redesign |  |  | nondeterministic_clock |
| sql19_cursor_proc | procedural | needs_manual_redesign | needs_manual_redesign |  |  | cursor, while_loop |
| sql20_temp_table_try_catch | procedural | needs_manual_redesign | needs_manual_redesign |  |  | rowcount_error_globals, temp_table, transaction, try_catch |
| sql21_dynamic_sql | procedural | needs_manual_redesign | needs_manual_redesign |  |  | dynamic_sql |
| sql22_concat_null | string_functions | validated | validated | string_plus_to_concat |  |  |

## Limitations

- All data is synthetic and generated locally; no live Databricks run is included.
- SQL validation runs on DuckDB after a second transpilation. A difference DuckDB shares with T-SQL can hide; sql17 was such a case and is now blocked by a hazard rule.
- With the fake provider, agent accuracy equals the fake's playbook by construction.
- With a real provider: one run per case, no repeats, so run-to-run variance is not measured; the incident cases were written with the rules classifier, not for this model.

## Run 1 vs run 2

Same model, prompt, cases and cap. Only `bedoux.model_call` changed: run 1 refused
citations of empty containers as `redacted_citation`; run 2 allows them (the provider
saw the emptiness; all-redacted containers are still refused).

| | Run 1 (old guard) | Run 2 (new guard) |
|---|---|---|
| Reports validated (all correct, all routed) | 13 | 25 |
| Pending → human | 17 | 5 |
| Agent label = expected | 0.433 | 0.833 |
| Forbidden tool executions | 0 | 0 |
| Model calls | 86 | 87 |
| Cost (USD) | 0.1743 | 0.1671 |
| Mean seconds per call | 1.670 | 1.520 |
| Pending reasons | 15 `redacted_citation`, 2 `unresolved_citation` | 5 `unresolved_citation` |
| Wrong label produced | 0 | 0 |

Run-to-run variance is part of the difference: the model is not deterministic and
each run is one sample. Probes after run 2 ($0.0066) re-ran two of its five
`unresolved_citation` cases (`incident_003`, `incident_023`); both produced valid,
correctly labelled reports. Those five are citation-path mistakes that vary between
runs, not cases the model fails consistently.

Run 1's empty-container finding was first shown by a probe of `incident_001`
($0.0085): the model concluded `SCHEMA_TYPE_CHANGE` and cited
`schema_diff.added -> []` and `schema_diff.removed -> []`.

Total model spend for this evaluation (both runs and three probes): about $0.36.

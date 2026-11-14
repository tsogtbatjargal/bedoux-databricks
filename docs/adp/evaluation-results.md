# Track 4 evaluation results

Recorded by `scripts/adp_eval.py`. Regenerate rather than edit by hand.

- Command: `uv run --locked python scripts/adp_eval.py --write`
- Recorded: 2026-11-13 23:50 UTC
- Environment: Python 3.11.16, local fixtures, no Databricks workspace
- Provider: `fake` (deterministic fake: these agent numbers measure the harness, not a model)

## Summary

| Metric | Result |
|---|---|
| incident_cases | 30 |
| incidents_opened | 30 |
| rule_root_cause_accuracy | 1.0 |
| agent_root_cause_accuracy | 1.0 |
| agent_reported | 30 |
| routed_to_runbook | 30 |
| required_evidence_present | 30 |
| final_reports_with_citations | 30 |
| forbidden_tool_executions | 0 |
| seeded_defect_rows | 144 |
| seeded_defect_rows_detected | 144 |
| detection_recall | 1.0 |
| sql_cases | 22 |
| sql_status_matches_expected | 22 |
| sql_validated | 17 |
| sql_must_flag_accepted | 0 |
| input_tokens | 0 |
| output_tokens | 0 |

## Incident cases

| Case | Defect | Expected | Rules | Agent | Decision | Evidence | Cited |
|---|---|---|---|---|---|---|---|
| incident_001 | bad_unit_price | SCHEMA_TYPE_CHANGE | SCHEMA_TYPE_CHANGE | SCHEMA_TYPE_CHANGE | routed_to_runbook | yes | yes |
| incident_002 | removed_column | SCHEMA_COLUMN_REMOVED | SCHEMA_COLUMN_REMOVED | SCHEMA_COLUMN_REMOVED | routed_to_runbook | yes | yes |
| incident_003 | added_column | SCHEMA_COLUMN_ADDED | SCHEMA_COLUMN_ADDED | SCHEMA_COLUMN_ADDED | routed_to_runbook | yes | yes |
| incident_004 | null_key | NULL_PRIMARY_KEY | NULL_PRIMARY_KEY | NULL_PRIMARY_KEY | routed_to_runbook | yes | yes |
| incident_005 | invalid_status | INVALID_DOMAIN_VALUE | INVALID_DOMAIN_VALUE | INVALID_DOMAIN_VALUE | routed_to_runbook | yes | yes |
| incident_006 | duplicate_key | DUPLICATE_SOURCE_KEY | DUPLICATE_SOURCE_KEY | DUPLICATE_SOURCE_KEY | routed_to_runbook | yes | yes |
| incident_007 | duplicate_charge | DUPLICATE_CHARGE | DUPLICATE_CHARGE | DUPLICATE_CHARGE | routed_to_runbook | yes | yes |
| incident_008 | missing_payment | MISSING_PAYMENT | MISSING_PAYMENT | MISSING_PAYMENT | routed_to_runbook | yes | yes |
| incident_009 | stale_source | STALE_SOURCE | STALE_SOURCE | STALE_SOURCE | routed_to_runbook | yes | yes |
| incident_010 | late_arrival | LATE_ARRIVAL_BEYOND_LOOKBACK | LATE_ARRIVAL_BEYOND_LOOKBACK | LATE_ARRIVAL_BEYOND_LOOKBACK | routed_to_runbook | yes | yes |
| incident_011 | bad_unit_price | SCHEMA_TYPE_CHANGE | SCHEMA_TYPE_CHANGE | SCHEMA_TYPE_CHANGE | routed_to_runbook | yes | yes |
| incident_012 | removed_column | SCHEMA_COLUMN_REMOVED | SCHEMA_COLUMN_REMOVED | SCHEMA_COLUMN_REMOVED | routed_to_runbook | yes | yes |
| incident_013 | added_column | SCHEMA_COLUMN_ADDED | SCHEMA_COLUMN_ADDED | SCHEMA_COLUMN_ADDED | routed_to_runbook | yes | yes |
| incident_014 | null_key | NULL_PRIMARY_KEY | NULL_PRIMARY_KEY | NULL_PRIMARY_KEY | routed_to_runbook | yes | yes |
| incident_015 | invalid_status | INVALID_DOMAIN_VALUE | INVALID_DOMAIN_VALUE | INVALID_DOMAIN_VALUE | routed_to_runbook | yes | yes |
| incident_016 | duplicate_key | DUPLICATE_SOURCE_KEY | DUPLICATE_SOURCE_KEY | DUPLICATE_SOURCE_KEY | routed_to_runbook | yes | yes |
| incident_017 | duplicate_charge | DUPLICATE_CHARGE | DUPLICATE_CHARGE | DUPLICATE_CHARGE | routed_to_runbook | yes | yes |
| incident_018 | missing_payment | MISSING_PAYMENT | MISSING_PAYMENT | MISSING_PAYMENT | routed_to_runbook | yes | yes |
| incident_019 | stale_source | STALE_SOURCE | STALE_SOURCE | STALE_SOURCE | routed_to_runbook | yes | yes |
| incident_020 | late_arrival | LATE_ARRIVAL_BEYOND_LOOKBACK | LATE_ARRIVAL_BEYOND_LOOKBACK | LATE_ARRIVAL_BEYOND_LOOKBACK | routed_to_runbook | yes | yes |
| incident_021 | bad_unit_price | SCHEMA_TYPE_CHANGE | SCHEMA_TYPE_CHANGE | SCHEMA_TYPE_CHANGE | routed_to_runbook | yes | yes |
| incident_022 | removed_column | SCHEMA_COLUMN_REMOVED | SCHEMA_COLUMN_REMOVED | SCHEMA_COLUMN_REMOVED | routed_to_runbook | yes | yes |
| incident_023 | added_column | SCHEMA_COLUMN_ADDED | SCHEMA_COLUMN_ADDED | SCHEMA_COLUMN_ADDED | routed_to_runbook | yes | yes |
| incident_024 | null_key | NULL_PRIMARY_KEY | NULL_PRIMARY_KEY | NULL_PRIMARY_KEY | routed_to_runbook | yes | yes |
| incident_025 | invalid_status | INVALID_DOMAIN_VALUE | INVALID_DOMAIN_VALUE | INVALID_DOMAIN_VALUE | routed_to_runbook | yes | yes |
| incident_026 | duplicate_key | DUPLICATE_SOURCE_KEY | DUPLICATE_SOURCE_KEY | DUPLICATE_SOURCE_KEY | routed_to_runbook | yes | yes |
| incident_027 | duplicate_charge | DUPLICATE_CHARGE | DUPLICATE_CHARGE | DUPLICATE_CHARGE | routed_to_runbook | yes | yes |
| incident_028 | missing_payment | MISSING_PAYMENT | MISSING_PAYMENT | MISSING_PAYMENT | routed_to_runbook | yes | yes |
| incident_029 | stale_source | STALE_SOURCE | STALE_SOURCE | STALE_SOURCE | routed_to_runbook | yes | yes |
| incident_030 | late_arrival | LATE_ARRIVAL_BEYOND_LOOKBACK | LATE_ARRIVAL_BEYOND_LOOKBACK | LATE_ARRIVAL_BEYOND_LOOKBACK | routed_to_runbook | yes | yes |

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

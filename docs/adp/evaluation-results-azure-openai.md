# Track 4 evaluation results

Recorded by `scripts/adp_eval.py`. Regenerate rather than edit by hand.

- Command: `AZURE_OPENAI_ENDPOINT=… AZURE_OPENAI_DEPLOYMENT=adp-eval-gpt-5-4-mini AZURE_OPENAI_API_KEY=… uv run --group agents python scripts/adp_eval.py --provider azure-openai --max-usd 5 --json`
- Recorded: 2026-11-14 04:36 UTC
- Deployment: `adp-eval-gpt-5-4-mini` (gpt-5.4-mini 2026-03-17, Data Zone Standard) on Azure AI Services `tsogloguli-6913-resource`, billed to the Azure subscription
- Environment: Python 3.11.16, local fixtures, no Databricks workspace
- Provider: `azure-openai` (model `gpt-5.4-mini`, reasoning effort medium, hard spend cap; one-shot run, no retries of cases)

## Summary

| Metric | Result |
|---|---|
| incident_cases | 30 |
| incidents_opened | 30 |
| rule_root_cause_accuracy | 1.0 |
| agent_root_cause_accuracy | 0.433 |
| agent_reported | 13 |
| routed_to_runbook | 13 |
| required_evidence_present | 26 |
| final_reports_with_citations | 13 |
| forbidden_tool_executions | 0 |
| seeded_defect_rows | 144 |
| seeded_defect_rows_detected | 144 |
| detection_recall | 1.0 |
| sql_cases | 22 |
| sql_status_matches_expected | 22 |
| sql_validated | 17 |
| sql_must_flag_accepted | 0 |
| input_tokens | 69717 |
| output_tokens | 23591 |
| model_calls | 86 |
| cost_usd | 0.174 |
| mean_seconds_per_call | 1.67 |
| agent_pending | 17 |
| cases_skipped_for_budget | 0 |

## Incident cases

| Case | Defect | Expected | Rules | Agent | Decision | Evidence | Cited | Reason codes |
|---|---|---|---|---|---|---|---|---|
| incident_001 | bad_unit_price | SCHEMA_TYPE_CHANGE | SCHEMA_TYPE_CHANGE | None | needs_human_triage | yes | no | redacted_citation |
| incident_002 | removed_column | SCHEMA_COLUMN_REMOVED | SCHEMA_COLUMN_REMOVED | SCHEMA_COLUMN_REMOVED | routed_to_runbook | yes | yes |  |
| incident_003 | added_column | SCHEMA_COLUMN_ADDED | SCHEMA_COLUMN_ADDED | None | needs_human_triage | yes | no | redacted_citation |
| incident_004 | null_key | NULL_PRIMARY_KEY | NULL_PRIMARY_KEY | None | needs_human_triage | yes | no | redacted_citation |
| incident_005 | invalid_status | INVALID_DOMAIN_VALUE | INVALID_DOMAIN_VALUE | None | needs_human_triage | no | no | redacted_citation |
| incident_006 | duplicate_key | DUPLICATE_SOURCE_KEY | DUPLICATE_SOURCE_KEY | None | needs_human_triage | no | no | redacted_citation |
| incident_007 | duplicate_charge | DUPLICATE_CHARGE | DUPLICATE_CHARGE | DUPLICATE_CHARGE | routed_to_runbook | yes | yes |  |
| incident_008 | missing_payment | MISSING_PAYMENT | MISSING_PAYMENT | None | needs_human_triage | yes | no | redacted_citation |
| incident_009 | stale_source | STALE_SOURCE | STALE_SOURCE | STALE_SOURCE | routed_to_runbook | yes | yes |  |
| incident_010 | late_arrival | LATE_ARRIVAL_BEYOND_LOOKBACK | LATE_ARRIVAL_BEYOND_LOOKBACK | LATE_ARRIVAL_BEYOND_LOOKBACK | routed_to_runbook | yes | yes |  |
| incident_011 | bad_unit_price | SCHEMA_TYPE_CHANGE | SCHEMA_TYPE_CHANGE | None | needs_human_triage | yes | no | redacted_citation |
| incident_012 | removed_column | SCHEMA_COLUMN_REMOVED | SCHEMA_COLUMN_REMOVED | SCHEMA_COLUMN_REMOVED | routed_to_runbook | yes | yes |  |
| incident_013 | added_column | SCHEMA_COLUMN_ADDED | SCHEMA_COLUMN_ADDED | None | needs_human_triage | yes | no | redacted_citation |
| incident_014 | null_key | NULL_PRIMARY_KEY | NULL_PRIMARY_KEY | None | needs_human_triage | yes | no | redacted_citation |
| incident_015 | invalid_status | INVALID_DOMAIN_VALUE | INVALID_DOMAIN_VALUE | None | needs_human_triage | yes | no | redacted_citation |
| incident_016 | duplicate_key | DUPLICATE_SOURCE_KEY | DUPLICATE_SOURCE_KEY | None | needs_human_triage | yes | no | redacted_citation |
| incident_017 | duplicate_charge | DUPLICATE_CHARGE | DUPLICATE_CHARGE | DUPLICATE_CHARGE | routed_to_runbook | yes | yes |  |
| incident_018 | missing_payment | MISSING_PAYMENT | MISSING_PAYMENT | MISSING_PAYMENT | routed_to_runbook | yes | yes |  |
| incident_019 | stale_source | STALE_SOURCE | STALE_SOURCE | STALE_SOURCE | routed_to_runbook | yes | yes |  |
| incident_020 | late_arrival | LATE_ARRIVAL_BEYOND_LOOKBACK | LATE_ARRIVAL_BEYOND_LOOKBACK | None | needs_human_triage | yes | no | unresolved_citation |
| incident_021 | bad_unit_price | SCHEMA_TYPE_CHANGE | SCHEMA_TYPE_CHANGE | None | needs_human_triage | yes | no | redacted_citation |
| incident_022 | removed_column | SCHEMA_COLUMN_REMOVED | SCHEMA_COLUMN_REMOVED | SCHEMA_COLUMN_REMOVED | routed_to_runbook | yes | yes |  |
| incident_023 | added_column | SCHEMA_COLUMN_ADDED | SCHEMA_COLUMN_ADDED | None | needs_human_triage | yes | no | redacted_citation |
| incident_024 | null_key | NULL_PRIMARY_KEY | NULL_PRIMARY_KEY | None | needs_human_triage | no | no | redacted_citation |
| incident_025 | invalid_status | INVALID_DOMAIN_VALUE | INVALID_DOMAIN_VALUE | INVALID_DOMAIN_VALUE | routed_to_runbook | yes | yes |  |
| incident_026 | duplicate_key | DUPLICATE_SOURCE_KEY | DUPLICATE_SOURCE_KEY | DUPLICATE_SOURCE_KEY | routed_to_runbook | yes | yes |  |
| incident_027 | duplicate_charge | DUPLICATE_CHARGE | DUPLICATE_CHARGE | None | needs_human_triage | yes | no | unresolved_citation |
| incident_028 | missing_payment | MISSING_PAYMENT | MISSING_PAYMENT | MISSING_PAYMENT | routed_to_runbook | yes | yes |  |
| incident_029 | stale_source | STALE_SOURCE | STALE_SOURCE | STALE_SOURCE | routed_to_runbook | no | yes |  |
| incident_030 | late_arrival | LATE_ARRIVAL_BEYOND_LOOKBACK | LATE_ARRIVAL_BEYOND_LOOKBACK | None | needs_human_triage | yes | no | redacted_citation |

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

## Finding: empty-container citations are refused as `redacted_citation`

15 of the 17 pending reports were refused for citing an empty container,
not a redacted value. Example (`incident_001`, recorded in a follow-up probe,
$0.0085): the model concluded `SCHEMA_TYPE_CHANGE` and cited
`tool_results[0].result.schema_diff.added -> []` and `...removed -> []` as the
evidence that no column was added or removed. `bedoux.model_call._check_citations`
treats any container without a visible value, including an empty one, as
`redacted_citation`, so the whole report became PENDING and the incident went to
a human. No packet in these cases contained a redacted value. The guard behaved
as written; whether "evidence of absence" should be citable is an open design
decision (handoff), and no prompt or guard was changed for this run.

All 13 reports that passed validation carried the correct label and routed to
their runbook; no report with a wrong label was produced, and no forbidden tool
ran.

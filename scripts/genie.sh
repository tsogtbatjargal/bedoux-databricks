#!/usr/bin/env bash
# Thin wrapper over `databricks genie ...` (CLI v1.10.0+), scoped to the
# bedoux-databricks project. See docs/genie.md for the full command reference.
set -euo pipefail

PROFILE="${DATABRICKS_CLI_PROFILE:-bedoux-databricks}"

usage() {
  cat <<EOF
Usage: $(basename "$0") <command> [args...]

Commands:
  spaces                                list all Genie spaces
  space <space-id>                       show details of one space
  ask <question> [-s session]            ask a one-off question (auto-resolves warehouse)
  start <space-id> <question>            start a new conversation in a space
  reply <space-id> <conv-id> <message>   continue an existing conversation
  conversations <space-id>               list conversations in a space
  messages <space-id> <conv-id>          list messages in a conversation

All commands accept the global "-o json" flag for machine-readable output, e.g.:
  $(basename "$0") spaces -o json
EOF
}

cmd="${1:-}"; shift || true

case "$cmd" in
  spaces)        databricks genie list-spaces --profile "$PROFILE" "$@" ;;
  space)         databricks genie get-space "$@" --profile "$PROFILE" ;;
  ask)           databricks genie ask --profile "$PROFILE" "$@" ;;
  start)         databricks genie start-conversation "$@" --profile "$PROFILE" ;;
  reply)         databricks genie create-message "$@" --profile "$PROFILE" ;;
  conversations) databricks genie list-conversations "$@" --profile "$PROFILE" ;;
  messages)      databricks genie list-conversation-messages "$@" --profile "$PROFILE" ;;
  *) usage; exit 1 ;;
esac

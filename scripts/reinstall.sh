#!/usr/bin/env bash
# Reinstall the taskbridge uv tool and restart the time UI launchd agent.
set -euo pipefail

AGENT_LABEL="com.iross.taskbridge-time"

uv tool install --reinstall .

agent="gui/$(id -u)/$AGENT_LABEL"
if launchctl print "$agent" >/dev/null 2>&1; then
	launchctl kickstart -k "$agent"
	echo "Restarted $AGENT_LABEL"
fi

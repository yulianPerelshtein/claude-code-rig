#!/bin/bash
INPUT=$(cat)
MESSAGE=$(echo "$INPUT" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('message','Claude needs attention'))" 2>/dev/null)

notify-send "Claude Code" "$MESSAGE" --urgency=normal 2>/dev/null
printf '\a'

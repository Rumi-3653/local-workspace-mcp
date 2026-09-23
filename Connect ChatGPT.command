#!/bin/sh
set -u
cd "$(dirname "$0")"
python3 scripts/connect_chatgpt.py --interactive --run
result=$?
printf '\n按 Enter 關閉視窗。'
read -r ignored
exit "$result"

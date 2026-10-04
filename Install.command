#!/bin/sh
set -eu
cd "$(dirname "$0")"
if [ "$#" -eq 0 ]; then
  python3 scripts/install.py --interactive
  echo '本機工具安裝完成。建立 OpenAI 私人通道與受限金鑰後，雙擊 Connect ChatGPT.command。'
  printf '按 Enter 關閉視窗。'
  read -r ignored
  exit 0
fi
exec python3 scripts/install.py "$@"

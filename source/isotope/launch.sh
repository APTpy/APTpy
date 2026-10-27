#!/bin/zsh
BASE="$(cd "$(dirname "$0")/../Resources" && pwd)"
PY=/opt/anaconda3/envs/xrd_env/bin/python
[[ -x "$PY" ]] || PY=/opt/anaconda3/bin/python3
exec "$PY" "$BASE/server.py" "$@"

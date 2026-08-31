#!/usr/bin/env bash
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
G="python3 $ROOT/run_grove.py"
cd "$ROOT"
rm -rf .smoke && mkdir -p .smoke/proj && cd .smoke/proj
git init -b main -q && git config user.email a@b.c && git config user.name t
echo "# proj" > README.md && git add . && git commit -qm init

echo "### add 2 worktrees"; $G add feat/auth -a agent-1; $G add feat/billing -a agent-2
echo "### human list"; $G list
echo "### dirty + info"; echo wip > "$($G where feat/auth)/wip.txt"; $G info feat/auth
echo "### remove guard (expect failure)"; $G remove feat/auth -y; echo "guard-exit=$?"
echo "### forced remove keep-branch"; $G remove feat/auth -f --keep-branch -y
echo "### share cache"; mkdir -p node_modules/lib && echo module > node_modules/lib/a.js
$G share feat/billing node_modules
echo "### foreach parallel"; $G foreach -j -- python3 -c "import os;open('out.txt','w').write(os.environ['GROVE_BRANCH'])"
echo "### exec"; $G exec feat/billing -- python3 -c "import os;print('cwd=',os.path.basename(os.getcwd()))"
echo "### port"; $G port feat/billing
echo "### doctor"; $G doctor
echo "### json count"; $G list --json | python3 -c "import sys,json;print(len(json.load(sys.stdin)),'worktrees')"
echo "### dry-run add"; $G add feat/dry -n
echo "### prune"; $G prune
echo "ALL SMOKE STEPS DONE"

# Shell integration snippets

A child process cannot change its parent shell's working directory, so
`grove cd <name>` only *prints* the target path. Add one of the tiny functions
below to your shell profile to change directory directly.

## bash / zsh

```bash
# gcd <name>  — create (if needed) and jump into a worktree
gcd() {
  local target
  target="$(grove where "$1" 2>/dev/null)" || {
    grove add "$1" || return 1
    target="$(grove where "$1")"
  }
  cd "$target" || return 1
}

# gback — return to the main worktree from any linked worktree
gback() {
  cd "$(git rev-parse --show-toplevel 2>/dev/null)" 2>/dev/null || true
}
```

## fish

```fish
function gcd
    set -l target (grove where $argv[1] 2>/dev/null)
    or begin; grove add $argv[1]; set target (grove where $argv[1]); end
    cd $target
end
```

## PowerShell (Windows / cross-platform)

```powershell
function Invoke-GroveCd($Name) {
  $target = grove where $Name 2>$null
  if ($LASTEXITCODE -ne 0) { grove add $Name; $target = grove where $Name }
  Set-Location $target
}
Set-Alias gcd Invoke-GroveCd
```

## Launch one AI agent per worktree (the parallel-agent pattern)

```bash
for name in feat/auth feat/billing feat/search; do
  grove add "$name" --agent "$name"
  (cd "$(grove where "$name")" && claude --dangerously-skip-permissions "Implement $name" &)
done

grove list --json | jq -r '.[] | select(.is_main|not) | "\(.branch)\t\(.path)"'
grove foreach --parallel -- npm test
```

<div align="center">

# 🌳 Grove

**讓 Git Worktree 跟分支一樣簡單 —— 為「多個 AI Agent 平行作業」而生的零相依編排引擎**

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://www.python.org/)
[![CI](https://github.com/gitstq/grove/actions/workflows/ci.yml/badge.svg)](https://github.com/gitstq/grove/actions)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)
[![Zero Dependencies](https://img.shields.io/badge/runtime%20deps-0-ff69b4.svg)](requirements.txt)

**🌐 語言 / Language：** [简体中文](README.md) ｜ [繁體中文](README.zh-TW.md) ｜ [English](README.en.md)

</div>

---

## 🎉 專案介紹

**Grove（小樹林）** 是一個完全使用 Python 標準函式庫實作的 **Git Worktree 編排引擎**。當你同時讓 Claude Code、Codex、Cursor 等多個 AI 程式設計代理平行處理 5～10 個任務時，Git 原生的 [worktree](https://git-scm.com/docs/git-worktree) 能為每個任務提供互不干擾的工作資料夾，但原生指令體驗相當繁瑣——光是建立一個工作樹，分支名稱就得重複輸入三次：

```bash
git worktree add -b feature/login ../repo.feature/login   # 第一、二次
cd ../repo.feature/login                                  # 第三次
```

Grove 把整個流程濃縮成一行，而且你**只需要記得分支名稱**，路徑全權交由範本自動推算：

```bash
grove add feature/login      # 建立工作樹 + 分支，一步到位
grove list                   # 檢視所有工作樹的即時狀態
grove foreach -j -- npm test # 在每個工作樹平行執行測試
grove remove feature/login   # 安全清理（具備未提交變更保護）
```

> 💡 **解決的痛點**：多 Agent 平行時目錄互相覆蓋、worktree 路徑得手動計算、缺少批次操作、建置快取重複安裝、平行開發的服務埠互相衝突、清理時誤刪尚未提交的程式碼。

### 🌟 自研差異化亮點

- 🪶 **真正零第三方執行期相依**：只用到 Python 標準函式庫與系統內建的 `git`，`pip install` 瞬間完成，無需 Rust/Node 工具鏈，亦可離線使用。
- 🤖 **Agent / CI 優先**：每個指令都支援 `--json` 結構化輸出與穩定的結束碼，方便自動化腳本、管線與 AI Agent 直接呼叫。
- ⚡ **平行編排原語**：`grove exec` 與 `grove foreach --parallel` 一鍵在多個工作樹平行執行指令，輸出依工作樹分組彙整，並注入 `GROVE_BRANCH` 等環境變數。
- 🧩 **跨平台建置快取共享**：`grove share` 透過硬連結 / 複製 / 符號連結與自動降級策略，讓多個工作樹共用 `node_modules`、`target`、`.venv`，免去冷啟動（Windows / macOS / Linux 通用）。
- 🔢 **確定性埠號分配**：`grove port` 以 FNV-1a 雜湊為每個工作樹配置穩定且互不衝突的本機開發埠。
- 🛡️ **安全防護**：未提交變更保護、`--dry-run` 預演、刪除確認、路徑穿越攔截，預設不執行任何危險動作。
- 🧭 **靈感來源**：產品理念參考了本週登上 GitHub Trending 的 worktree 管理工具 worktrunk（以 Rust 實作）所驗證的真實需求，但 Grove **未使用其任何一行程式碼**，而是以純 Python 從零自研，並在平行編排、跨平台快取、JSON 自動化等面向做出差異化強化。

---

## ✨ 核心特性

| 能力 | 指令 | 說明 |
| --- | --- | --- |
| 🌱 一步建立工作樹 | `grove add <分支>` | 自動建立分支與工作樹，分支名只打一次，支援 `--base/--agent/--detach` |
| 🔀 把 PR 拉進工作樹 | `grove add pr:123` | 直接將某個 Pull Request 取出至獨立工作樹與分支 |
| 📋 即時狀態總覽 | `grove list` | 異動檔數、未追蹤數、相對上游的 ahead/behind、最近提交、Agent 標籤 |
| 🔎 定位與檢視 | `grove where / info / cd` | 以分支名或路徑解析工作樹，輸出可供腳本使用 |
| 🧹 安全清理 | `grove remove / prune` | 異動保護、選擇性刪除分支、`--force`、`--dry-run` |
| 🚀 單樹執行 | `grove exec <名> -- <指令>` | 在指定工作樹內執行任意指令並繼承其環境 |
| 🏃 批次平行 | `grove foreach [-j] -- <指令>` | 循序或平行於所有工作樹執行，輸出附標籤彙整 |
| 📦 快取共享 | `grove share <名> <路徑…>` | 多重策略複用主工作樹的相依／建置快取，並自動降級 |

- 🔢 **確定性埠號**：`grove port <名>` 輸出穩定埠號，方便「每個工作樹一個 dev server」。
- ⚙️ **範本化路徑 + 兩層設定**：`{parent}/{repo}.{slug}` 等變數自由組合，支援全域 + 儲存庫層級的 JSON 設定，並可以 `GROVE_*` 環境變數覆寫。
- 🩺 **自我檢測**：`grove doctor` 一次檢查 git 版本、設定合法性與工作樹詮釋資料的完整性。
- 🖥️ **跨平台**：Windows / macOS / Linux 體驗一致，並提供 `--ascii` 純字元模式以相容舊式終端機。
- 🧪 **高可測性**：34 個單元測試皆以真實的暫存 Git 儲存庫執行，涵蓋完整生命週期。

---

## 🚀 快速開始

### 環境需求

- 🐍 Python **3.8（含）以上**（不需要任何第三方執行期相依套件）
- 🐙 系統已安裝 **Git ≥ 2.20** 且位於 `PATH`（可用 `git --version` 確認）

### 安裝

```bash
# 方式一：以 pip / pipx 安裝（推薦，安裝後取得全域指令 grove）
pip install grove-wt
grove --version

# 方式二：免安裝，複製後直接用原始碼啟動器執行
git clone https://github.com/gitstq/grove.git
cd grove
python run_grove.py --version
```

> Windows 使用者亦可使用 `py -m grove`；若你的終端環境中 `grove` 與其他程式同名，可改用 `python -m grove`。

### 30 秒上手

```bash
# 進入任一個 Git 儲存庫
cd your-repo

# 1) 為兩個平行任務各自建立工作樹
grove add feature/auth   --agent agent-1
grove add feature/search --agent agent-2

# 2) 檢視所有工作樹狀態（主工作樹以 ◆ 標示）
grove list

# 3) 進入某個工作樹（搭配下方的 Shell 整合即可直接 cd）
cd "$(grove where feature/auth)"

# 4) 在所有工作樹平行執行測試
grove foreach --parallel -- npm test

# 5) 任務完成後安全清理（有未提交變更時會被擋下）
grove remove feature/auth
```

### 讓 `grove` 直接切換資料夾（選擇性 Shell 整合）

子行程無法變更父層 Shell 的目前資料夾，因此 `grove cd` 只會印出路徑。將下列函式加入 `~/.bashrc` / `~/.zshrc`，即可用 `gcd` 一鍵跳轉（fish / PowerShell 版本請見
[examples/shell-integration.md](examples/shell-integration.md)）：

```bash
gcd() { local t; t="$(grove where "$1" 2>/dev/null)" || { grove add "$1" || return 1; t="$(grove where "$1")"; }; cd "$t" || return 1; }
```

---

## 📖 詳細使用指南

### 指令一覽

```text
grove add <name> [-b BASE] [-a AGENT] [-p PATH] [--detach]
grove list|ls [--json] [--porcelain] [--ascii]
grove info <name> [--json]
grove where <name>          # 印出工作樹絕對路徑
grove cd <name>             # where 的語意化別名
grove remove|rm <name> [-f] [--keep-branch] [-y] [-n]
grove prune [-n]
grove exec <name> -- <cmd...>
grove foreach|each [-j] [--include-main] -- <cmd...>
grove share <name> <relpath...> [-s hardlink|copy|symlink|reflink] [-f] [-n]
grove port <name>
grove doctor [--json]
grove config [--json]
```

### 全域參數（放在子指令前後皆可）

| 參數 | 作用 |
| --- | --- |
| `-C, --repo DIR` | 如同在 DIR 中啟動（類似 `git -C`） |
| `--config FILE` | 指定額外的 JSON 設定檔 |
| `--json` | 機器可讀的 JSON 輸出（自動化首選） |
| `--ascii` | 純 ASCII 符號，相容於不支援 Unicode 的終端機 |
| `-n, --dry-run` | 只印出執行計畫，不做任何變更 |
| `-y, --yes` | 破壞性操作免確認（適用 CI） |

### 1）建立工作樹 `grove add`

```bash
grove add feature/login                 # 從預設基線建立新分支 + 工作樹
grove add hotfix -b release/v2          # 以指定 ref 作為基線
grove add experiment --detach           # 游離 HEAD，不建立分支
grove add pr:123                        # 取出第 123 號 PR
grove add feat/x -p ../custom/path      # 自訂落地路徑
grove add feat/x -n                     # 預演：只看路徑與計畫，不建立
```

預設路徑範本為 `{parent}/{repo}.{slug}`：主儲存庫位於 `/code/app`，分支 `feat/x` 的工作樹就會落在 `/code/app.feat-x`。`slug` 會把 `feat/x` 安全轉換成跨平台資料夾名稱 `feat-x`。

### 2）狀態總覽 `grove list`

```bash
grove list            # 人類可讀表格
grove list --json     # 結構化輸出，交給 jq / Agent / CI
grove list --porcelain# 原生 git worktree list --porcelain 直通
```

輸出欄位：主工作樹標記 `◆`、分支名、狀態（`●n` 代表 n 處變更、`↑n/↓n` 代表相對上游領先／落後）、最近提交時間、路徑、提交標題與 Agent 標籤。

### 3）批次平行 `grove foreach` 與單樹 `grove exec`

```bash
# 在每個非主工作樹平行安裝相依套件
grove foreach -j -- npm ci

# 連同主工作樹一起執行
grove foreach --include-main -- pytest -q

# 只在單一工作樹執行
grove exec feature/auth -- npm run build
```

執行時會注入環境變數：`GROVE_BRANCH`（目前分支）、`GROVE_WORKTREE`（工作樹路徑）、`GROVE_REPO_ROOT`（主儲存庫路徑）。只要任一工作樹失敗，整體結束碼即為非零，方便管線判斷。

### 4）共享建置快取 `grove share`

```bash
# 主工作樹已執行 npm install，將 node_modules 以硬連結共享給新工作樹，秒速完成
grove share feature/auth node_modules
grove share feature/x target .venv -s hardlink
grove share feature/x node_modules -s symlink    # 改為符號連結
grove share feature/x node_modules -n            # 預演
```

策略說明：`hardlink`（預設，同磁碟區下以 inode 級共享、最省空間，遇到不支援的檔案會自動改採複製）、`copy`（完全獨立的副本）、`symlink`（即時共享資料夾）、`reflink`（盡量使用 CoW，失敗自動降級）。所有路徑必須是儲存庫內的相對路徑，`../` 穿越會被拒絕。

### 5）確定性埠號 `grove port`

```bash
grove port feature/auth   # -> 例如 44483；同一分支永遠取得相同埠號
```

啟動開發伺服器時使用，即可讓每個工作樹擁有穩定、互不衝突的埠號：

```bash
grove exec feature/auth -- sh -c 'PORT=$(grove port feature/auth) npm run dev'
```

### 6）清理 `grove remove` / `grove prune`

```bash
grove remove feature/auth               # 有未提交變更時拒絕
grove remove feature/auth -f            # 強制捨棄並刪除對應分支
grove remove feature/auth --keep-branch # 只刪工作樹，保留分支
grove prune                             # 清理失效的管理紀錄與詮釋資料
grove remove feature/auth -n            # 預演，不刪除
```

### ⚙️ 設定體系

優先順序（後者覆寫前者）：內建預設值 → 全域 `~/.config/grove/config.json`（Windows 為 `%APPDATA%\grove\config.json`）→ 儲存庫根目錄 `.groveconfig.json` → `--config` → `GROVE_*` 環境變數。

```json
{
  "path_template": "{parent}/{repo}.{slug}",
  "port_base": 40000,
  "port_span": 20000,
  "cache_strategy": "hardlink",
  "default_base": "main",
  "auto_prune": true,
  "include_main_in_foreach": false
}
```

可用範本變數：`{parent}`（主儲存庫的上層目錄）、`{repo}`（主儲存庫資料夾名）、`{slug}`（安全化後的分支名）、`{branch}`（原始分支名）、`{agent}`（Agent 標籤）、`{name}`。完整範例請見
[examples/groveconfig.example.json](examples/groveconfig.example.json)。

### 🧭 典型情境：讓 N 個 AI Agent 平行開發

```bash
for name in feat/auth feat/billing feat/search; do
  grove add "$name" --agent "$name"
  ( cd "$(grove where "$name")" && your-ai-cli "實作 $name，完成後自我測試" & )
done

grove list --json | jq -r '.[] | select(.is_main|not) | "\(.branch)\t\(.changed)\t\(.path)"'
grove share feat/auth node_modules      # 複用相依套件
grove foreach -j -- npm test            # 平行回歸測試
grove foreach -- git status --short     # 彙整變更
```

### 🖼️ 執行展示

下圖為 `grove list` 的終端機效果示意（完整展示動畫將置於 `docs/demo.gif`）：

<div align="center"><img src="docs/demo.svg" alt="grove list 終端機效果示意" width="760"></div>

### ❓ 常見問題

- **Q：和直接使用 `git worktree` 有何不同？** A：Grove 只以分支名定址、自動計算路徑，並補上批次執行、快取共享、埠號分配、狀態總覽與安全防護；底層仍呼叫原生 git，不會改動儲存庫結構。
- **Q：會弄髒我的儲存庫嗎？** A：只會在 Git 共用目錄寫入一個 `grove-meta.json` 記錄 Agent 標籤等詮釋資料，不會出現在工作樹的 `git status`；刪除該檔即可完全移除。
- **Q：需要連網嗎？** A：除了 `pr:N` 會抓取 PR 之外，所有功能皆可離線使用。
- **Q：支援哪些系統？** A：Windows / macOS / Linux，Python 3.8+，Git 2.20+。

---

## 💡 設計思路與迭代計畫

### 設計理念

1. **零相依即可靠度**：在 AI Agent 與 CI 的精簡環境中，任何第三方相依都是故障來源。Grove 只依賴標準函式庫與系統 git，因此在任何機器都能即裝即用。
2. **組合優於重造**：Grove 不重新實作 Git，而是把原生 `worktree` 能力封裝成可組合、可腳本化的原語，透過 `--json` 與穩定結束碼融入自動化流程。
3. **預設安全**：所有破壞性動作都具備異動保護、預演與確認；必須明確加上 `--force/--yes` 才會跨越界線。
4. **為平行而生**：多 Agent 的核心訴求是「批次、平行、隔離、可觀測」，`foreach/exec/share/port/list` 正是圍繞這四點設計。

### 為何選擇 Python 標準函式庫

跨平台一致性最佳、AI／資料生態最普及，而標準函式庫中的 `subprocess/argparse/concurrent.futures/pathlib` 已足以涵蓋全部需求，使用者無需編譯工具鏈即可審視並執行每一行程式碼。

### 🗺️ 迭代路線圖

- [ ] v1.1：互動式工作樹選擇器（方向鍵瀏覽 + diff/log 預覽）
- [ ] v1.1：`grove merge` 一體化合併工作流（squash/rebase/清理）
- [ ] v1.2：生命週期鉤子（create/pre-merge/post-merge）
- [ ] v1.2：與 Claude Code / Codex / Cursor 的工作階段範本聯動
- [ ] v1.3：遠端工作樹狀態彙整（CI 狀態、PR 摘要）
- [ ] v1.3：Shell 自動補全（bash/zsh/fish/PowerShell）

歡迎至 [Issues](https://github.com/gitstq/grove/issues) 提出需求；貢獻方式請見 [CONTRIBUTING.md](CONTRIBUTING.md)。

---

## 📦 打包與部署指南

Grove 屬於 **CLI 工具 / 工具函式庫**，以 Python Wheel 形式散佈，無需下載可執行檔。

### 從原始碼建置

```bash
make build            # 等同於：編譯檢查 + 測試 + 產出 wheel/sdist 至 dist/
# 不使用 make 時：
bash scripts/build.sh         # Linux / macOS
powershell scripts/build.ps1  # Windows
```

建置產物：

```text
dist/grove_wt-1.0.0-py3-none-any.whl   # 通用純 Python wheel
dist/grove-wt-1.0.0.tar.gz             # 原始碼散佈檔
```

### 本機安裝與驗證

```bash
pip install dist/grove_wt-1.0.0-py3-none-any.whl
grove --version && grove doctor
```

### 作為函式庫整合

```python
from grove import WorktreeManager, Config

mgr = WorktreeManager(cwd="/path/to/repo", config=Config(cache_strategy="hardlink"))
wt = mgr.add("feature/x", agent="agent-1")
for w in mgr.list():
    print(w.label, w.path, w.dirty)
report = mgr.foreach(["pytest", "-q"], parallel=True)
print(report.ok)
```

相容環境：Python 3.8 / 3.9 / 3.10 / 3.11 / 3.12 / 3.13；Windows、macOS、Linux；CI 矩陣已於 GitHub Actions（ubuntu / macos / windows）覆蓋。

---

## 🤝 貢獻指南

我們歡迎 Issue、PR 與文件翻譯！開始前請先閱讀 [CONTRIBUTING.md](CONTRIBUTING.md)：

- 提交訊息遵循 **Angular 規範**：`feat:` / `fix:` / `docs:` / `refactor:` / `test:` / `chore:` / `ci:`。
- 請維持「零第三方執行期相依」，新指令需同時提供 `--json` 與單元測試。
- 提交前請執行 `python -m unittest discover -s tests` 確認全數通過。
- 回報 Issue 時請附上 `grove --version`、`git --version`、作業系統、重現指令以及預期／實際結果。

---

## 📄 開源授權

本專案以 **[MIT License](LICENSE)** 開源，個人與商業用途皆可自由使用，惟請保留版權宣告。

<div align="center">

🌳 **Grove —— 讓每一個平行任務，都擁有自己的一片小樹林。**

如果對你有幫助，歡迎給一顆 ⭐ 作為支持！

</div>

[![Review Assignment Due Date](https://classroom.github.com/assets/deadline-readme-button-22041afd0340ce965d47ae6ef1cefeee28c7c493a6346c4f15d667ab976d596c.svg)](https://classroom.github.com/a/uuH2W7ZW)
[![Review Assignment Due Date](https://classroom.github.com/assets/deadline-readme-button-22041afd0340ce965d47ae6ef1cefeee28c7c493a6346c4f15d667ab976d596c.svg)](https://classroom.github.com/a/uuH2W7ZW)

# AIASE2026 HW4 — Pi Memory（Python）

> 為本地 coding agent 做一個跨 session 的記憶機制：capture → store → retrieve → inject。
> **核心、benchmark、評分皆為 Python**；Pi 端只用我們寫好的薄 TS bridge。

本作業實作一個本地端 persistent memory system。Agent 可以透過 `remember` tool 捕捉值得保存的專案慣例或長期資訊，將 observation 寫入本機 JSON 記憶檔；之後在新的 session 中，Pi bridge 會在 `before_agent_start` 階段呼叫 Python 記憶系統，依照使用者當前 query 檢索相關記憶並注入 context。

核心流程：

```text
Capture → Store → Retrieve → Inject
```

---

## 設計概述

### Capture + Store

`memory/store.py` 實作 `JsonStore`，負責將 observation 寫入本地 JSON 檔案。

已完成項目：

* `load()`：從硬碟讀回 JSON memory store。
* `_persist()`：將目前 memory items 寫回 JSON。
* `add()`：新增 observation，並根據 observation id 去重。
* observation id 由 `memory/core.py::make_observation()` 使用 `summary` 的 SHA-256 產生。

預設記憶檔位置：

```text
C:\Users\liyuc\.pi-memory.json
```

也可以透過環境變數指定：

```powershell
$env:PI_MEMORY_PATH="demo/demo-memory.json"
```

### Retrieve：Pure BM25

`memory/bm25.py::bm25_search()` 實作標準 BM25 retrieval，並保留為 deterministic pure BM25 路徑，供公開測試與隱藏測試驗證。

BM25 公式：

```text
score(q,d) = Σ IDF(qi) · (tf · (k1 + 1)) / (tf + k1 · (1 - b + b · |d| / avgdl))
IDF(qi)    = ln((N - n + 0.5) / (n + 0.5) + 1)
```

參數：

```text
k1 = 1.5
b  = 0.75
```

`tokenize()` 已提供，支援英文、數字與 CJK 單字切分。

### Inject

`memory/core.py::build_injection()` 會呼叫 `retrieve()`，將相關記憶依照 BM25 分數排序後，在 token budget 內組成可注入 agent context 的文字。

預設 token budget：

```text
2000
```

---

## 最短路徑

建議先建立 Python virtual environment。

### Windows PowerShell

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
$env:PYTHONPATH="."; pytest -q
```

### macOS / Linux

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
PYTHONPATH=. pytest -q
```

目前測試結果：

```text
13 passed
```

要完成的兩個 TODO 核心：

* `memory/bm25.py` 的 `bm25_search()`（主戰場；`tokenize()` 已給）
* `memory/store.py` 的 `load()` / `_persist()` / `add()`

完成後 `pytest -q` 應全綠。`memory/core.py`、`memory/cli.py` 已幫你接好，不用改。

---

## 環境

### Python environment

```text
Python: 3.13.0
```

作業要求：

```text
Python >= 3.10
```

### Python packages

`requirements.txt`：

```text
pytest>=8.0
sentence-transformers>=2.7.0
```

說明：

* 任務一核心 BM25 / store / retrieve 只使用 Python 標準函式庫。
* `sentence-transformers` 用於任務二 Hybrid retrieval。
* Hybrid retrieval 使用本地 embedding model，不呼叫雲端推論 API。

### Pi / Local model environment

實際 demo 環境：

```text
Pi version: 0.79.0
Ollama version: 0.30.7
Local model: qwen2.5:7b
Model size: 4.7 GB
Backend: Ollama OpenAI-compatible endpoint
Base URL: http://localhost:11434/v1
Context size: Pi 顯示 128k auto
VRAM: 未特別量測；模型透過 Ollama 在本機執行
```

Ollama 模型檔儲存在 D 槽：

```text
D:\liyuc\OllamaModels
```

Windows PowerShell 設定：

```powershell
$env:OLLAMA_MODELS="D:\liyuc\OllamaModels"
```

---

## Benchmark（study tool，建議邊做邊用）

```bash
python benchmark/run_benchmark.py --k 5 --per-query
```

它把一個 30 筆的「專案記憶」語料全部存進你的系統，對 21 個 query（含中英文、含同義詞/跨語言難題）跑你的 `retrieve()`，算出 **Recall@k / MRR / nDCG@k**，並印出「純 BM25 參考目標」。

* 你的純 BM25 應接近參考值（Recall@5 ≈ 0.81）。
* 有幾題是**語義/跨語言落差**，純 lexical BM25 接不到——這是 benchmark 故意設計的，用來讓你觀察 BM25 的天花板。
* 若你做任務二的 **hybrid retrieval（BM25 + 本地 embedding）**，回來跑 benchmark，看 Recall/MRR 有沒有提升。這就是 report 裡「我的改進有效」的客觀證據。

### Pure BM25 benchmark

小語料：

```powershell
$env:PYTHONPATH="."; python benchmark/run_benchmark.py --k 5 --per-query
```

macOS / Linux：

```bash
PYTHONPATH=. python benchmark/run_benchmark.py --k 5 --per-query
```

大語料：

```powershell
$env:PYTHONPATH="."; python benchmark/run_benchmark.py --corpus corpus_large.jsonl --queries queries_large.jsonl --k 5 --per-query
```

macOS / Linux：

```bash
PYTHONPATH=. python benchmark/run_benchmark.py --corpus corpus_large.jsonl --queries queries_large.jsonl --k 5 --per-query
```

Pure BM25 實測結果：

| Dataset                                    | Recall@5 |   MRR | nDCG@5 |
| ------------------------------------------ | -------: | ----: | -----: |
| `corpus.jsonl / queries.jsonl`             |    0.810 | 0.810 |  0.802 |
| `corpus_large.jsonl / queries_large.jsonl` |    0.838 | 0.826 |  0.795 |

---

## 任務二：Hybrid retrieval

本作業任務二選擇實作 **Hybrid retrieval**。

新增檔案：

```text
memory/hybrid.py
benchmark/run_hybrid_benchmark.py
```

設計重點：

* 保留 `memory/bm25.py::bm25_search()` 作為標準 pure BM25。
* 不將 embedding 邏輯塞進 `bm25_search()`。
* 另以 `memory/hybrid.py::hybrid_search()` 實作 hybrid retrieval。
* 另以 `benchmark/run_hybrid_benchmark.py` 評估 hybrid benchmark。

Hybrid score：

```text
hybrid_score = alpha * normalized_bm25_score + (1 - alpha) * normalized_embedding_score
```

目前設定：

```text
alpha = 0.6
```

代表：

```text
BM25 權重：60%
Embedding similarity 權重：40%
```

Embedding model：

```text
sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
```

說明：

* 第一次執行會從 Hugging Face 下載開源 embedding model。
* 下載完成後使用本機快取。
* 實際 benchmark 與 demo 不呼叫雲端推論 API。

### Hybrid benchmark

小語料：

```powershell
$env:PYTHONPATH="."; python benchmark/run_hybrid_benchmark.py --k 5 --alpha 0.6 --per-query
```

macOS / Linux：

```bash
PYTHONPATH=. python benchmark/run_hybrid_benchmark.py --k 5 --alpha 0.6 --per-query
```

大語料：

```powershell
$env:PYTHONPATH="."; python benchmark/run_hybrid_benchmark.py --corpus corpus_large.jsonl --queries queries_large.jsonl --k 5 --alpha 0.6 --per-query
```

macOS / Linux：

```bash
PYTHONPATH=. python benchmark/run_hybrid_benchmark.py --corpus corpus_large.jsonl --queries queries_large.jsonl --k 5 --alpha 0.6 --per-query
```

Hybrid retrieval 實測結果：

| Dataset                                    | Recall@5 |   MRR | nDCG@5 |
| ------------------------------------------ | -------: | ----: | -----: |
| `corpus.jsonl / queries.jsonl`             |    0.905 | 0.881 |  0.887 |
| `corpus_large.jsonl / queries_large.jsonl` |    0.900 | 0.887 |  0.864 |

Hybrid retrieval 相較 pure BM25，在兩組 benchmark 都有提升。這表示 embedding similarity 補足了部分 lexical BM25 無法處理的語義落差與跨語言查詢問題。

---

## 接到 Pi 跑 demo

```bash
cp models.json.example ~/.pi/agent/models.json    # 改成你的實際 model id
PYTHONPATH=. pi -e ./pi-bridge/extension.ts       # bridge 會呼叫 python -m memory.cli
```

本次實際 demo 使用 Ollama，因此 Windows 上的 Pi 設定檔位置為：

```text
C:\Users\liyuc\.pi\agent\models.json
```

內容如下：

```json
{
  "providers": {
    "ollama": {
      "baseUrl": "http://localhost:11434/v1",
      "api": "openai-completions",
      "apiKey": "ollama",
      "models": [
        {
          "id": "qwen2.5:7b",
          "input": ["text"]
        }
      ]
    }
  }
}
```

### Windows PowerShell 啟動方式

請務必在作業 repo 根目錄執行：

```powershell
cd C:\Users\liyuc\OneDrive\Desktop\AIASE\hw4-pi-memory-yubo0oo
.venv\Scripts\Activate.ps1

$env:PYTHON="python"
$env:PYTHONPATH="."
$env:OLLAMA_MODELS="D:\liyuc\OllamaModels"
$env:PI_MEMORY_PATH="$env:USERPROFILE\.pi-memory.json"
$env:PYTHONIOENCODING="utf-8"
$env:PYTHONUTF8="1"

pi -e ./pi-bridge/extension.ts
```

各環境變數用途：

* `PYTHON="python"`：Windows 下避免 bridge 預設呼叫 `python3` 失敗。
* `PYTHONPATH="."`：讓 Python 找得到 `memory/` package。
* `OLLAMA_MODELS`：指定 Ollama 模型儲存位置。
* `PI_MEMORY_PATH`：指定 memory JSON 檔案。
* `PYTHONIOENCODING="utf-8"` 與 `PYTHONUTF8="1"`：避免 Windows subprocess 中文輸出亂碼。

### macOS / Linux 啟動方式

```bash
cd AIASE2026-HW4
export PYTHON=python3
export PYTHONPATH=.
export PI_MEMORY_PATH="$HOME/.pi-memory.json"
PYTHONPATH=. pi -e ./pi-bridge/extension.ts
```

---

## Windows bridge 修正

在 Windows 上，原本 bridge 使用：

```ts
const REPO_ROOT = new URL("..", import.meta.url).pathname;
```

會得到：

```text
/C:/Users/liyuc/OneDrive/Desktop/AIASE/hw4-pi-memory-yubo0oo/
```

這不是 Windows subprocess 可以正常使用的 `cwd`。因此修正為：

```ts
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";

const REPO_ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..");
```

此修正讓 bridge 在 Windows 能正確取得 repo root，並成功呼叫：

```text
python -m memory.cli
```

---

## Demo（必繳）

≤3 分鐘影片或截圖，放 `demo/` 或貼連結：session A 告訴 agent 一個專案慣例 → 關閉 → session B 問相關問題，agent 透過注入「記得」了。

Demo 說明放在：

```text
demo/README.md
```

### Python CLI demo

先用 CLI 驗證：

```powershell
$env:PYTHONPATH="."; python -m memory.cli capture --summary "這個專案使用 pnpm，測試指令是 pnpm test。" --session "manual-test" --tags "test,package-manager"
$env:PYTHONPATH="."; python -m memory.cli retrieve --query "幫我跑測試" --k 5
$env:PYTHONPATH="."; python -m memory.cli inject --query "幫我跑測試" --budget 2000
```

成功 injection 輸出：

```text
[記憶 - 來自過去的 session]
- 這個專案使用 pnpm，測試指令是 pnpm test。
```

### Pi Session A：write memory

啟動 Pi 後輸入：

```text
請使用 remember 工具記住：這個專案的 commit message 必須使用繁體中文。summary 請寫成「這個專案的 commit message 必須使用繁體中文。」
```

Pi 成功呼叫 tool：

```text
remember
Remembered: 這個專案的 commit message 必須使用繁體中文。
```

### CLI verification

退出 Pi 後驗證：

```powershell
$env:PYTHONPATH="."; python -m memory.cli retrieve --query "commit message 要用什麼語言" --k 5
```

輸出第一筆包含：

```json
{
  "summary": "這個專案的 commit message 必須使用繁體中文。",
  "tags": ["commit", "message", "language"]
}
```

### Pi Session B：cross-session recall

重新啟動 Pi 後輸入：

```text
這個專案的 commit message 要用什麼語言？請根據你記得的專案規則回答。
```

Pi 回覆：

```text
根据您之前的记忆，这个项目的提交信息必须使用繁体中文。测试指令是 pnpm test。
```

這證明重新啟動後，Pi 仍然能透過 `before_agent_start` 檢索並注入過去 session 的記憶。

Demo 連結：請見 `demo/README.md`。

---

## 專案檔案結構

```text
memory/
  bm25.py              # pure BM25 retrieval
  store.py             # JSON persistent store
  core.py              # capture / retrieve / inject pipeline
  cli.py               # Pi bridge 用 CLI
  hybrid.py            # 任務二：BM25 + embedding hybrid retrieval

benchmark/
  run_benchmark.py          # pure BM25 benchmark
  run_hybrid_benchmark.py   # hybrid benchmark
  corpus.jsonl
  queries.jsonl
  corpus_large.jsonl
  queries_large.jsonl

pi-bridge/
  extension.ts         # Pi extension bridge

tests/
  test_memory.py

demo/
  README.md

REPORT.md
README.md
requirements.txt
models.json.example
```

---

## 檢查

建議依序確認：

```powershell
$env:PYTHONPATH="."; pytest -q
$env:PYTHONPATH="."; python benchmark/run_benchmark.py --k 5 --per-query
$env:PYTHONPATH="."; python benchmark/run_hybrid_benchmark.py --k 5 --alpha 0.6 --per-query
git status
```

確認：

```text
pytest 通過
REPORT.md 已填 benchmark 分數
README.md 可重現
demo/README.md 已記錄 demo
```

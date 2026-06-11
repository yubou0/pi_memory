# Local Agent Memory System

一個為本地端程式開發代理（Coding Agent）打造的輕量級持久化記憶系統。

本專案讓本地 AI 程式代理具備跨工作階段保存與回憶專案知識的能力。代理可以擷取重要的專案規範、將資訊儲存至本地 JSON 記憶庫，並在後續互動中檢索相關記憶，於回應前自動注入模型上下文，提升長期協作能力。

## 專案特色

* 支援跨工作階段的持久化記憶
* 採用 JSON 作為本地記憶儲存格式
* 使用可重現、可測試的 BM25 檢索機制
* 結合 sentence-transformers 的混合式檢索（Hybrid Retrieval）
* 透過 TypeScript Extension 與 Pi Coding Agent 整合
* 支援 Ollama 與 `qwen2.5:7b` 本地模型
* 內建單元測試與檢索效能評估工具

## 問題背景

多數本地端 Coding Agent 在工作階段結束後會遺失上下文資訊。

例如使用者曾告訴代理：

```text
This project uses pnpm, and the test command is pnpm test.
```

當代理重新啟動後，這項資訊通常無法被保留。

本專案透過建立記憶循環（Memory Loop）解決此問題：

```text
Capture → Store → Retrieve → Inject
```

代理可以保存專案層級的重要知識，並在後續對話中根據使用者需求檢索相關記憶，再將結果注入模型上下文後產生回應。

## 系統架構

```text
User message
    ↓
Pi coding agent
    ↓
remember tool / before_agent_start hook
    ↓
pi-bridge/extension.ts
    ↓
python -m memory.cli
    ↓
memory/core.py
    ↓
JsonStore + BM25 / Hybrid retrieval
    ↓
Injected memory context
    ↓
Local LLM response
```

## 核心元件

### `memory/store.py`

負責本地 JSON 記憶儲存。

主要職責：

* 從磁碟載入記憶資料
* 將記憶持久化至 JSON
* 依據 ID 去除重複記憶
* 維持儲存層的簡潔與可預測性

每筆記憶資料格式如下：

```json
{
  "id": "sha256 hash",
  "summary": "This project uses pnpm, and the test command is pnpm test.",
  "tags": ["test", "package-manager"]
}
```

### `memory/bm25.py`

實作可重現的 BM25 檢索演算法。

選擇 BM25 作為核心檢索方式的原因：

* 結果具備決定性（Deterministic）
* 容易撰寫測試
* 適合小型本地記憶庫
* 方便進行自動化評估

純 BM25 檢索流程與混合式檢索流程彼此獨立。

### `memory/hybrid.py`

實作混合式檢索機制：

```text
hybrid_score = alpha * normalized_bm25_score + (1 - alpha) * normalized_embedding_score
```

目前設定：

```text
alpha = 0.6
```

代表：

* 60% BM25 關鍵字匹配分數
* 40% Embedding 語意相似度分數

使用的 Embedding 模型：

```text
sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
```

此設計可改善純 BM25 在語意查詢與跨語言查詢上的限制。

### `memory/cli.py`

提供命令列介面（CLI），供 Pi Bridge 呼叫。

支援指令：

```bash
python -m memory.cli capture --summary "..."
python -m memory.cli retrieve --query "..." --k 5
python -m memory.cli inject --query "..." --budget 2000
```

### `pi-bridge/extension.ts`

負責將 Pi Coding Agent 與 Python 記憶系統串接。

提供功能：

* `remember` 工具：儲存長期記憶
* `before_agent_start` Hook：在代理回應前檢索並注入相關記憶

在 Windows 環境下，透過 `fileURLToPath` 與 `path.resolve` 將 `import.meta.url` 正確轉換為檔案系統路徑。

## Demo

以下展示跨工作階段記憶功能的完整流程。

### Session A：儲存記憶

使用者要求代理記住專案規範：

```text
Remember that this project's commit messages must be written in Traditional Chinese.
```

Pi Agent 呼叫 `remember` 工具：

```text
remember
Remembered: 這個專案的 commit message 必須使用繁體中文。
```

### 驗證：檢索記憶

記憶儲存後，可透過 CLI 查詢：

```powershell
python -m memory.cli retrieve --query "commit message 要用什麼語言" --k 5
```

檢索結果包含：

```text
這個專案的 commit message 必須使用繁體中文。
```

### Session B：重新啟動後回憶

重新啟動 Pi 後，使用者詢問：

```text
這個專案的 commit message 要用什麼語言？
```

代理根據注入的記憶回答：

```text
這個項目的提交信息必須使用繁體中文。
```

Demo 截圖位於：

```text
demo/
```

## Screenshots

### Session A：Remember Tool

![Session A remember tool](demo/session-a-remember.png)

### CLI Retrieval

![CLI retrieve memory](demo/cli-retrieve.png)

### Session B：Cross-session Recall

![Session B cross-session recall](demo/session-b-recall.png)

## Benchmark Results

檢索評估用於驗證系統是否能正確找回相關記憶。

評估指標：

* `Recall@5`：正確記憶是否出現在前五名結果中
* `MRR`：第一個正確結果的平均排名倒數
* `nDCG@5`：前五名結果的排序品質

### 純 BM25

| Dataset      | Recall@5 | MRR   | nDCG@5 |
| ------------ | -------- | ----- | ------ |
| Small corpus | 0.810    | 0.810 | 0.802  |
| Large corpus | 0.838    | 0.826 | 0.795  |

### Hybrid Retrieval

| Dataset      | Recall@5 | MRR   | nDCG@5 |
| ------------ | -------- | ----- | ------ |
| Small corpus | 0.905    | 0.881 | 0.887  |
| Large corpus | 0.900    | 0.887 | 0.864  |

結果顯示，混合式檢索透過結合關鍵字匹配與語意相似度，可有效提升檢索品質。

## 技術棧

* Python 3.13
* TypeScript
* Pi Coding Agent
* Ollama
* `qwen2.5:7b`
* `sentence-transformers`
* BM25
* JSON 本地儲存
* pytest

## 本地模型設定

本專案測試環境：

```text
Pi: 0.79.0
Ollama: 0.30.7
Model: qwen2.5:7b
Backend: Ollama OpenAI-compatible endpoint
Base URL: http://localhost:11434/v1
Context size: 128k auto
```

Pi 模型設定範例：

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

Windows 預設設定檔位置：

```text
C:\Users\<username>\.pi\agent\models.json
```

## 安裝方式

建立虛擬環境：

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

安裝相依套件：

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

執行測試：

```powershell
$env:PYTHONPATH="."; pytest -q
```

預期結果：

```text
13 passed
```

## 執行 Benchmark

### 純 BM25

```powershell
$env:PYTHONPATH="."; python benchmark/run_benchmark.py --k 5 --per-query
```

大型資料集：

```powershell
$env:PYTHONPATH="."; python benchmark/run_benchmark.py --corpus corpus_large.jsonl --queries queries_large.jsonl --k 5 --per-query
```

### Hybrid Retrieval

```powershell
$env:PYTHONPATH="."; python benchmark/run_hybrid_benchmark.py --k 5 --alpha 0.6 --per-query
```

大型資料集：

```powershell
$env:PYTHONPATH="."; python benchmark/run_hybrid_benchmark.py --corpus corpus_large.jsonl --queries queries_large.jsonl --k 5 --alpha 0.6 --per-query
```

## 與 Pi 整合執行

設定環境變數：

```powershell
$env:PYTHON="python"
$env:PYTHONPATH="."
$env:PI_MEMORY_PATH="$env:USERPROFILE\.pi-memory.json"
$env:PYTHONIOENCODING="utf-8"
$env:PYTHONUTF8="1"
```

若 Ollama 模型儲存在非 C 槽：

```powershell
$env:OLLAMA_MODELS="D:\liyuc\OllamaModels"
```

啟動 Pi 並載入記憶橋接模組：

```powershell
pi -e ./pi-bridge/extension.ts
```

## 專案結構

```text
memory/
  bm25.py              # BM25 檢索
  store.py             # JSON 記憶儲存
  core.py              # Capture / Retrieve / Inject 流程
  cli.py               # CLI 介面
  hybrid.py            # BM25 + Embedding 混合檢索

benchmark/
  run_benchmark.py          # BM25 Benchmark
  run_hybrid_benchmark.py   # Hybrid Benchmark
  corpus.jsonl
  queries.jsonl
  corpus_large.jsonl
  queries_large.jsonl

pi-bridge/
  extension.ts         # Pi Extension Bridge

demo/
  README.md
  session-a-remember.png
  cli-retrieve.png
  session-b-recall.png

tests/
  test_memory.py
```

## 設計說明

核心檢索流程維持決定性：

```text
memory.core.retrieve()
→ memory.bm25.bm25_search()
```

混合式檢索則獨立實作：

```text
memory.hybrid.hybrid_search()
```

此設計讓核心功能保持穩定與可測試性，同時保留語意檢索的擴充空間。

## 專案收穫

透過本專案，我實作並驗證了以下能力：

* 建立本地 AI Agent 的持久化記憶機制
* 將決定性檢索與機率式 LLM 行為分離
* 從零實作 BM25 檢索演算法
* 使用 Recall、MRR 與 nDCG 評估檢索品質
* 整合 Python 工具鏈與 TypeScript Agent Bridge
* 解決 Windows 環境下的路徑與編碼問題
* 建立可重現、可測試的 Agent Memory Pipeline

# ESG 新聞趨勢分析系統

此專案是一個自動化的 ESG（環境、社會、治理）新聞分析系統，用於從 ESG 新聞網站抓取最新標題，分析當前趨勢，並生成結構化的分析報告。

## 功能概述

- 自動從 [ESG News](https://esgnews.com/) 網站抓取最新新聞標題
- 提取並清理新聞標題
- 分析 ESG 趨勢（環境、社會、治理）
- 評估分析結果並提供反思
- 生成包含多角度影響分析的 Markdown 格式報告
- 自動保存報告到輸出目錄

## 系統架構

該系統使用 AutoGen 建立multi-agents架構，包括以下agents：

1. **多代理協作系統**：使用 AutoGen 框架實現的多代理協作系統，包含以下角色：
   - `web_scraper_agent`：抓取 ESG 新聞網站的原始文本
   - `title_extractor_agent`：從原始文本中提取新聞標題
   - `analyst_agent`：分析標題反映的 ESG 趨勢
   - `reflection_agent`：評估分析質量（RAG 增強）
   - `correction_agent`：在發現問題時協調修正
   - `draft_agent`：整合內容並撰寫報告草稿
   - `document_agent`：格式化並保存最終報告

2. **SimpleRAG 系統**：使用簡單關鍵詞匹配實現的檢索增強生成系統，包含：
   - 文檔加載和處理機制
   - 基於關鍵詞匹配的相似度計算
   - 文本塊檢索引擎

## 環境設置

### 前提條件

- Python 3.10 或更高版本
- Azure OpenAI API 密鑰
- Node.js (用於 MCP 服務器)
- 相關 Python 和 Node.js 套件

### 安裝步驟

1. **安裝依賴**：
    **安裝必要的 python 套件**：
   ```bash
   pip install "autogen-ext[openai,mcp]" autogen-agentchat
   pip install mcp-server-fetch
   pip install python-dotenv
   ```

    **安裝必要的 Node.js 套件**：

   ```bash
   npm install -g @modelcontextprotocol/server-filesystem
   ```

2. **環境變量設置**：

在 PowerShell 中設置 API 密鑰（Windows）：
```powershell
$env:AZURE_API_KEY="你的API金鑰"
```

3. **目錄結構設置**：

```
project/
│
├── manual_for_RAG/              # RAG 手冊目錄
│   └── ESG_Reflection_Agent_Guide.md  # 反思指南
│
├── output/                      # 輸出報告目錄
│
├── simple_rag.py                # 簡單RAG實現
├── esg_news_analyzer.py         # 主程序
├── run_esg_analyzer.py          # 啟動腳本
└── README.md                    # 本文檔
```

## 使用方法

1. 確保 `ESG_Reflection_Agent_Guide.md` 文件已放入 `manual_for_RAG` 目錄

2. 設置  API 密鑰：
   ```powershell
   $env:AZURE_API_KEY="你的API金鑰"
   $env:OPENAI_API_KEY="你的OpenAI API金鑰
   ```

3. 運行啟動腳本：
   ```bash
   python esg_analyzer.py
   ```

4. 查看 `output` 目錄中生成的報告

## SimpleRAG 系統詳解

本項目實現了一個簡單的基於關鍵詞匹配的 RAG 系統，用於增強 `reflection_agent` 的能力：

### 文檔處理

- 直接加載 Markdown 文件
- 使用基於章節和段落的自然分界點進行文本分塊
- 保留文檔結構和章節信息

### 檢索機制

- 使用基本的關鍵詞匹配計算相似度
- 將查詢和文本轉換為詞集合，計算詞集合的交集大小
- 基於相似度排序檢索最相關的文本塊

### 查詢處理

- 將 `reflection_agent` 的需求轉化為查詢
- 預先查詢關鍵評估內容，嵌入到系統提示中
- 支持根據不同查詢動態檢索內容

## 技術細節

- **相似度計算**：基於關鍵詞匹配的相似度計算
- **分塊策略**：基於自然段落和章節的分塊，最大500字符/塊
- **檢索方法**：top-k 關鍵詞相似度檢索

## 維護和擴展

- 若要更新評估指南，只需修改 `manual_for_RAG` 目錄中的文件
- 若要調整檢索性能，可修改 `simple_rag.py` 中的相似度計算和分塊策略
- 若要擴展到其他代理，可複製類似的 RAG 實現模式 
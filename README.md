# ESG 新聞趨勢分析系統

此專案是一個自動化的 ESG（環境、社會、治理）新聞分析系統，使用 AutoGen 多代理協作框架，從 ESG 新聞網站抓取最新標題，分析當前趨勢，並生成結構化的分析報告。

## 功能概述

- 🌐 自動從 [ESG News](https://esgnews.com/) 網站抓取最新新聞標題
- 🔍 智能提取並清理新聞標題（目標 10 條）
- 📊 深度分析 ESG 趨勢（環境、社會、治理分類）
- 🎯 識別核心主題和關鍵焦點
- 💡 提供多角度影響分析（對企業、投資者、社會、監管機構等）
- 📝 生成包含完整分析的 Markdown 格式報告
- 💾 自動保存報告到輸出目錄，檔名包含時間戳

## 系統架構

該系統使用 AutoGen 框架建立多代理協作系統，包括以下 7 個專業 agents：

1. **`web_scraper_agent`** - 網頁抓取專家：從 ESG News 網站抓取原始文本內容
2. **`title_extractor_agent`** - 標題提取專家：從原始文本中精確提取 10 條新聞標題
3. **`analyst_agent`** - ESG 趨勢分析專家：進行深入的 ESG 趨勢分析和分類
4. **`reflection_agent`** - 品質評估專家：評估分析品質並提供影響分析洞見
5. **`correction_agent`** - 品質控制協調員：在發現問題時協調修正過程
6. **`draft_agent`** - 報告撰寫專家：整合所有內容並撰寫完整報告草稿
7. **`document_agent`** - 文檔發布專員：格式化並保存最終報告

## 環境設置

### 前提條件

- **Python 3.10 或更高版本**
- **Node.js 16 或更高版本**（用於 MCP 服務器）
- **OpenAI API 金鑰** 或 **Azure OpenAI API 金鑰**
- **MCP fetch 服務器**（需要單獨設置）
- **AutoGen v0.4 或更高版本**

### 詳細安裝步驟

#### 1. 安裝 Python 依賴

```bash
# 安裝核心 AutoGen 套件
pip install "autogen-ext[openai,mcp]"
pip install autogen-agentchat
pip install mcp-server-fetch

# 如果上述安裝有問題，可以分別安裝：
# pip install autogen-ext
# pip install autogen-agentchat
# pip install openai
# pip install mcp-server-fetch
```

#### 2. 安裝 Node.js 依賴

```bash
# 安裝 MCP 文件系統服務器（全域安裝，推薦）
npm install -g @modelcontextprotocol/server-filesystem

# 或者使用 npx（程式會自動處理，但首次運行較慢）
# npx @modelcontextprotocol/server-filesystem
```

#### 3. 設置 MCP Fetch 服務器

**重要**：程式碼中使用了自定義的 MCP fetch 服務器，您需要：

1. **選項 A：修改程式碼路徑**（推薦）
   
   在 `esg_news_analyzer.py` 第 25 行，將路徑修改為您的實際路徑：
   ```python
   # 將此路徑修改為您的 fetch-mcp 服務器路徑
   args=["您的路徑/fetch-mcp/dist/index.js"]
   ```

2. **選項 B：設置 fetch-mcp 服務器**
   
   如果您沒有 fetch-mcp 服務器，可以：
   - 從相關 GitHub 倉庫下載並設置
   - 或聯繫開發者獲取設置指引

#### 4. 設置 API 金鑰

在 PowerShell 中設置環境變數：

```powershell
# 使用 OpenAI API（推薦，程式預設啟用）
$env:OPENAI_API_KEY="您的OpenAI API金鑰"

# 或使用 Azure OpenAI API（需要修改程式碼）
$env:AZURE_API_KEY="您的Azure API金鑰"
```

**注意**：如要使用 Azure OpenAI API，需要在程式碼中：
1. 註釋掉 OpenAI API 相關程式碼（第 42-52 行）
2. 取消註釋 Azure OpenAI API 程式碼（第 54-72 行）
3. 修改 `azure_endpoint` 為您的實際端點

#### ⚠️ **Azure OpenAI 重要限制警告**

如果您選擇使用 Azure OpenAI API，請特別注意以下限制：

**🚨 Token 速率限制（Rate Limits）**：
- **Standard S0 定價層**（預設）有嚴格的 token 使用限制
- **每分鐘 token 限制**：通常為 20,000-40,000 tokens/分鐘（依模型而異）
- **每小時 token 限制**：可能有額外的小時限制
- **併發請求限制**：同時進行的 API 請求數量有限制

**💡 本系統的 Token 使用特性**：
- 此系統使用 **7 個 AI agents** 進行多輪對話
- 在 **2-5 分鐘內** 會有密集的 API 調用

**⚠️ 可能遇到的問題**：
- `RateLimitError`: 超出每分鐘 token 限制
- `QuotaExceededError`: 超出配額限制
- 執行中斷或延遲

**🔧 建議解決方案**：
1. **升級定價層**：考慮升級到更高的定價層（如 Standard S1, S2）
2. **使用 OpenAI API**：OpenAI API 通常有更寬鬆的限制
3. **監控使用量**：在 Azure Portal 中監控 token 使用情況
4. **分時執行**：避免在高峰時段執行

**📊 Azure OpenAI 定價層比較**：
- **Standard S0**: 20K tokens/min, 適合輕量使用
- **Standard S1**: 40K tokens/min, 適合中等使用
- **Standard S2**: 60K tokens/min, 適合重度使用

#### 5. 創建目錄結構

```bash
# 確保專案目錄結構正確
mkdir output  # 報告輸出目錄（程式會自動創建）
```

最終目錄結構：
```
esg_news_analyzer/
├── esg_news_analyzer.py     # 主程式
├── output/                  # 輸出報告目錄
└── README.md                # 本文檔
```

## 使用方法

### 快速開始

1. **確認環境變數已設置**：
   ```powershell
   # 檢查 API 金鑰是否已設置
   echo $env:OPENAI_API_KEY
   ```

2. **運行程式**：
   ```bash
   python esg_news_analyzer.py
   ```

3. **觀察執行過程**：
   - 系統會顯示各個 agent 的工作進度
   - 整個流程通常需要 2-5 分鐘完成
   - 最終會在 `output` 目錄生成報告

4. **查看結果**：
   - 報告檔名格式：`ESG_News_YYYY-MM-DD_HH-MM-SS.md`
   - 包含完整的標題列表、趨勢分析和影響評估

### 執行流程說明

程式執行時會按以下順序進行：

```
用戶啟動 → 網頁抓取 → 標題提取 → 趨勢分析 → 品質評估 → 
(可能的修正) → 報告撰寫 → 文檔保存 → 自動終止
```

每個步驟都有詳細的 console 輸出，您可以追蹤進度。

## 自定義配置

### 模型設置
- **主要模型**：GPT-4o（用於複雜分析任務）
- **選擇器模型**：GPT-4o-mini（用於流程控制）
- 可在程式碼中修改模型選擇

### 分析參數
- **標題數量**：預設提取 10 條新聞標題
- **分析深度**：包含 E、S、G 分類、核心主題識別、影響分析
- **報告結構**：固定的 Markdown 格式，包含多個分析維度

### 輸出設置
- **輸出路徑**：`output/` 目錄
- **檔名格式**：`ESG_News_YYYY-MM-DD_HH-MM-SS.md`
- **內容格式**：結構化的 Markdown 報告

## 故障排除

### 常見問題

1. **MCP 服務器連接失敗**
   - 檢查 Node.js 是否已安裝
   - 確認 MCP 套件已正確安裝
   - 檢查程式碼中的路徑設置

2. **API 金鑰錯誤**
   - 確認環境變數已正確設置
   - 檢查 API 金鑰是否有效
   - 確認 API 配額是否充足

3. **Azure OpenAI Rate Limit 錯誤**
   - 檢查您的定價層是否足夠（建議 S1 或以上）
   - 等待幾分鐘後重試
   - 考慮切換到 OpenAI API
   - 在 Azure Portal 檢查使用量和限制

4. **網頁抓取失敗**
   - 檢查網路連接
   - 確認目標網站是否可訪問
   - 檢查 fetch-mcp 服務器是否正常運行

5. **程式執行中斷**
   - 檢查 console 輸出中的錯誤訊息
   - 確認所有依賴項已正確安裝
   - 檢查系統資源是否充足

## 技術特色

- **多代理協作**：7 個專業 agent 分工合作
- **智能品質控制**：自動檢測和修正分析問題
- **結構化輸出**：標準化的報告格式
- **自動終止機制**：完成後自動停止，無需手動干預
- **錯誤恢復**：內建修正機制處理常見問題

## 注意事項

- 程式運行期間請勿中斷，讓系統自動完成整個流程
- 首次運行可能需要較長時間下載和設置 MCP 服務器
- 建議在穩定的網路環境下運行
- API 調用會產生費用，請注意使用量控制
- **Azure OpenAI 用戶**：請確保您的定價層足以支撐密集的 API 調用

## 版本資訊

- **AutoGen 版本**：**v0.4 或更高版本**
- **Python 版本**：3.10+
- **Node.js 版本**：16+
- **支援的 API**：OpenAI API、Azure OpenAI API
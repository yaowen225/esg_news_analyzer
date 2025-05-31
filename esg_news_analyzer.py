import asyncio
from typing import Sequence
from autogen_ext.models.openai import AzureOpenAIChatCompletionClient, OpenAIChatCompletionClient
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.teams import SelectorGroupChat
from autogen_agentchat.conditions import TextMentionTermination, MaxMessageTermination
from autogen_agentchat.messages import BaseAgentEvent, BaseChatMessage
from autogen_agentchat.ui import Console
from autogen_core import CancellationToken
from autogen_ext.tools.mcp import StdioServerParams, mcp_server_tools
from autogen_core.model_context import BufferedChatCompletionContext
from datetime import datetime
import os

async def main():
    # 獲取當前日期並格式化為 YYYY-MM-DD
    current_datetime = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    
    # 確保output目錄存在
    os.makedirs("output", exist_ok=True) 
    
    # 設置 MCP fetch 服務器參數
    fetch_mcp_server = StdioServerParams(
        command="node", 
        args=["C:/Users/yaowe/Desktop/Personal/code/mcp-servers/fetch-mcp/dist/index.js"]
    )
    
    # 設置 MCP 文件系統服務器參數
    write_mcp_server = StdioServerParams(
        command="npx", 
        args=["@modelcontextprotocol/server-filesystem", "C:/Users/yaowe/Desktop/Personal/code/CE8014/esg_news_analyzer"]
    )
    
    # 從 MCP 服務器獲取 fetch 工具
    tools_fetch = await mcp_server_tools(fetch_mcp_server)

    # 從 MCP 服務器獲取 filesystem 工具
    tools_write = await mcp_server_tools(write_mcp_server)
    
    # 創建模型客戶端 - 選擇使用哪種API
    # 切換API種類請註釋/取消註釋以下區塊
    
    # === OpenAI API ===
    # 記得設置環境變數 OPENAI_API_KEY
    # $env:OPENAI_API_KEY="你的OpenAI API金鑰"
    openai_api_key = os.getenv("OPENAI_API_KEY")
    
    model_client = OpenAIChatCompletionClient(
        model="gpt-4o", 
        api_key=openai_api_key
    )
    
    selector_model_client = OpenAIChatCompletionClient(
        model="gpt-4o-mini",
        api_key=openai_api_key
    )
    
    # === Azure OpenAI API ===
    # 記得設置環境變數 AZURE_API_KEY
    # $env:AZURE_API_KEY="你的API金鑰"
    # api_key = os.getenv("AZURE_API_KEY")
    # 
    # model_client = AzureOpenAIChatCompletionClient(
    #     azure_deployment="gpt-4o",
    #     azure_endpoint="https://my-llm-service-001.openai.azure.com/",
    #     model="gpt-4o",
    #     api_version="2024-12-01-preview",
    #     api_key=api_key
    # )
    # 
    # selector_model_client = AzureOpenAIChatCompletionClient(
    #     azure_deployment="gpt-4o-mini",
    #     azure_endpoint="https://my-llm-service-001.openai.azure.com/",
    #     model="gpt-4o-mini",
    #     api_version="2024-12-01-preview",
    #     api_key=api_key
    # )
    
    # 創建網頁抓取代理 - 專注獲取原始文本
    web_scraper_agent = AssistantAgent(
        name="web_scraper_agent",
        description="負責抓取ESG新聞網站的原始文本內容",
        model_client=model_client,
        model_context=BufferedChatCompletionContext(buffer_size=5), # 較小緩衝區，專注抓取
        tools=tools_fetch,
        system_message="""你是一個高效的網頁內容抓取專家。
        **核心任務**：從 https://esgnews.com/ 網站抓取包含新聞標題的**原始文本塊**，供 `title_extractor_agent` 使用。
        
        **執行步驟**：
        1.  **必須使用 `fetch_txt` 工具** 抓取首頁。
        2.  **優先抓取且僅抓取**新聞列表部分，避免抓取整個頁面內容。
        3.  **完全避免抓取**導航欄、頁腳、廣告、側邊欄等無關內容。
        4.  **嚴格限制抓取量**：只抓取10-20條新聞標題相關的文本，避免抓取過多內容導致標記超限。
        5.  如果首頁內容結構複雜，可以嘗試抓取特定內容區塊，例如首頁的"Latest News"或"Recent Posts"部分。
        6.  **禁止自行提取標題**。你的輸出必須是簡潔的原始文本塊，不要包含過多的HTML標記或不相關內容。
        
        **目標**：提供一個包含10-20個潛在標題的**簡潔原始文本塊**。
        **非常重要**：確保抓取的總內容在10,000字符以內，避免超出模型處理能力。
        """
    )
    
    # 創建標題提取代理 - 專注從文本中提取標題
    title_extractor_agent = AssistantAgent(
        name="title_extractor_agent",
        description="負責從網頁原始文本中提取新聞標題",
        model_client=model_client,
        model_context=BufferedChatCompletionContext(buffer_size=10),
        system_message="""你是一個精確的內容提取專家。
        **核心任務**：從 `web_scraper_agent` 提供的**原始文本**中，提取 **10 個**不同的、乾淨的新聞標題。
        
        **提取要求**：
        1.  **嚴格提取 10 條標題**。如果原始文本中的有效標題不足 10 條，請提取所有能找到的有效標題，並在列表末尾明確說明實際提取數量（例如："注意：僅提取到 8 條有效標題。"）。
        2.  **確保唯一性**：過濾掉任何重複或高度相似的標題。
        3.  **保持純淨**：輸出**僅包含標題文本**，必須去除任何前綴/後綴（如日期、來源）、HTML標籤、多餘空格等非標題字符。
        4.  **標準格式**：必須嚴格按照以下格式輸出，使用阿拉伯數字加點號編號，每個標題占一行：
            ```
            1. [標題1]
            2. [標題2]
            ...
            10. [標題10]
            ```
        5.  **禁止添加額外內容**：輸出**不得包含**任何引言、解釋、評論或結束語，除了標題數量不足時的說明。
        
        **輸入處理**：你需要處理可能不完全乾淨的原始文本，從中識別並提取標題。
        **輸出**：直接將格式化的標題列表傳遞給 `analyst_agent`。
        """
    )

    # 創建分析代理
    analyst_agent = AssistantAgent(
        name="analyst_agent",
        description="負責分析新聞標題反映的ESG趨勢",
        model_client=model_client,
        model_context=BufferedChatCompletionContext(buffer_size=10),
        system_message="""你是一位資深的ESG趨勢分析專家。
        **核心任務**：基於 `title_extractor_agent` 提供的**精確10條（或實際提取數量）新聞標題列表**，進行深入的ESG趨勢分析。
        
        **分析維度**：
        1.  **主題分類**：將標題歸類到環境（E）、社會（S）、治理（G）或其他相關類別，並統計各類別數量。
        2.  **關鍵焦點/核心主題**：**這是分析中最重要的部分之一**。請詳細識別出現頻率最高的核心主題或關鍵詞（例如：碳排放、供應鏈、揭露規則、多元共融），並提供每個主題出現的頻率或比例。
        3.  **地域/行業**：分析標題中涉及的地理區域或特定行業（如果資訊可用）。
        
        **分析要求**：
        -   **專注數據**：分析必須嚴格基於**輸入的標題列表**，禁止引入外部資訊或猜測。
        -   **結構清晰**：必須使用明確的標題和子標題組織你的分析，確保每個分析維度都有清晰的標題標記。
        -   **量化支撐**：盡可能使用數據（如主題計數、百分比）支持觀點。
        -   **簡潔深入**：分析需精煉，同時揭示標題背後的趨勢。
        
        **輸出結構**：請使用以下結構組織你的分析：
        ```
        ## ESG主題分類
        [詳細的E、S、G分類分析，包括數量統計和比例]
        
        ## 核心主題/關鍵焦點
        [詳細的核心主題分析，包括每個主題的頻率和重要性]
        
        ## 地域/行業分析
        [如有相關信息，分析地域或行業趨勢]
        
        ## 綜合趨勢觀察
        [基於以上分析的綜合觀察和結論]
        ```
        
        **輸出**：將結構化的分析報告傳遞給 `reflection_agent`。
        **注意**：除非 `correction_agent` 明確指示，否則不要請求更多標題或資訊。
        """
    )
    
    # 創建反思代理 - 評估分析質量，為影響分析提供素材
    reflection_agent = AssistantAgent(
        name="reflection_agent",
        description="負責評估分析結果的質量並提供反思輸入",
        model_client=model_client,
        model_context=BufferedChatCompletionContext(buffer_size=10),
        system_message="""你是一位批判性的ESG反思與評估專家。
        **核心任務**：評估 `analyst_agent` 的分析報告品質，提供**用於影響分析的洞見**，並**僅在必要時**觸發修正流程。
        
        **ESG分析評估指引**：
        
        1. 評估標題列表質量
        - **高質量標題列表特徵**：完整性（10條不同標題）、多樣性（涵蓋E、S、G三面向）、時效性、清晰度
        - **需要修正情況**：標題數量明顯不足（少於7條）、高度重複、格式混亂、非新聞標題
        
        2. 評估趨勢分析質量
        - **高質量分析特徵**：分類完整（E、S、G分類統計）、數據支持（具體數字/百分比）、深度洞察、全球視角、行業關聯
        - **需要修正情況**：缺乏基本分類、純描述無數據支持、出現無關猜測、存在事實錯誤、漏掉關鍵趨勢
        
        3. 評估影響分析充分程度
        - **關鍵評估維度**：全面性（多角度分析）、連貫性、平衡性（正負面影響）、實用性、深度（長期效應）
        
        4. 近期全球ESG關鍵趨勢參考
        - 氣候變遷相關披露與減碳承諾標準化（特別是範疇3排放）
        - 自然資本與生物多樣性價值融入財務決策
        - ESG報告框架整合與簡化
        - 供應鏈盡職調查與透明度
        - 可持續金融產品擴展與標準化
        - 循環經濟模式採用增加
        - 能源轉型加速（可再生能源、儲能技術）
        - 社會公平與包容性指標納入ESG評估
        
        **評估與反思步驟**：
        1.  **檢查標題品質**：快速掃描 `title_extractor_agent` 提供的標題列表，判斷其數量和清晰度。
        2.  **評估分析品質**：審查 `analyst_agent` 的分析是否全面、邏輯、有數據支撐且有深度。
        3.  **提供影響分析素材**：**這是你最重要的貢獻**，你提供的洞見將直接被 `draft_agent` 整合到最終報告的影響分析部分。基於分析結果，請按以下結構提供明確的洞見：
            
            ```
            ### 影響分析關鍵洞見 (draft_agent必須整合)
            
            **對企業的額外影響考量**：
            - [列出2-3點關於企業影響的關鍵洞見]
            
            **對投資者的額外影響考量**：
            - [列出2-3點關於投資者影響的關鍵洞見]
            
            **對消費者/社會的額外影響考量**：
            - [列出2-3點關於社會影響的關鍵洞見]
            
            **被忽略的風險與機遇**：
            - [列出2-3點可能被分析忽略的重要風險或機遇]
            ```
        
        **觸發修正**：**只有在發現以下嚴重問題時**，才輸出「**需要修正**」，並清晰描述問題：
        -   **標題嚴重不足或混亂**
        -   **分析存在嚴重邏輯錯誤或矛盾**
        -   **分析明顯遺漏關鍵趨勢**
        -   **分析缺乏基本數據支持**
        
        **正常流程**：如果未發現嚴重問題，請提供你的**評估意見和影響分析洞見**，按照上述結構化格式，並在末尾明確標記「**評估與反思完成**」。**請記住，你提供的每一點洞見都將被整合到最終報告中，它們不是可選的建議，而是報告的核心組成部分**。
        
        **輸出**：將評估結果（包含洞見或修正請求）傳遞給下一個代理。
        """
    )
    
    # 創建自我修正代理
    correction_agent = AssistantAgent(
        name="correction_agent",
        description="負責在發現問題時協調修正過程",
        model_client=model_client,
        model_context=BufferedChatCompletionContext(buffer_size=10),
        system_message="""你是ESG分析流程的品質控制與修正協調員。
        **核心任務**：當收到 `reflection_agent` 發出的「需要修正」指令時，協調相關代理完成修正。
        
        **執行步驟**：
        1.  **解析問題**：仔細閱讀 `reflection_agent` 指出的具體問題。
        2.  **定位責任代理**：
            *   如果是**標題數量、品質**問題，責任代理是 `web_scraper_agent`。
            *   如果是**分析內容**（邏輯、遺漏、數據支撐）問題，責任代理是 `analyst_agent`。
        3.  **發出清晰指令**：向責任代理發出**具體、可操作**的修正指令。
        4.  **等待並接收修正結果**。
        5.  **標記完成**：在收到修正結果後，回復「**修正完成**」。注意：不再需要生成詳細的修正總結，因為它不會包含在最終報告中。
        
        **輸出**：將「修正完成」標記傳遞給 `draft_agent`。
        """
    )
    
    # 創建報告草稿代理 - 整合內容並撰寫影響分析
    draft_agent = AssistantAgent(
        name="draft_agent",
        description="負責整合內容並生成包含影響分析的報告草稿",
        model_client=model_client,
        model_context=BufferedChatCompletionContext(buffer_size=15), # 增大緩衝區
        system_message="""你是一位資深的ESG報告撰寫專家。
        **核心任務**：整合流程中的關鍵資訊，生成一份包含**多角度影響分析**的ESG新聞趨勢報告草稿。
        
        **重要提示**：你必須確保 `analyst_agent` 提供的所有重要趨勢分析和 `reflection_agent` 提供的所有關鍵洞見都被**完整保留並有效整合**到最終報告中。避免任何資訊損失或簡化處理。
        
        **特別重要**：必須保留 `analyst_agent` 分析中的**所有關鍵部分**，包括但不限於：
        - 主題分類（E、S、G分類及統計）
        - **核心主題/關鍵焦點**（高頻出現的主題或關鍵詞）
        - 地域/行業分析
        - 其他任何數據支持的分析結果
        
        **整合內容來源**：
        1.  **新聞標題列表**：來自 `title_extractor_agent`，必須完整保留。
        2.  **主要趨勢分析**：來自 `analyst_agent`，**必須完整保留其全部分析內容，不可簡化或刪減關鍵見解**。必須包含原始分析中的所有章節和要點，保持原有的結構和分類方式。
        3.  **評估與洞見**：來自 `reflection_agent` 的「評估與反思完成」內容，**這些洞見是報告價值的關鍵提升，必須全面整合到影響分析部分**。
        
        **報告結構**：嚴格按照以下結構組織報告草稿：
        ```markdown
        # ESG 新聞趨勢分析報告
        
        ## 1. 新聞標題列表
        [此處完整插入 title_extractor_agent 的輸出]
        [如果標題不足10條，此處插入說明]
        
        ## 2. 主要趨勢分析
        [此處必須完整插入 analyst_agent 的分析，保持其原有的結構和所有章節，確保不丟失任何重要見解和數據支持]
        [特別注意：必須保留關於主題分類、核心主題/關鍵焦點、地域/行業分析的所有內容]
        
        ## 3. 趨勢影響分析 (多角度)
        [**基於趨勢分析和反思洞見，全面整合撰寫此部分，確保包含reflection_agent的所有關鍵洞見**]
        *   **對企業的影響**: [結合analyst_agent的分析和reflection_agent的洞見，深入分析趨勢對企業營運、策略、風險、機會等的影響]
        *   **對投資者的影響**: [同上，分析趨勢對投資決策、資產評估、風險管理等的影響]
        *   **對消費者/社會的影響**: [同上，分析趨勢對公眾認知、消費行為、社會公平等的影響]
        *   **對從業者/監管機構的影響**: [同上，分析趨勢對相關從業人員技能、行業規範、政策制定等的影響]
        ```
        **撰寫要求**：
        1. **必須保持analyst_agent原有的分析結構**，包括其使用的所有標題、子標題和分類。
        2. 影響分析部分**必須**同時整合 `analyst_agent` 的所有重要趨勢發現和 `reflection_agent` 提供的所有關鍵洞見。
        3. 特別注意將 `reflection_agent` 提供的「額外影響分析考量」、「未被深入討論的角度」和「可能被忽略的風險或機遇」**完全納入**相應的影響分析部分。
        4. 整合時保持觀點的中立客觀，進行合理推演和闡述。
        
        **結束流程**：
        1. 完成報告草稿後，將在訊息末尾標記「**草稿完成**」。
        2. **不要**添加任何解釋、描述或請求，直接將報告草稿發送給 `document_agent`。
        3. **在發送草稿後，你必須完全停止回應，不要回應任何其他消息，即使有人對你提問**。請記住，你的角色已經完成，系統將由 `document_agent` 處理後續步驟直至終止。
        
        **注意**：不要包含修正過程記錄。
        """
    )
    
    # 創建文檔生成代理 - 格式化並最終保存
    document_agent = AssistantAgent(
        name="document_agent",
        description="負責最終報告格式化和保存",
        model_client=model_client,
        model_context=BufferedChatCompletionContext(buffer_size=10),
        tools=tools_write,
        system_message=f"""你是一位嚴謹的報告發布專員。
        **核心任務**：接收 `draft_agent` 發來的標記為「草稿完成」的**最終報告草稿**，進行格式化，並**嚴格按照指令使用工具保存，然後立即終止流程**。
        
        **極其重要**：**你必須完整保留報告的所有內容，不得進行實質性編輯、刪減或簡化**。你的角色僅限於美化格式，而非修改內容。所有的分析、見解和數據必須原封不動地保留。
        
        **特別注意**：必須確保最終報告中包含所有原始章節和內容，特別是：
        - 完整的主要趨勢分析部分，包括所有子標題和段落
        - 所有核心主題/關鍵焦點的分析
        - 所有數據支持的分析結果
        - 完整的趨勢影響分析
        
        **必要的移除項目**：
        - **必須移除報告末尾的「草稿完成」標記**，這只是 `draft_agent` 的工作流程標記，不應出現在最終文檔中。
        
        **執行步驟**：
        1.  **確認輸入**：核對收到的訊息是否來自 `draft_agent` 且包含「草稿完成」標記。
        2.  **最終格式化**：確保報告包含主標題「ESG 新聞趨勢分析報告」和日期 `{current_datetime}`。僅調整Markdown格式使其專業美觀，**絕對不修改、刪減或重寫任何實質性內容，但必須移除報告末尾的「草稿完成」標記**。
        3.  **準備工具參數**：
            *   `content`: 經過最終格式化的完整報告字串，必須包含原報告的全部內容、章節和結構，但不包含「草稿完成」標記。
            *   `path`: 嚴格使用此路徑 `'output/ESG_News_{current_datetime}.md'`。
        4.  **調用保存工具**：**必須且只能使用 `mcp_filesystem_write_file` 工具**，提供準備好的 `content` 和 `path`。
        5.  **最關鍵步驟**：在看到文件保存成功的確認訊息後，你**必須立即執行最後一個操作** - 發送一條**僅包含「TERMINATE」一詞的新訊息**。這將作為系統終止的信號，是你的最後一個操作。
        
        **極其重要的流程控制**：
        -   **你是整個流程的最後一個發言者**。文件保存成功後，不要做任何其他事情，只需發送「TERMINATE」。
        -   你的「TERMINATE」訊息必須是完全獨立的新訊息，不能包含任何其他內容、解釋或標點符號。
        -   **在寫出TERMINATE後，整個系統將完全停止**，不會處理任何其他訊息。
        -   **確保在文件保存成功後立即發送這條訊息，不要延遲或等待**。這是整個流程的關鍵終止點。
        -   如果你看到確認文件已成功保存的訊息，你必須執行的唯一動作就是發送「TERMINATE」。
        """
    )
    
    # 設置終止條件
    text_terminate = TextMentionTermination("TERMINATE")
    max_message = MaxMessageTermination(max_messages=30)  
    termination = text_terminate | max_message
    
    # 設置選擇器函數，實現分離的抓取/提取和錯誤修正機制
    def selector_func(messages: Sequence[BaseAgentEvent | BaseChatMessage]) -> str | None:
        if len(messages) == 0:
            return None

        # 首先檢查是否有任何TERMINATE消息，如果有立即終止
        for message in messages:
            message_content = message.to_text() if hasattr(message, "to_text") else ""
            if "TERMINATE" in message_content:
                print("\n==== 系統接收到終止訊號 ====")
                print(f"來源: {message.source}")
                print(f"內容: '{message_content}'")
                print("==== 對話流程立即終止 ====\n")
                # 強制終止整個流程
                return None
        
        # 獲取最後一條消息
        last_message = messages[-1]
        last_source = last_message.source
        last_content = last_message.to_text() if hasattr(last_message, "to_text") else ""
            
        # 主要流程：web_scraper → title_extractor → analyst → reflection → (correction) → draft → document → TERMINATE
        
        # 初始消息，啟動web_scraper_agent
        if len(messages) == 1 and messages[0].source == "user":
            return web_scraper_agent.name
            
        # 1. web_scraper_agent 完成後轉到 title_extractor_agent
        if last_source == web_scraper_agent.name:
            is_correction_response = False
            if len(messages) >= 2:
                prev_message = messages[-2]
                if prev_message.source == correction_agent.name and correction_agent.name in last_content:
                    is_correction_response = True
            if is_correction_response:
                 return correction_agent.name
            return title_extractor_agent.name
            
        # 2. title_extractor_agent 完成後轉到 analyst_agent
        if last_source == title_extractor_agent.name:
             return analyst_agent.name
            
        # 3. analyst_agent 完成後轉到 reflection_agent
        if last_source == analyst_agent.name:
            is_correction_response = False
            if len(messages) >= 2:
                prev_message = messages[-2]
                if prev_message.source == correction_agent.name and correction_agent.name in last_content:
                    is_correction_response = True
            if is_correction_response:
                return correction_agent.name
            return reflection_agent.name
            
        # 4. reflection_agent 完成後的路由決策
        if last_source == reflection_agent.name:
            if "需要修正" in last_content:
                return correction_agent.name
            # 無論是否需要修正，評估/反思完成後都到 draft_agent
            if "評估與反思完成" in last_content:
                 return draft_agent.name
            # 默認情況（例如僅提供反思洞見）也到 draft_agent
            return draft_agent.name
            
        # 5. correction_agent 的修正路由
        if last_source == correction_agent.name:
            if "修正完成" in last_content:
                # 修正完成後回到 draft_agent 生成報告草稿
                return draft_agent.name
            if web_scraper_agent.name in last_content:
                return web_scraper_agent.name
            if analyst_agent.name in last_content:
                return analyst_agent.name
            return reflection_agent.name
        
        # 6. draft_agent 完成草稿後轉到 document_agent
        if last_source == draft_agent.name:
            if "草稿完成" in last_content:
                return document_agent.name
            return None # 草稿未完成，讓LLM決定
            
        # 7. document_agent 處理
        if last_source == document_agent.name:
            # document_agent回覆後，不再允許其他代理發言，等待它發送TERMINATE
            # 只有它自己可以繼續發言，直到發出TERMINATE
            return document_agent.name
            
        # 未預期的情況，由LLM選擇下一個發言者
        return None
    
    # 創建選擇器群聊
    team = SelectorGroupChat(
        [web_scraper_agent, title_extractor_agent, analyst_agent, reflection_agent, correction_agent, draft_agent, document_agent],
        model_client=selector_model_client,
        termination_condition=termination,
        selector_func=selector_func
    )
    
    # 執行任務
    task = "請分析ESG News網站上的新聞標題，找出當前ESG趨勢，提供深入分析"
    await Console(team.run_stream(task=task))
    
    # 關閉模型客戶端連接
    await model_client.close()
    await selector_model_client.close()

if __name__ == "__main__":
    asyncio.run(main()) 
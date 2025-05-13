import asyncio
from typing import Sequence
from autogen_ext.models.openai import AzureOpenAIChatCompletionClient
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
# 導入簡單 RAG 系統
from simple_rag import SimpleRAG

async def main():
    # 獲取當前日期並格式化為 YYYY-MM-DD
    current_datetime = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    
    # 確保output目錄存在
    os.makedirs("output", exist_ok=True) 
    
    # 設置 MCP fetch 服務器參數
    fetch_mcp_server = StdioServerParams(
        command="node", 
        args=["C:/Users/USER/Desktop/code/mcp-servers/fetch-mcp/dist/index.js"]
    )
    
    # 設置 MCP 文件系統服務器參數
    write_mcp_server = StdioServerParams(
        command="npx", 
        args=["@modelcontextprotocol/server-filesystem", "C:/Users/USER/Desktop/code/CE8014/hw3"]
    )
    
    # 從 MCP 服務器獲取 fetch 工具
    tools_fetch = await mcp_server_tools(fetch_mcp_server)

    # 從 MCP 服務器獲取 filesystem 工具
    tools_write = await mcp_server_tools(write_mcp_server)
    
    # 創建Azure OpenAI模型客戶端
    # 記得先在終端輸入:" $env:AZURE_API_KEY="你的API金鑰 "
    api_key = os.getenv("AZURE_API_KEY")

    model_client = AzureOpenAIChatCompletionClient(
        azure_deployment="gpt-4o",
        azure_endpoint="https://my-llm-service-001.openai.azure.com/",
        model="gpt-4o",
        api_version="2024-12-01-preview",
        api_key=api_key
    )
    
    selector_model_client = AzureOpenAIChatCompletionClient(
        azure_deployment="gpt-4o-mini",
        azure_endpoint="https://my-llm-service-001.openai.azure.com/",
        model="gpt-4o-mini",
        api_version="2024-12-01-preview",
        api_key=api_key
    )
    
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
        2.  **優先抓取**新聞列表、主要內容等最可能包含標題的區域。
        3.  **避免抓取**導航欄、頁腳、廣告等無關內容。
        4.  如果初次抓取的文本明顯缺乏標題內容，可以**嘗試抓取其他部分**（如"Recent Posts"），但仍需使用 `fetch_txt`。
        5.  **禁止自行提取標題**。你的輸出必須是**未經處理的原始文本**（可進行最小程度的清理，如去除多餘空行，但保留結構）。
        6.  將獲取的**原始文本**直接傳遞給 `title_extractor_agent`。
        
        **目標**：提供一個包含足夠潛在標題（理想情況下至少10個）的**原始文本塊**。
        **注意**：除非 `correction_agent` 明確指示，否則不要重複抓取。
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
        2.  **關鍵焦點**：識別出現頻率最高的核心主題或關鍵詞（例如：碳排放、供應鏈、揭露規則、多元共融）。
        3.  **地域/行業**：分析標題中涉及的地理區域或特定行業（如果資訊可用）。
        
        **分析要求**：
        -   **專注數據**：分析必須嚴格基於**輸入的標題列表**，禁止引入外部資訊或猜測。
        -   **結構清晰**：使用清晰的標題和要點呈現分析結果。
        -   **量化支撐**：盡可能使用數據（如主題計數）支持觀點。
        -   **簡潔深入**：分析需精煉，同時揭示標題背後的趨勢。
        
        **輸出**：將結構化的分析報告傳遞給 `reflection_agent`。
        **注意**：除非 `correction_agent` 明確指示，否則不要請求更多標題或資訊。
        """
    )
    
    # 初始化 RAG 系統
    reflection_rag = SimpleRAG()
    
    # 獲取一些評估指南內容
    high_quality_criteria = reflection_rag.query_guide("高質量分析的特徵 什麼是好的評估")
    evaluation_dimensions = reflection_rag.query_guide("評估影響分析的充分程度 關鍵評估維度")
    correction_criteria = reflection_rag.query_guide("需要修正的情況 什麼時候需要修正")
    
    # 創建反思代理 - 評估分析質量，為影響分析提供素材
    reflection_agent = AssistantAgent(
        name="reflection_agent",
        description="負責評估分析結果的質量並提供反思輸入",
        model_client=model_client,
        model_context=BufferedChatCompletionContext(buffer_size=10),
        system_message=f"""你是一位批判性的ESG反思與評估專家。
        **核心任務**：評估 `analyst_agent` 的分析報告品質，提供**用於影響分析的洞見**，並**僅在必要時**觸發修正流程。
        
        **RAG 輔助評估指南**：
        以下是關於評估ESG分析質量的指南，請參考這些標準進行評估：
        
        高質量分析的特徵:
        {high_quality_criteria}
        
        評估影響分析的關鍵維度:
        {evaluation_dimensions}
        
        需要修正的情況:
        {correction_criteria}
        
        **評估與反思步驟**：
        1.  **檢查標題品質**：快速掃描 `title_extractor_agent` 提供的標題列表，判斷其數量和清晰度。
        2.  **評估分析品質**：審查 `analyst_agent` 的分析是否全面、邏輯、有數據支撐且有深度。
        3.  **提供影響分析素材**：基於分析結果，思考以下問題，提供簡潔的洞見：
            *   這些趨勢的主要**潛在影響**是什麼？（正面/負面）
            *   這些趨勢對**不同利益相關者**（企業、投資者、社會）可能意味著什麼？
            *   分析中是否有**被忽略的角度**或**潛在風險**需要注意？
        
        **觸發修正**：**只有在發現以下嚴重問題時**，才輸出「**需要修正**」，並清晰描述問題：
        -   **標題嚴重不足或混亂**
        -   **分析存在嚴重邏輯錯誤或矛盾**
        -   **分析明顯遺漏關鍵趨勢**
        -   **分析缺乏基本數據支持**
        
        **正常流程**：如果未發現嚴重問題，請提供你的**評估意見和影響分析洞見**，並在末尾明確標記「**評估與反思完成**」。你的輸出將作為 `draft_agent` 生成影響分析部分的重要參考。
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
        
        **整合內容來源**：
        1.  **新聞標題列表**：來自 `title_extractor_agent`。
        2.  **主要趨勢分析**：來自 `analyst_agent`。
        3.  **評估與洞見**：來自 `reflection_agent` 的「評估與反思完成」內容，用於**啟發影響分析**。
        
        **報告結構**：嚴格按照以下結構組織報告草稿：
        ```markdown
        # ESG 新聞趨勢分析報告
        
        ## 1. 新聞標題列表
        [此處插入 title_extractor_agent 的輸出]
        [如果標題不足10條，此處插入說明]
        
        ## 2. 主要趨勢分析
        [此處插入 analyst_agent 的分析]
        
        ## 3. 趨勢影響分析 (多角度)
        [**基於趨勢分析和反思洞見，撰寫此部分**]
        *   **對企業的影響**: [分析趨勢對企業營運、策略、風險、機會等的影響]
        *   **對投資者的影響**: [分析趨勢對投資決策、資產評估、風險管理等的影響]
        *   **對消費者/社會的影響**: [分析趨勢對公眾認知、消費行為、社會公平等的影響]
        *   **對從業者/監管機構的影響**: [分析趨勢對相關從業人員技能、行業規範、政策制定等的影響]
        
        ```
        **撰寫要求**：影響分析部分需要結合 `analyst_agent` 的趨勢和 `reflection_agent` 的洞見，進行合理推演和闡述，觀點需中立客觀。
        
        **輸出**：完成報告草稿後，在末尾標記「**草稿完成**」，並將完整的報告草稿傳遞給 `document_agent`。
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
        
        **執行步驟**：
        1.  **確認輸入**：核對收到的訊息是否來自 `draft_agent` 且包含「草稿完成」標記。
        2.  **最終格式化**：確保報告包含主標題「ESG 新聞趨勢分析報告」和日期 `{current_datetime}`。調整Markdown格式使其專業美觀。
        3.  **準備工具參數**：
            *   `content`: 經過最終格式化的完整報告字串。
            *   `path`: 嚴格使用此路徑 `'output/ESG_News_{current_datetime}.md'`。
        4.  **調用保存工具**：**必須且只能使用 `mcp_filesystem_write_file` 工具**，提供準備好的 `content` 和 `path`。
        5.  **結束流程**：在**成功調用 `mcp_filesystem_write_file` 工具後**（你會收到工具執行的結果，確認無誤），**必須立即回復一個單獨的、不包含任何其他字符的字串：「TERMINATE」**。
        
        **極其重要**：
        -   必須實際調用工具 `mcp_filesystem_write_file`。
        -   必須使用指定的 `path`。
        -   **工具調用成功後，你的唯一回覆必須是「TERMINATE」**，沒有任何額外文字。
        """
    )
    
    # 設置終止條件
    text_terminate = TextMentionTermination("TERMINATE")
    max_message = MaxMessageTermination(max_messages=40)  # 增加最大消息數以支持修正過程
    termination = text_terminate | max_message
    
    # 設置選擇器函數，實現分離的抓取/提取和錯誤修正機制
    def selector_func(messages: Sequence[BaseAgentEvent | BaseChatMessage]) -> str | None:
        if len(messages) == 0:
            return None
            
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
            # 只有收到嚴格的 "TERMINATE" 才結束
            if last_content.strip() == "TERMINATE":
                return None # 結束流程
            # 如果 document_agent 回覆了其他內容（例如工具調用結果或錯誤），讓LLM決定下一步
            return None 
            
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
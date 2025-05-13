import os
import re
import openai
from dotenv import load_dotenv

class SimpleRAG:
    
    def __init__(self):
        """初始化簡單 RAG 系統"""
        # 加載環境變量
        load_dotenv()
        
        # 配置 OpenAI
        self.api_key = os.getenv("AZURE_API_KEY")
        self.api_base = os.getenv("AZURE_ENDPOINT", "https://my-llm-service-001.openai.azure.com")
        self.api_version = os.getenv("AZURE_API_VERSION", "2023-05-15")
        
        openai.api_key = self.api_key
        openai.api_base = self.api_base
        openai.api_type = "azure"
        openai.api_version = self.api_version
        
        # 加載手冊內容
        self.guide_content = self._load_guide()
        
        # 將內容分塊
        self.chunks = self._chunk_content(self.guide_content)
        print(f"將文檔分為 {len(self.chunks)} 個塊")
    
    def _load_guide(self):
        """加載 ESG 反思指南"""
        try:
            guide_path = "manual_for_RAG/ESG_Reflection_Agent_Guide.md"
            if not os.path.exists(guide_path):
                print(f"錯誤: 未找到指南文件 {guide_path}")
                return ""
            
            with open(guide_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            print(f"成功加載指南文件，內容長度: {len(content)} 字符")
            return content
        except Exception as e:
            print(f"加載指南文件時出錯: {e}")
            return ""
    
    def _chunk_content(self, content, max_chunk_size=500):
        """將內容分塊，使用章節和段落作為自然分界點"""
        if not content:
            return []
        
        # 使用標題和空行作為分界點
        chunks = []
        
        # 按章節分割
        sections = re.split(r'(^##\s.*$)', content, flags=re.MULTILINE)
        
        current_chunk = ""
        current_section = ""
        
        for i, section in enumerate(sections):
            # 如果是標題
            if section.strip().startswith("##"):
                current_section = section
                # 如果當前塊不為空，先保存
                if current_chunk:
                    chunks.append(current_chunk)
                current_chunk = current_section + "\n"
            else:
                # 按段落分割
                paragraphs = section.split("\n\n")
                for para in paragraphs:
                    if not para.strip():
                        continue
                    # 如果添加這個段落會使當前塊超過最大大小
                    if len(current_chunk) + len(para) > max_chunk_size and current_chunk:
                        chunks.append(current_chunk)
                        current_chunk = current_section + "\n" if current_section else ""
                    
                    current_chunk += para + "\n\n"
        
        # 添加最後一個塊
        if current_chunk:
            chunks.append(current_chunk)
        
        return chunks
    
    def _calculate_similarity(self, query, text):
        """計算查詢和文本塊之間的相似度（基於關鍵詞匹配）"""
        # 將查詢和文本轉換為小寫，並分割為詞
        query_words = set(query.lower().split())
        text_words = set(text.lower().split())
        
        # 計算相交的詞數
        intersection = query_words.intersection(text_words)
        
        # 返回相似度得分
        return len(intersection) / max(len(query_words), 1)
    
    def query_guide(self, query, top_k=3):
        """查詢指南並返回最相關的內容"""
        if not self.chunks:
            return "無法查詢指南，未成功加載指南內容。"
        
        try:
            # 計算每個塊與查詢的相似度
            chunk_scores = [(chunk, self._calculate_similarity(query, chunk)) for chunk in self.chunks]
            
            # 按相似度排序
            chunk_scores.sort(key=lambda x: x[1], reverse=True)
            
            # 獲取最相關的 top_k 個塊
            top_chunks = [chunk for chunk, score in chunk_scores[:top_k]]
            
            # 組合結果
            result = "\n\n".join(top_chunks)
            
            return result
        except Exception as e:
            print(f"查詢過程中出錯: {e}")
            import traceback
            traceback.print_exc()
            return f"查詢時出錯: {e}"


# 測試代碼
if __name__ == "__main__":
    rag = SimpleRAG()
    queries = [
        "如何評估ESG分析的質量?",
        "什麼是高質量標題列表的特徵?",
        "什麼情況下需要修正分析?",
        "如何評估影響分析的充分程度?",
        "優質影響分析有哪些要素?"
    ]
    
    for i, query in enumerate(queries, 1):
        print(f"\n測試查詢 {i}: '{query}'")
        result = rag.query_guide(query)
        print(f"查詢結果 (前200字符):\n{result[:200]}...\n")
        print("-" * 50) 
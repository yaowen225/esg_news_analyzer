import os
import re
import openai
import numpy as np
from dotenv import load_dotenv
from openai import AzureOpenAI

class SimpleRAG:
    
    def __init__(self):
        """初始化簡單 RAG 系統"""
        # 加載環境變量
        load_dotenv()
        
        # 配置 OpenAI
        self.api_key = os.getenv("AZURE_API_KEY")
        self.api_base = os.getenv("AZURE_ENDPOINT", "https://my-llm-service-001.openai.azure.com")
        self.api_version = os.getenv("AZURE_API_VERSION", "2023-05-15")
        
        # 設置嵌入模型名稱
        self.embedding_model = os.getenv("AZURE_EMBEDDING_MODEL", "text-embedding-ada-002")
        # 設置GPT模型名稱
        self.gpt_model = os.getenv("gpt-4o", "gpt-4o")
        
        # 初始化 Azure OpenAI 客戶端
        self.client = AzureOpenAI(
            api_key=self.api_key,
            api_version=self.api_version,
            azure_endpoint=self.api_base
        )
        
        # 加載手冊內容
        self.guide_content = self._load_guide()
        
        # 將內容分塊
        self.chunks = self._chunk_content(self.guide_content)
        print(f"將文檔分為 {len(self.chunks)} 個塊")
        
        # 為文本塊生成嵌入
        self.chunk_embeddings = self._generate_embeddings(self.chunks)
        print(f"已生成 {len(self.chunk_embeddings)} 個文本嵌入")
    
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
    
    def _generate_embeddings(self, texts):
        """使用Azure OpenAI API生成文本嵌入"""
        embeddings = []
        try:
            for text in texts:
                response = self.client.embeddings.create(
                    input=text,
                    model=self.embedding_model
                )
                embeddings.append(response.data[0].embedding)
            return embeddings
        except Exception as e:
            print(f"生成嵌入時出錯: {e}")
            # 如果API出錯，返回空嵌入列表
            return [[] for _ in texts]
    
    def _calculate_similarity(self, query_embedding, chunk_embeddings):
        """計算查詢嵌入和文本塊嵌入之間的餘弦相似度"""
        # 如果嵌入為空，返回零相似度
        if not query_embedding or not chunk_embeddings or not all(chunk_embeddings):
            return [0] * len(chunk_embeddings)
        
        similarities = []
        for emb in chunk_embeddings:
            # 計算兩個向量的點積
            dot_product = sum(a * b for a, b in zip(query_embedding, emb))
            # 計算向量長度
            magnitude_a = sum(a * a for a in query_embedding) ** 0.5
            magnitude_b = sum(b * b for b in emb) ** 0.5
            # 計算餘弦相似度
            similarity = dot_product / (magnitude_a * magnitude_b) if magnitude_a * magnitude_b > 0 else 0
            similarities.append(similarity)
        
        return similarities
    
    def query_guide(self, query, top_k=3):
        """查詢指南並返回最相關的內容"""
        if not self.chunks:
            return "無法查詢指南，未成功加載指南內容。"
        
        try:
            # 生成查詢的嵌入向量
            query_embedding = self._generate_embeddings([query])[0]
            
            # 計算相似度
            similarities = self._calculate_similarity(query_embedding, self.chunk_embeddings)
            
            # 排序並獲取前top_k個相似塊的索引
            top_indices = sorted(range(len(similarities)), key=lambda i: similarities[i], reverse=True)[:top_k]
            
            # 獲取最相關的top_k個塊
            top_chunks = [self.chunks[i] for i in top_indices]
            
            # 將相關內容組合為上下文
            context = "\n\n".join(top_chunks)
            
            try:
                # 使用GPT模型生成最終回答
                response = self.client.chat.completions.create(
                    model=self.gpt_model,
                    messages=[
                        {"role": "system", "content": "你是一個ESG分析助手。請根據提供的上下文回答用戶問題。如果上下文中沒有相關信息，請誠實告知。"},
                        {"role": "user", "content": f"基於以下參考信息回答問題：\n\n{context}\n\n問題：{query}"}
                    ]
                )
                return response.choices[0].message.content
            except Exception as api_error:
                print(f"GPT API調用出錯: {api_error}")
                # 如果GPT API調用失敗，回退到直接返回相關內容
                return context
                
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
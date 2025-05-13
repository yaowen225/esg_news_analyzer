import os
from dotenv import load_dotenv
from simple_rag import SimpleRAG

def test_simple_rag():
    """測試簡單 RAG 系統"""
    print("開始測試簡單 RAG 系統...")
    
    # 加載環境變量
    load_dotenv()
    
    # 檢查API Key
    api_key = os.getenv("AZURE_API_KEY")
    if not api_key:
        print("錯誤: 未設置 AZURE_API_KEY 環境變量")
        print("請使用 '$env:AZURE_API_KEY=\"你的API金鑰\"' 設置環境變量")
        return False
    else:
        print(f"找到 AZURE_API_KEY 環境變量 (長度: {len(api_key)})")
    
    # 檢查手冊文件
    guide_path = "manual_for_RAG/ESG_Reflection_Agent_Guide.md"
    if not os.path.exists(guide_path):
        print(f"錯誤: 未找到手冊文件 {guide_path}")
        print("請將 ESG_Reflection_Agent_Guide.md 檔案移動到 manual_for_RAG 目錄")
        return False
    else:
        file_size = os.path.getsize(guide_path)
        print(f"找到手冊文件: {guide_path} (大小: {file_size} 字節)")
    
    try:
        # 初始化 RAG 系統
        rag = SimpleRAG()
        
        # 測試查詢
        test_queries = [
            "如何評估ESG分析的質量?",
            "什麼是高質量標題列表的特徵?",
            "什麼情況下需要修正分析?",
            "如何評估影響分析的充分程度?",
            "優質影響分析有哪些要素?"
        ]
        
        print("\n開始測試查詢...")
        for i, query in enumerate(test_queries, 1):
            print(f"\n測試查詢 {i}: '{query}'")
            result = rag.query_guide(query)
            if result and len(result) > 0:
                print(f"查詢結果 (前200字符):\n{result[:200]}...\n")
                print("-" * 50)
            else:
                print(f"錯誤: 查詢 '{query}' 返回空結果")
                return False
        
        print("\n測試成功完成!")
        return True
        
    except Exception as e:
        print(f"測試過程中發生錯誤: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("簡單 RAG 系統測試")
    print("=" * 50)
    
    success = test_simple_rag()
    
    if success:
        print("\n✅ 測試成功: 簡單 RAG 系統運行正常")
    else:
        print("\n❌ 測試失敗: 簡單 RAG 系統存在問題") 
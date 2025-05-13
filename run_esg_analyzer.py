import os
import sys
from dotenv import load_dotenv

def check_environment():
    """檢查環境設置和必要文件"""
    # 加載環境變量
    load_dotenv()
    
    # 檢查API Key
    api_key = os.getenv("AZURE_API_KEY")
    if not api_key:
        print("錯誤: 未設置 AZURE_API_KEY 環境變量")
        print("請使用 '$env:AZURE_API_KEY=\"你的API金鑰\"' 設置環境變量")
        return False
    
    # 檢查手冊目錄
    if not os.path.exists("manual_for_RAG"):
        print("創建 manual_for_RAG 目錄...")
        os.makedirs("manual_for_RAG", exist_ok=True)
        print("請確保將 ESG_Reflection_Agent_Guide.md 放入 manual_for_RAG 目錄")
        return False
    
    # 檢查手冊文件
    guide_path = "manual_for_RAG/ESG_Reflection_Agent_Guide.md"
    if not os.path.exists(guide_path):
        print(f"錯誤: 未找到手冊文件 {guide_path}")
        print("請將 ESG_Reflection_Agent_Guide.md 檔案移動到 manual_for_RAG 目錄")
        return False
    
    # 檢查 reflection_rag.py
    if not os.path.exists("reflection_rag.py"):
        print("錯誤: 未找到 reflection_rag.py")
        return False
    
    # 檢查主程序文件
    if not os.path.exists("esg_news_analyzer.py"):
        print("錯誤: 未找到 esg_news_analyzer.py")
        return False
    
    # 檢查輸出目錄
    if not os.path.exists("output"):
        print("創建 output 目錄...")
        os.makedirs("output", exist_ok=True)
    
    return True

def main():
    """主函數"""
    print("ESG 新聞分析器 - RAG 增強版")
    print("----------------------------")
    
    # 檢查環境
    if not check_environment():
        print("\n環境檢查失敗，請解決上述問題後重試")
        return
    
    print("\n環境檢查通過！")
    print("開始執行 ESG 新聞分析...")
    
    # 執行主程序
    import asyncio
    from esg_news_analyzer import main as esg_main
    
    try:
        asyncio.run(esg_main())
        print("\nESG 新聞分析完成！請查看 output 目錄獲取結果報告")
    except Exception as e:
        print(f"\n執行過程中發生錯誤: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 
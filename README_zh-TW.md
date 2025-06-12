# NeuralResearcher
![NeuralResearcher](assets/logo.png)

**🌐 Language / 语言 / 言語 / 언어**
- [English](README.md)
- [简体中文](README_zh-CN.md)
- [繁體中文](README_zh-TW.md) (目前)
- [日本語](README_ja.md)
- [한국어](README_ko.md)

---

基於LangGraph的智慧研究助手，能夠自動進行深度研究並產生高品質的研究報告。

## 功能特性

- 🔍 **智慧搜尋**：支援多種搜尋引擎（DuckDuckGo、Google等）
- 🤖 **8智慧體協作**：使用LangGraph協調編排器、研究員、編輯、寫作、審查、修訂、人工和發布智慧體
- 📊 **並行研究**：同時對多個主題進行深度研究
- 📝 **多格式輸出**：支援Markdown、PDF、DOCX格式
- 🔄 **品質控制**：內建審查和修訂機制
- 💰 **成本追蹤**：即時追蹤API呼叫成本
- 🎯 **可設定**：靈活的設定選項和指導原則
- 🗄️ **RAG框架**：整合本地文件檢索和向量資料庫
- 📚 **多資料類型**：支援文件、結構化資料和資料流處理
- 🔗 **混合檢索**：智慧結合本地文件和網路搜尋

## 架構設計

### 主工作流管道

系統遵循13步主工作流，具有模組化元件以增強可維護性和可擴展性：

![主工作流管道](assets/main-flow.svg)

### 核心系統元件

#### 🔄 **13步主管道**
1. **編排器初始化** - 系統初始化和任務協調
2. **初始研究** - 使用RAG模組進行初步資訊收集
3. **計劃大綱** - 研究結構規劃和章節定義
4. **人工審查計劃** - 可選的人工監督和回饋
5. **修訂計劃** - 基於回饋的計劃完善（條件迴圈）
6. **並行研究** - 多執行緒深度研究執行
7. **審查研究** - 品質評估和驗證
8. **撰寫報告** - 使用範本和本地化進行內容產生
9. **人工審查報告** - 可選的最終內容人工審查
10. **修訂報告** - 基於回饋的內容完善（條件迴圈）
11. **最終審查** - 綜合品質檢查
12. **發布報告** - 多格式文件產生
13. **編排器完成** - 任務完成和清理

#### 🤖 **8智慧體協作系統**
- **編排器智慧體**：協調整體工作流程並管理智慧體互動
- **研究員智慧體**：負責資訊收集和深度研究
- **編輯智慧體**：負責研究大綱規劃和並行研究管理
- **寫作智慧體**：負責撰寫和組織最終報告
- **審查智慧體**：負責品質審查和回饋
- **修訂智慧體**：負責基於回饋修訂內容
- **人工智慧體**：負責人工監督和回饋
- **發布智慧體**：負責多格式文件發布

### 模組化架構元件

系統採用解耦模組設計，可以獨立開發和維護：

#### 📚 **RAG模組 - 文件處理與檢索**
![RAG模組](assets/doc-processing.svg)

**主要功能：**
- 多格式文件處理（PDF、DOCX、TXT、CSV、JSON、XML）
- 掃描文件的OCR文字提取
- 分塊摘要和合併的長文字處理
- Milvus向量資料庫進行語義搜尋
- 混合檢索策略（本地文件+網路搜尋）
- 支援結構化資料和資料流

#### ⚡ **並行處理模組 - 多任務研究**
![並行處理模組](assets/parallel-process.svg)

**主要功能：**
- 多個研究任務的並發執行
- 每個主題的深度搜尋和逾時處理
- 結果聚合和去重
- 品質過濾和相關性排序
- 錯誤處理和重試機制

#### 🌐 **範本與本地化模組**
![範本與本地化模組](assets/template-local.svg)

**主要功能：**
- YAML/JSON範本設定系統
- 章節結構和引用格式自訂
- 多語言支援（英語、簡體中文/繁體中文、日語、韓語）
- 未指定範本時的自由LLM產生
- 內容格式化和驗證

#### 📄 **多格式發布模組**
![多格式發布模組](assets/fomat-process.svg)

**主要功能：**
- Markdown、PDF和DOCX格式產生
- 元資料整合和檔案組織
- 帶回退格式的錯誤處理
- 發布摘要和驗證
- 靈活的輸出目錄管理

## 安裝和設定

### 1. 安裝相依性
```bash
pip install -r requirements.txt
```

### 2. 環境設定
複製環境變數範本並設定：
```bash
cp .env.example .env
```

編輯`.env`檔案並新增必要的API金鑰：
```env
OPENAI_API_KEY=your_openai_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here  # 可選
GOOGLE_API_KEY=your_google_api_key_here        # 可選

# RAG設定（可選）
MILVUS_HOST=localhost
MILVUS_PORT=19530
EMBEDDING_PROVIDER=openai
RETRIEVER=hybrid  # web, local, hybrid
DOC_PATH=./my-docs
```

### 3. 啟動Milvus資料庫（可選，用於RAG功能）
```bash
# 使用Docker啟動Milvus
wget https://github.com/milvus-io/milvus/releases/download/v2.3.0/milvus-standalone-docker-compose.yml -O docker-compose.yml
docker-compose up -d

# 檢查狀態
docker-compose ps
```

### 4. 建立輸出目錄
```bash
mkdir -p outputs logs my-docs
```

## 使用方法

### 命令列使用

#### 基本使用
```bash
python main.py "AI在醫療保健中的應用前景如何？"
```

#### 進階使用
```bash
python main.py "氣候變遷對全球糧食安全的影響" \
  --format markdown pdf docx \
  --max-sections 5 \
  --model gpt-4o \
  --tone analytical \
  --verbose
```

#### 使用設定檔
```bash
python main.py --config task.json
```

### RAG文件管理

#### 索引本地文件
```bash
# 索引整個目錄
python rag_cli.py index --source ./my-docs

# 索引單一檔案
python rag_cli.py index --source ./document.pdf
```

#### 搜尋本地文件
```bash
# 基本搜尋
python rag_cli.py search --query "機器學習演算法"

# 進階搜尋
python rag_cli.py search --query "人工智慧" \
  --top-k 5 \
  --doc-types pdf txt \
  --threshold 0.8
```

#### 檢視文件統計
```bash
python rag_cli.py stats
```

#### 測試RAG系統
```bash
python test_rag_system.py
```

### 程式介面使用

#### 基本研究
```python
import asyncio
from main import ResearchRunner

async def run_research():
    runner = ResearchRunner()

    result = await runner.run_research_from_query(
        query="人工智慧發展的最新趨勢",
        max_sections=3,
        publish_formats={"markdown": True, "pdf": True}
    )

    runner.print_results_summary(result)

asyncio.run(run_research())
```

#### 進階設定
```python
from config import TaskConfig
from main import ResearchRunner

async def advanced_research():
    task_config = TaskConfig(
        query="區塊鏈技術在金融領域的應用",
        max_sections=5,
        publish_formats={"markdown": True, "pdf": True, "docx": True},
        follow_guidelines=True,
        guidelines=[
            "使用學術寫作風格",
            "包含具體案例研究",
            "引用權威來源"
        ],
        model="gpt-4o",
        tone="analytical"
    )

    runner = ResearchRunner()
    result = await runner.run_research_from_config(task_config)

    return result
```

## 設定選項

### 任務設定 (task.json)
```json
{
  "query": "研究問題",
  "max_sections": 5,
  "publish_formats": {
    "markdown": true,
    "pdf": true,
    "docx": false
  },
  "model": "gpt-4o",
  "tone": "objective",
  "guidelines": [
    "寫作指導原則1",
    "寫作指導原則2"
  ],
  "verbose": true
}
```

### 環境變數設定
主要設定項：
- `LLM_PROVIDER`: LLM提供商 (openai/anthropic)
- `SMART_LLM_MODEL`: 智慧模型 (gpt-4o)
- `FAST_LLM_MODEL`: 快速模型 (gpt-4o-mini)
- `MAX_SEARCH_RESULTS_PER_QUERY`: 每次搜尋查詢的最大結果數
- `OUTPUT_PATH`: 輸出目錄路徑

RAG相關設定：
- `RETRIEVER`: 檢索模式 (web/local/hybrid)
- `MILVUS_HOST`: Milvus資料庫主機
- `MILVUS_PORT`: Milvus資料庫連接埠
- `EMBEDDING_PROVIDER`: 嵌入模型提供商 (openai/sentence_transformers/huggingface)
- `EMBEDDING_MODEL`: 嵌入模型名稱
- `CHUNK_SIZE`: 文件塊大小
- `SIMILARITY_THRESHOLD`: 相似度閾值
- `DOC_PATH`: 本地文件目錄路徑

## 輸出格式

### 研究報告結構
1. **標題和元資料**
2. **目錄**
3. **引言**
4. **主要研究章節**
5. **結論**
6. **參考文獻**
7. **報告元資料**

### 支援的輸出格式
- **Markdown** (.md): 適合線上閱讀和進一步編輯
- **PDF** (.pdf): 適合列印和正式分發
- **DOCX** (.docx): 適合Microsoft Word編輯

## 成本管理

系統自動追蹤API呼叫成本：
- OpenAI API呼叫成本
- 按模型和令牌使用量計算
- 報告中顯示總成本
- 支援成本預算控制

## 故障排除

### 常見問題

1. **API金鑰錯誤**
   - 檢查`.env`檔案中的API金鑰是否正確
   - 確認API金鑰有足夠的配額

2. **搜尋結果為空**
   - 檢查網路連線
   - 嘗試切換搜尋引擎
   - 調整搜尋查詢

3. **報告產生失敗**
   - 檢查輸出目錄權限
   - 確認有足夠的磁碟空間
   - 查看日誌檔案獲取詳細錯誤資訊

### 日誌檔案
- 應用程式日誌：`logs/research.log`
- 詳細錯誤資訊和除錯資訊

## 測試和驗證

### 範例執行
```bash

# 快速測試
python -c "
import asyncio
from main import ResearchRunner
async def test():
    runner = ResearchRunner()
    result = await runner.run_research_from_query('什麼是機器學習？', max_sections=2)
    print(f'狀態: {result[\"status\"]}')
asyncio.run(test())
"
```

### 人工回饋測試
```bash
# 啟用人工回饋的研究
python main.py "AI發展趨勢" --format markdown --verbose
# 注意：這將在研究過程中需要人工輸入回饋
```

## 擴展開發

### 新增新智慧體
1. 在`agents/`目錄中建立新的智慧體類別
2. 繼承基礎智慧體介面
3. 在`graph.py`中註冊新節點
4. 更新工作流程圖

### 新增新工具
1. 在`tools/`目錄中建立新工具
2. 實作必要的介面方法
3. 在相關智慧體中整合新工具

### 自訂輸出格式
1. 在`tools/document_tools.py`中新增新產生器
2. 更新`PublisherAgent`以支援新格式
3. 在設定中新增新格式選項

## 授權

Apache License 2.0

## 貢獻

歡迎提交Issues和Pull Requests來改進專案。

## 更新日誌

### v2.0.0 - 8智慧體管道
- 擴展到8個專業智慧體
- 新增編排器智慧體進行工作流協調
- 新增修訂智慧體進行內容修訂
- 新增人工智慧體進行人工監督
- 完整的人工回饋迴圈
- 進階品質控制機制
- 條件修訂過程
- 詳細的效能監控

### v1.0.0 - 基礎多智慧體系統
- 基於LangGraph的完整重構
- 5智慧體協作架構
- 並行研究處理
- 多格式輸出支援
- 成本追蹤功能
- 基礎品質控制機制

# NeuralResearcher
![NeuralResearcher](assets/logo.png)

An intelligent research assistant based on LangGraph that can automatically conduct in-depth research and generate high-quality research reports.

## Features

- 🔍 **Smart Search**: Support for multiple search engines (DuckDuckGo, Google, etc.)
- 🤖 **8-Agent Collaboration**: Uses LangGraph to coordinate Orchestrator, Researcher, Editor, Writer, Reviewer, Reviser, Human, and Publisher agents
- 📊 **Parallel Research**: Simultaneous in-depth research on multiple topics
- 📝 **Multi-format Output**: Support for Markdown, PDF, DOCX formats
- 🔄 **Quality Control**: Built-in review and revision mechanisms
- 💰 **Cost Tracking**: Real-time tracking of API call costs
- 🎯 **Configurable**: Flexible configuration options and guidelines
- 🗄️ **RAG Framework**: Integrated local document retrieval and vector database
- 📚 **Multi-data Types**: Support for documents, structured data, and data stream processing
- 🔗 **Hybrid Retrieval**: Intelligent combination of local documents and web search

## Architecture Design

### Main Workflow Pipeline

The system follows a 13-step main workflow with modular components for enhanced maintainability and scalability:

![Main Workflow Pipeline](assets/main-flow.svg)

### Core System Components

#### 🔄 **13-Step Main Pipeline**
1. **Orchestrator Init** - System initialization and task coordination
2. **Initial Research** - Preliminary information gathering using RAG module
3. **Plan Outline** - Research structure planning and section definition
4. **Human Review Plan** - Optional human supervision and feedback
5. **Revise Plan** - Plan refinement based on feedback (conditional loop)
6. **Parallel Research** - Multi-threaded deep research execution
7. **Review Research** - Quality assessment and validation
8. **Write Report** - Content generation with template and localization
9. **Human Review Report** - Optional human review of final content
10. **Revise Report** - Content refinement based on feedback (conditional loop)
11. **Final Review** - Comprehensive quality check
12. **Publish Report** - Multi-format document generation
13. **Orchestrator Finalize** - Task completion and cleanup

#### 🤖 **8-Agent Collaboration System**
- **OrchestratorAgent**: Coordinates overall workflow and manages agent interactions
- **ResearcherAgent**: Responsible for information gathering and in-depth research
- **EditorAgent**: Responsible for research outline planning and parallel research management
- **WriterAgent**: Responsible for writing and organizing the final report
- **ReviewerAgent**: Responsible for quality review and feedback
- **ReviserAgent**: Responsible for revising content based on feedback
- **HumanAgent**: Responsible for human supervision and feedback
- **PublisherAgent**: Responsible for multi-format document publishing

### Modular Architecture Components

The system is designed with decoupled modules that can be independently developed and maintained:

#### 📚 **RAG Module - Document Processing & Retrieval**
![RAG Module](assets/doc-processing.svg)

**Key Features:**
- Multi-format document processing (PDF, DOCX, TXT, CSV, JSON, XML)
- OCR text extraction for scanned documents
- Long text processing with chunked summarization and merging
- Milvus vector database for semantic search
- Hybrid retrieval strategy (local documents + web search)
- Support for structured data and data streams

#### ⚡ **Parallel Processing Module - Multi-Task Research**
![Parallel Processing Module](assets/parallel-process.svg)

**Key Features:**
- Concurrent execution of multiple research tasks
- Deep search for each topic with timeout handling
- Result aggregation and deduplication
- Quality filtering and relevance ranking
- Error handling and retry mechanisms

#### 🌐 **Template & Localization Module**
![Template & Localization Module](assets/template-local.svg)

**Key Features:**
- YAML/JSON template configuration system
- Chapter structure and citation format customization
- Multi-language support (English, Chinese Simplified/Traditional, Japanese, Korean)
- Free LLM generation when no template is specified
- Content formatting and validation

#### 📄 **Multi-format Publishing Module**
![Multi-format Publishing Module](assets/fomat-process.svg)

**Key Features:**
- Markdown, PDF, and DOCX format generation
- Metadata integration and file organization
- Error handling with fallback formats
- Publishing summary and validation
- Flexible output directory management

## Installation and Configuration

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Environment Configuration
Copy the environment variable template and configure:
```bash
cp .env.example .env
```

Edit the `.env` file and add necessary API keys:
```env
OPENAI_API_KEY=your_openai_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here  # Optional
GOOGLE_API_KEY=your_google_api_key_here        # Optional

# RAG Configuration (Optional)
MILVUS_HOST=localhost
MILVUS_PORT=19530
EMBEDDING_PROVIDER=openai
RETRIEVER=hybrid  # web, local, hybrid
DOC_PATH=./my-docs
```

### 3. Start Milvus Database (Optional, for RAG functionality)
```bash
# Start Milvus using Docker
wget https://github.com/milvus-io/milvus/releases/download/v2.3.0/milvus-standalone-docker-compose.yml -O docker-compose.yml
docker-compose up -d

# Check status
docker-compose ps
```

### 4. Create Output Directories
```bash
mkdir -p outputs logs my-docs
```

## Usage

### Command Line Usage

#### Basic Usage
```bash
python main.py "What are the prospects for AI applications in healthcare?"
```

#### Advanced Usage
```bash
python main.py "Impact of climate change on global food security" \
  --format markdown pdf docx \
  --max-sections 5 \
  --model gpt-4o \
  --tone analytical \
  --verbose
```

#### Using Configuration File
```bash
python main.py --config task.json
```

### RAG Document Management

#### Index Local Documents
```bash
# Index entire directory
python rag_cli.py index --source ./my-docs

# Index single file
python rag_cli.py index --source ./document.pdf
```

#### Search Local Documents
```bash
# Basic search
python rag_cli.py search --query "machine learning algorithms"

# Advanced search
python rag_cli.py search --query "artificial intelligence" \
  --top-k 5 \
  --doc-types pdf txt \
  --threshold 0.8
```

#### View Document Statistics
```bash
python rag_cli.py stats
```

#### Test RAG System
```bash
python test_rag_system.py
```

### Programming Interface Usage

#### Basic Research
```python
import asyncio
from main import ResearchRunner

async def run_research():
    runner = ResearchRunner()

    result = await runner.run_research_from_query(
        query="Latest trends in artificial intelligence development",
        max_sections=3,
        publish_formats={"markdown": True, "pdf": True}
    )

    runner.print_results_summary(result)

asyncio.run(run_research())
```

#### Advanced Configuration
```python
from config import TaskConfig
from main import ResearchRunner

async def advanced_research():
    task_config = TaskConfig(
        query="Applications of blockchain technology in finance",
        max_sections=5,
        publish_formats={"markdown": True, "pdf": True, "docx": True},
        follow_guidelines=True,
        guidelines=[
            "Use academic writing style",
            "Include specific case studies",
            "Cite authoritative sources"
        ],
        model="gpt-4o",
        tone="analytical"
    )

    runner = ResearchRunner()
    result = await runner.run_research_from_config(task_config)

    return result
```

## Configuration Options

### Task Configuration (task.json)
```json
{
  "query": "Research question",
  "max_sections": 5,
  "publish_formats": {
    "markdown": true,
    "pdf": true,
    "docx": false
  },
  "model": "gpt-4o",
  "tone": "objective",
  "guidelines": [
    "Writing guideline 1",
    "Writing guideline 2"
  ],
  "verbose": true
}
```

### Environment Variable Configuration
Main configuration items:
- `LLM_PROVIDER`: LLM provider (openai/anthropic)
- `SMART_LLM_MODEL`: Smart model (gpt-4o)
- `FAST_LLM_MODEL`: Fast model (gpt-4o-mini)
- `MAX_SEARCH_RESULTS_PER_QUERY`: Maximum results per search query
- `OUTPUT_PATH`: Output directory path

RAG-related configuration:
- `RETRIEVER`: Retrieval mode (web/local/hybrid)
- `MILVUS_HOST`: Milvus database host
- `MILVUS_PORT`: Milvus database port
- `EMBEDDING_PROVIDER`: Embedding model provider (openai/sentence_transformers/huggingface)
- `EMBEDDING_MODEL`: Embedding model name
- `CHUNK_SIZE`: Document chunk size
- `SIMILARITY_THRESHOLD`: Similarity threshold
- `DOC_PATH`: Local document directory path

## Output Formats

### Research Report Structure
1. **Title and Metadata**
2. **Table of Contents**
3. **Introduction**
4. **Main Research Sections**
5. **Conclusion**
6. **References**
7. **Report Metadata**

### Supported Output Formats
- **Markdown** (.md): Suitable for online reading and further editing
- **PDF** (.pdf): Suitable for printing and formal distribution
- **DOCX** (.docx): Suitable for Microsoft Word editing

## Cost Management

The system automatically tracks API call costs:
- OpenAI API call costs
- Calculated by model and token usage
- Total cost displayed in reports
- Support for cost budget control

## Troubleshooting

### Common Issues

1. **API Key Errors**
   - Check if API keys in `.env` file are correct
   - Confirm API keys have sufficient quota

2. **Empty Search Results**
   - Check network connection
   - Try switching search engines
   - Adjust search queries

3. **Report Generation Failure**
   - Check output directory permissions
   - Confirm sufficient disk space
   - Check log files for detailed error information

### Log Files
- Application logs: `logs/research.log`
- Detailed error information and debugging info

## Testing and Validation

### System Testing
```bash
# Run basic system tests
python test_system.py

# Run 8-agent pipeline tests
python test_8agent_pipeline.py
```

### Example Runs
```bash
# Run interactive example
python run_example.py

# Quick test
python -c "
import asyncio
from main import ResearchRunner
async def test():
    runner = ResearchRunner()
    result = await runner.run_research_from_query('What is machine learning?', max_sections=2)
    print(f'Status: {result[\"status\"]}')
asyncio.run(test())
"
```

### Human Feedback Testing
```bash
# Research with human feedback enabled
python main.py "AI development trends" --format markdown --verbose
# Note: This will require human input feedback during the research process
```

## Extension Development

### Adding New Agents
1. Create new agent class in `agents/` directory
2. Inherit from base agent interface
3. Register new node in `graph.py`
4. Update workflow diagram

### Adding New Tools
1. Create new tool in `tools/` directory
2. Implement necessary interface methods
3. Integrate new tool in relevant agents

### Custom Output Formats
1. Add new generator in `tools/document_tools.py`
2. Update `PublisherAgent` to support new format
3. Add new format option in configuration

## License

Apache License 2.0

## Contributing

Issues and Pull Requests are welcome to improve the project.

## Changelog

### v2.0.0 - 8-Agent Pipeline
- Extended to 8 specialized agents
- Added OrchestratorAgent for workflow coordination
- Added ReviserAgent for content revision
- Added HumanAgent for human supervision
- Complete human feedback loop
- Advanced quality control mechanisms
- Conditional revision process
- Detailed performance monitoring

### v1.0.0 - Basic Multi-Agent System
- Complete refactoring based on LangGraph
- 5-agent collaboration architecture
- Parallel research processing
- Multi-format output support
- Cost tracking functionality
- Basic quality control mechanisms

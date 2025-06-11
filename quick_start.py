#!/usr/bin/env python3
"""
NeuroResearcher Quick Demo Script
A simplified demonstration of the core research pipeline functionality
"""

import asyncio
import logging
import sys
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def quick_research_demo():
    """Quick demonstration of the research pipeline"""
    print("🧠 NeuroResearcher Quick Demo")
    print("=" * 50)
    
    try:
        # Import core components
        from config import get_config, get_task_config
        from main import ResearchRunner
        
        print("✅ Core components loaded successfully")
        
        # Initialize configuration
        config = get_config()
        runner = ResearchRunner()
        
        print(f"✅ Configuration loaded - Provider: {config.llm_provider}")
        
        # Create a simple research task
        task_config = get_task_config(
            query="What are the key benefits and challenges of renewable energy?",
            max_sections=3,
            publish_formats={"markdown": True},
            model="gpt-4o-mini",
            tone="informative",
            verbose=True
        )
        
        print(f"✅ Research task created:")
        print(f"   Query: {task_config.query}")
        print(f"   Sections: {task_config.max_sections}")
        print(f"   Format: {list(task_config.publish_formats.keys())}")
        
        # Check API configuration
        if not config.openai_api_key or config.openai_api_key == "your_openai_api_key_here":
            print("\n⚠️  API Key Configuration Required")
            print("   To run actual research, please:")
            print("   1. Create a .env file in the project root")
            print("   2. Add: OPENAI_API_KEY=your_actual_api_key")
            print("   3. Run this script again")
            print("\n✅ Pipeline structure verified - ready for API key configuration!")
            return True
        
        print("\n🚀 API keys configured - running research...")
        
        # Execute research
        result = await runner.run_research_from_config(task_config)
        
        # Display results
        if result.get("status") == "completed":
            print("\n🎉 Research Completed Successfully!")
            runner.print_results_summary(result)
            
            # Show output files
            final_state = result.get("final_state", {})
            publisher_output = final_state.get("agent_outputs", {}).get("publisher", {})
            if publisher_output:
                published_files = publisher_output.get("published_files", {})
                print("\n📁 Generated Files:")
                for format_type, file_path in published_files.items():
                    if not file_path.startswith("Error:"):
                        print(f"   - {format_type.upper()}: {file_path}")
        else:
            print(f"\n⚠️  Research completed with status: {result.get('status')}")
            if result.get('error'):
                print(f"   Error: {result.get('error')}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Demo failed: {str(e)}")
        print("   This might be due to missing dependencies or configuration issues")
        return False


async def show_pipeline_architecture():
    """Display the 8-agent pipeline architecture"""
    print("\n🏗️  NeuroResearcher 8-Agent Architecture")
    print("=" * 50)
    
    agents = [
        ("1. Orchestrator", "Coordinates the entire research workflow"),
        ("2. Researcher", "Conducts web searches and gathers information"),
        ("3. Editor", "Plans research outline and manages parallel tasks"),
        ("4. Writer", "Composes the final research report"),
        ("5. Reviewer", "Reviews research quality and report content"),
        ("6. Reviser", "Handles revisions based on feedback"),
        ("7. Human", "Provides human-in-the-loop feedback"),
        ("8. Publisher", "Generates output in multiple formats")
    ]
    
    for agent, description in agents:
        print(f"   {agent}: {description}")
    
    print("\n🔄 Workflow Stages:")
    stages = [
        "Initialize → Research → Plan → Review → Revise → Write → Publish → Finalize"
    ]
    print(f"   {stages[0]}")


def show_usage_examples():
    """Display usage examples"""
    print("\n📚 Usage Examples")
    print("=" * 50)
    
    examples = [
        {
            "title": "Basic Research",
            "command": "python main.py 'What is machine learning?'",
            "description": "Simple research query with default settings"
        },
        {
            "title": "Multi-format Output",
            "command": "python main.py 'Climate change impacts' --format markdown pdf docx",
            "description": "Generate report in multiple formats"
        },
        {
            "title": "Custom Configuration",
            "command": "python main.py 'AI ethics' --max-sections 5 --tone analytical --model gpt-4o",
            "description": "Advanced settings with specific parameters"
        },
        {
            "title": "Multilingual Research",
            "command": "python main.py --config examples/multilingual_task_example.json",
            "description": "Use configuration file for Chinese language research"
        },
        {
            "title": "Human Feedback",
            "command": "python main.py 'Future of work' --include-human-feedback",
            "description": "Enable human-in-the-loop review process"
        }
    ]
    
    for i, example in enumerate(examples, 1):
        print(f"\n{i}. {example['title']}:")
        print(f"   Command: {example['command']}")
        print(f"   Description: {example['description']}")


def check_system_requirements():
    """Check system requirements and dependencies"""
    print("\n🔍 System Requirements Check")
    print("=" * 50)
    
    # Critical dependencies
    critical_deps = [
        ("langgraph", "LangGraph workflow engine"),
        ("langchain", "LangChain framework"),
        ("openai", "OpenAI API client"),
        ("pydantic", "Data validation"),
        ("aiohttp", "Async HTTP client"),
        ("beautifulsoup4", "Web scraping")
    ]
    
    # Optional dependencies
    optional_deps = [
        ("anthropic", "Anthropic Claude API"),
        ("torch", "PyTorch for embeddings"),
        ("sentence_transformers", "Sentence embeddings"),
        ("pymilvus", "Milvus vector database"),
        ("pandas", "Data processing")
    ]
    
    print("Critical Dependencies:")
    for dep, desc in critical_deps:
        try:
            __import__(dep)
            print(f"   ✅ {dep} - {desc}")
        except ImportError:
            print(f"   ❌ {dep} - {desc} (MISSING)")
    
    print("\nOptional Dependencies:")
    for dep, desc in optional_deps:
        try:
            __import__(dep)
            print(f"   ✅ {dep} - {desc}")
        except ImportError:
            print(f"   ⚠️  {dep} - {desc} (optional)")
    
    # Check configuration files
    print("\nConfiguration Files:")
    config_files = [
        (".env", "Environment variables"),
        ("examples/multilingual_task_example.json", "Multilingual example"),
        ("templates/default_templates.yaml", "Default templates"),
        ("localization/languages", "Language files")
    ]
    
    for file_path, desc in config_files:
        if Path(file_path).exists():
            print(f"   ✅ {file_path} - {desc}")
        else:
            print(f"   ⚠️  {file_path} - {desc} (missing)")


async def main():
    """Main execution function"""
    print("🎯 NeuroResearcher Quick Demo & Setup Guide\n")
    
    # Check system requirements
    check_system_requirements()
    
    # Show architecture
    await show_pipeline_architecture()
    
    # Show usage examples
    show_usage_examples()
    
    # Run quick demo
    print("\n" + "=" * 60)
    print("RUNNING QUICK DEMO")
    print("=" * 60)
    
    success = await quick_research_demo()
    
    # Final instructions
    print("\n" + "=" * 60)
    print("SETUP INSTRUCTIONS")
    print("=" * 60)
    
    if success:
        print("🎉 Demo completed successfully!")
        print("\n📝 To get started with real research:")
        print("1. Create .env file with your API keys:")
        print("   OPENAI_API_KEY=your_openai_key_here")
        print("   ANTHROPIC_API_KEY=your_anthropic_key_here  # optional")
        print("\n2. Run your first research:")
        print("   python main.py 'Your research question here'")
        print("\n3. Check the outputs/ directory for results")
        print("\n4. Explore advanced features:")
        print("   - Multi-language support")
        print("   - RAG integration with local documents")
        print("   - Human-in-the-loop workflows")
        print("   - Custom templates and formats")
    else:
        print("⚠️  Demo encountered issues. Please check:")
        print("1. All required dependencies are installed")
        print("2. Python version is 3.8 or higher")
        print("3. Run: pip install -r requirements.txt")
    
    return success


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)

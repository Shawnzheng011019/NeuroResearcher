#!/usr/bin/env python3
"""
Example script to demonstrate GPT Researcher LangGraph implementation
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from config import TaskConfig, Tone
from main import ResearchRunner

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def example_ai_research():
    """Example: Research on AI trends"""
    print("🔬 Starting AI Research Example")
    print("="*60)
    
    runner = ResearchRunner()
    
    result = await runner.run_research_from_query(
        query="人工智能在2024年的最新发展趋势和应用前景",
        max_sections=3,
        publish_formats={"markdown": True, "pdf": False},
        model="gpt-4o-mini",  # Use faster model for demo
        tone="objective",
        verbose=True
    )
    
    runner.print_results_summary(result)
    return result


async def example_climate_research():
    """Example: Research on climate change"""
    print("🌍 Starting Climate Research Example")
    print("="*60)
    
    task_config = TaskConfig(
        query="气候变化对全球经济的影响及应对策略",
        max_sections=4,
        publish_formats={"markdown": True, "pdf": False},
        follow_guidelines=True,
        guidelines=[
            "使用客观、科学的语言",
            "包含具体的数据和案例",
            "提供可行的解决方案建议"
        ],
        model="gpt-4o-mini",
        tone=Tone.ANALYTICAL,
        verbose=True
    )
    
    runner = ResearchRunner()
    result = await runner.run_research_from_config(task_config)
    
    runner.print_results_summary(result)
    return result


async def example_tech_research():
    """Example: Research on technology trends"""
    print("💻 Starting Technology Research Example")
    print("="*60)
    
    runner = ResearchRunner()
    
    result = await runner.run_research_from_query(
        query="区块链技术在金融科技领域的创新应用",
        max_sections=3,
        publish_formats={"markdown": True},
        model="gpt-4o-mini",
        tone="informative",
        verbose=True
    )
    
    runner.print_results_summary(result)
    return result


async def run_examples():
    """Run all examples"""
    examples = [
        ("AI Research", example_ai_research),
        ("Climate Research", example_climate_research),
        ("Technology Research", example_tech_research),
    ]
    
    print("🚀 GPT Researcher LangGraph Examples")
    print("="*80)
    print("This script will run several research examples to demonstrate the system.")
    print("Each example will generate a research report in the ./outputs directory.")
    print("="*80)
    
    # Check if user wants to continue
    try:
        response = input("\nDo you want to continue? (y/N): ").strip().lower()
        if response not in ['y', 'yes']:
            print("Exiting...")
            return
    except KeyboardInterrupt:
        print("\nExiting...")
        return
    
    results = []
    
    for example_name, example_func in examples:
        print(f"\n{'='*20} {example_name} {'='*20}")
        
        try:
            result = await example_func()
            results.append((example_name, result))
            
            if result.get('status') == 'completed':
                print(f"✅ {example_name} completed successfully")
            else:
                print(f"❌ {example_name} failed")
                
        except KeyboardInterrupt:
            print(f"\n⏹️  {example_name} interrupted by user")
            break
        except Exception as e:
            print(f"❌ {example_name} failed with error: {str(e)}")
            results.append((example_name, {"status": "failed", "error": str(e)}))
    
    # Print final summary
    print("\n" + "="*80)
    print("EXAMPLES SUMMARY")
    print("="*80)
    
    successful = 0
    for example_name, result in results:
        status = result.get('status', 'unknown')
        if status == 'completed':
            successful += 1
            cost = result.get('total_cost', 0)
            print(f"✅ {example_name}: SUCCESS (Cost: ${cost:.4f})")
        else:
            error = result.get('error', 'Unknown error')
            print(f"❌ {example_name}: FAILED ({error})")
    
    print(f"\nTotal: {successful}/{len(results)} examples completed successfully")
    
    if successful > 0:
        print(f"\n📁 Check the ./outputs directory for generated reports")
        print(f"📋 Check the ./logs directory for detailed logs")


async def quick_test():
    """Quick test with a simple query"""
    print("⚡ Quick Test")
    print("="*40)
    
    runner = ResearchRunner()
    
    result = await runner.run_research_from_query(
        query="什么是机器学习？",
        max_sections=2,
        publish_formats={"markdown": True},
        model="gpt-4o-mini",
        verbose=True
    )
    
    runner.print_results_summary(result)
    return result


if __name__ == "__main__":
    print("GPT Researcher LangGraph - Example Runner")
    print("Choose an option:")
    print("1. Run quick test")
    print("2. Run all examples")
    print("3. Exit")
    
    try:
        choice = input("\nEnter your choice (1-3): ").strip()
        
        if choice == "1":
            asyncio.run(quick_test())
        elif choice == "2":
            asyncio.run(run_examples())
        elif choice == "3":
            print("Goodbye!")
        else:
            print("Invalid choice. Exiting...")
            
    except KeyboardInterrupt:
        print("\nGoodbye!")
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)

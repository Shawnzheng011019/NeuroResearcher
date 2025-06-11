#!/usr/bin/env python3
"""
Quick start script for the 8-agent research pipeline
"""

import asyncio
import sys
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from config import TaskConfig, Tone
from main import ResearchRunner


async def quick_demo():
    """Quick demonstration of the 8-agent pipeline"""
    print("🚀 8-Agent Research Pipeline Quick Demo")
    print("="*50)
    
    # Simple research without human feedback
    print("\n1. Running simple research (no human feedback)...")
    
    runner = ResearchRunner()
    
    result = await runner.run_research_from_query(
        query="什么是大语言模型？",
        max_sections=2,
        publish_formats={"markdown": True},
        model="gpt-4o-mini",
        tone="objective",
        verbose=False
    )
    
    print(f"Status: {result.get('status', 'unknown')}")
    
    if result.get('status') == 'completed':
        final_state = result.get('final_state', {})
        agent_outputs = final_state.get('agent_outputs', {})
        
        print(f"✅ Research completed successfully!")
        print(f"   - Active agents: {len(agent_outputs)}")
        print(f"   - Total cost: ${result.get('total_cost', 0):.4f}")
        print(f"   - Report length: {len(final_state.get('report', ''))} characters")
        
        # Show which agents participated
        print("   - Participating agents:")
        for agent_name in agent_outputs.keys():
            print(f"     • {agent_name.capitalize()}Agent")
        
        # Show published files
        publisher_output = agent_outputs.get('publisher', {})
        if publisher_output:
            published_files = publisher_output.get('published_files', {})
            for format_type, file_path in published_files.items():
                if not file_path.startswith("Error:"):
                    print(f"   - Output: {file_path}")
    else:
        print(f"❌ Research failed: {result.get('error', 'Unknown error')}")


async def interactive_demo():
    """Interactive demonstration with user input"""
    print("\n🎯 Interactive 8-Agent Research Demo")
    print("="*50)
    
    try:
        # Get user input
        query = input("Enter your research question: ").strip()
        if not query:
            query = "人工智能的未来发展趋势"
            print(f"Using default query: {query}")
        
        # Ask about human feedback
        human_feedback = input("Enable human feedback? (y/N): ").strip().lower()
        include_human = human_feedback in ['y', 'yes']
        
        # Ask about sections
        try:
            sections = int(input("Number of sections (1-5, default 3): ").strip() or "3")
            sections = max(1, min(5, sections))
        except ValueError:
            sections = 3
        
        print(f"\nStarting research with:")
        print(f"  - Query: {query}")
        print(f"  - Human feedback: {include_human}")
        print(f"  - Sections: {sections}")
        print(f"  - Model: gpt-4o-mini")
        
        # Create task configuration
        task_config = TaskConfig(
            query=query,
            max_sections=sections,
            publish_formats={"markdown": True, "pdf": False},
            include_human_feedback=include_human,
            model="gpt-4o-mini",
            tone=Tone.OBJECTIVE,
            verbose=True
        )
        
        # Run research
        runner = ResearchRunner()
        result = await runner.run_research_from_config(task_config)
        
        # Show results
        runner.print_results_summary(result)
        
    except KeyboardInterrupt:
        print("\n\nDemo interrupted by user. Goodbye!")
    except Exception as e:
        print(f"\nDemo failed: {str(e)}")


async def benchmark_demo():
    """Benchmark demonstration showing pipeline performance"""
    print("\n📊 8-Agent Pipeline Benchmark Demo")
    print("="*50)
    
    queries = [
        "什么是机器学习？",
        "区块链技术的应用",
        "气候变化的影响"
    ]
    
    results = []
    
    for i, query in enumerate(queries, 1):
        print(f"\n{i}. Benchmarking: {query}")
        
        runner = ResearchRunner()
        
        import time
        start_time = time.time()
        
        result = await runner.run_research_from_query(
            query=query,
            max_sections=2,
            publish_formats={"markdown": True},
            model="gpt-4o-mini",
            verbose=False
        )
        
        end_time = time.time()
        duration = end_time - start_time
        
        status = result.get('status', 'unknown')
        cost = result.get('total_cost', 0)
        
        results.append({
            'query': query,
            'status': status,
            'duration': duration,
            'cost': cost
        })
        
        print(f"   Status: {status}")
        print(f"   Duration: {duration:.2f}s")
        print(f"   Cost: ${cost:.4f}")
    
    # Summary
    print(f"\n📈 Benchmark Summary:")
    successful = sum(1 for r in results if r['status'] == 'completed')
    total_time = sum(r['duration'] for r in results)
    total_cost = sum(r['cost'] for r in results)
    
    print(f"   - Success rate: {successful}/{len(results)} ({successful/len(results)*100:.1f}%)")
    print(f"   - Total time: {total_time:.2f}s")
    print(f"   - Average time: {total_time/len(results):.2f}s")
    print(f"   - Total cost: ${total_cost:.4f}")
    print(f"   - Average cost: ${total_cost/len(results):.4f}")


def main():
    """Main function with demo options"""
    print("🤖 8-Agent Research Pipeline")
    print("Choose a demo option:")
    print("1. Quick Demo (automated)")
    print("2. Interactive Demo (with user input)")
    print("3. Benchmark Demo (performance test)")
    print("4. Exit")
    
    try:
        choice = input("\nEnter your choice (1-4): ").strip()
        
        if choice == "1":
            asyncio.run(quick_demo())
        elif choice == "2":
            asyncio.run(interactive_demo())
        elif choice == "3":
            asyncio.run(benchmark_demo())
        elif choice == "4":
            print("Goodbye!")
        else:
            print("Invalid choice. Please run the script again.")
            
    except KeyboardInterrupt:
        print("\nGoodbye!")
    except Exception as e:
        print(f"Error: {str(e)}")


if __name__ == "__main__":
    main()

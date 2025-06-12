import asyncio
import logging
import os
import sys
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
import argparse
import json

from config import get_config, get_task_config, TaskConfig, Tone
from graph import create_research_workflow
from state import ResearchState

# Load environment variables
load_dotenv()

# Configure logging
def setup_logging(verbose: bool = True):
    log_level = logging.INFO if verbose else logging.WARNING
    
    # Create logs directory
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    
    # Configure logging
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(logs_dir / 'research.log'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Suppress verbose third-party logging
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('openai').setLevel(logging.WARNING)
    logging.getLogger('anthropic').setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


class ResearchRunner:
    def __init__(self, config_path: str = None):
        self.config = get_config()
        self.workflow = create_research_workflow(self.config)
    
    async def run_research_from_query(self, query: str, **kwargs) -> dict:
        logger.info(f"Starting research for query: {query}")
        
        # Create task configuration
        task_config = get_task_config(query, **kwargs)
        
        # Run research workflow
        result = await self.workflow.run_research(task_config)
        
        return result
    
    async def run_research_from_config(self, task_config: TaskConfig) -> dict:
        logger.info(f"Starting research from configuration: {task_config.query}")
        
        # Run research workflow
        result = await self.workflow.run_research(task_config)
        
        return result
    
    async def run_research_from_file(self, config_file: str) -> dict:
        logger.info(f"Loading research configuration from: {config_file}")
        
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            # Create task configuration from file
            task_config = TaskConfig(**config_data)
            
            # Run research
            result = await self.run_research_from_config(task_config)
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to load configuration from {config_file}: {str(e)}")
            raise
    
    def print_results_summary(self, result: dict):
        print("\n" + "="*80)
        print("8-AGENT RESEARCH PIPELINE RESULTS")
        print("="*80)

        status = result.get("status", "unknown")
        print(f"Status: {status.upper()}")

        if status == "completed":
            final_state = result.get("final_state", {})

            # Get task config - it's a TaskConfig object, not a dict
            task = final_state.get('task')
            query = task.query if task else 'N/A'

            print(f"Query: {query}")
            print(f"Title: {final_state.get('title', 'N/A')}")
            print(f"Sections: {len(final_state.get('completed_sections', []))}")
            print(f"Sources: {len(final_state.get('sources', []))}")
            print(f"Total Cost: ${result.get('total_cost', 0):.4f}")
            print(f"Revisions: {final_state.get('revision_count', 0)}")
            print(f"Workflow Status: {final_state.get('workflow_status', 'Unknown')}")

            # Show agent performance
            agent_outputs = final_state.get("agent_outputs", {})
            print(f"\nAgent Performance:")
            print(f"  - Active Agents: {len(agent_outputs)}")

            # Show orchestrator metrics if available
            orchestrator_output = agent_outputs.get("orchestrator", {})
            if orchestrator_output:
                task_id = orchestrator_output.get("task_id", "N/A")
                print(f"  - Task ID: {task_id}")

                performance_metrics = orchestrator_output.get("performance_metrics", {})
                if performance_metrics:
                    completed_agents = performance_metrics.get("completed_agents", 0)
                    failed_agents = performance_metrics.get("failed_agents", 0)
                    print(f"  - Completed Agents: {completed_agents}")
                    print(f"  - Failed Agents: {failed_agents}")

            # Show human feedback if any
            human_output = agent_outputs.get("human", {})
            if human_output:
                feedback_provided = human_output.get("feedback_requested", False)
                print(f"  - Human Feedback: {'Provided' if feedback_provided else 'Not Requested'}")

            # Show published files
            publisher_output = agent_outputs.get("publisher", {})
            if publisher_output:
                published_files = publisher_output.get("published_files", {})
                print("\nPublished Files:")
                for format_type, file_path in published_files.items():
                    if not file_path.startswith("Error:"):
                        print(f"  - {format_type.upper()}: {file_path}")
                    else:
                        print(f"  - {format_type.upper()}: FAILED - {file_path}")

            # Show errors if any
            errors = result.get("errors", [])
            if errors:
                print(f"\nErrors ({len(errors)}):")
                for error in errors[:5]:  # Show first 5 errors
                    print(f"  - {error}")
                if len(errors) > 5:
                    print(f"  ... and {len(errors) - 5} more errors")

        elif status == "failed":
            print(f"Error: {result.get('error', 'Unknown error')}")

        print("="*80)


async def main():
    parser = argparse.ArgumentParser(description="GPT Researcher - LangGraph Implementation")
    parser.add_argument("query", nargs="?", help="Research query")
    parser.add_argument("--config", "-c", help="Configuration file path")
    parser.add_argument("--output", "-o", help="Output directory", default="./outputs")
    parser.add_argument("--format", "-f", nargs="+", choices=["markdown", "pdf", "docx"], 
                       default=["markdown"], help="Output formats")
    parser.add_argument("--max-sections", "-s", type=int, default=5, help="Maximum number of sections")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")
    parser.add_argument("--model", "-m", default="gpt-4o", help="LLM model to use")
    parser.add_argument("--tone", "-t", default="objective", help="Writing tone")
    parser.add_argument("--template", default="none",
                       help="Template name to use (use 'none' for free LLM generation)")
    parser.add_argument("--language", "-l", default="en",
                       choices=["en", "zh-cn", "zh-tw", "ja", "ko"],
                       help="Output language")
    parser.add_argument("--citation-style", default="ieee",
                       choices=["apa", "mla", "chicago", "ieee", "harvard"],
                       help="Citation style")
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.verbose)
    
    # Validate inputs
    if not args.query and not args.config:
        parser.error("Either provide a query or a configuration file")
    
    try:
        # Initialize research runner
        runner = ResearchRunner()
        
        # Run research based on input method
        if args.config:
            result = await runner.run_research_from_file(args.config)
        else:
            # Prepare publish formats
            publish_formats = {fmt: True for fmt in args.format}
            
            # Run research from command line arguments
            result = await runner.run_research_from_query(
                query=args.query,
                max_sections=args.max_sections,
                publish_formats=publish_formats,
                model=args.model,
                tone=args.tone,
                verbose=args.verbose,
                template_name=args.template,
                language=args.language,
                citation_style=args.citation_style
            )
        
        # Print results summary
        runner.print_results_summary(result)
        
        # Exit with appropriate code
        if result.get("status") == "completed":
            logger.info("Research completed successfully")
            sys.exit(0)
        else:
            logger.error("Research failed")
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.info("Research interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        sys.exit(1)


# Example usage functions
async def example_basic_research():
    """Example of basic research usage"""
    runner = ResearchRunner()
    
    result = await runner.run_research_from_query(
        query="What are the latest developments in artificial intelligence?",
        max_sections=3,
        publish_formats={"markdown": True, "pdf": True}
    )
    
    runner.print_results_summary(result)
    return result


async def example_advanced_research():
    """Example of advanced research with custom configuration"""
    task_config = TaskConfig(
        query="How is climate change affecting global food security?",
        max_sections=5,
        publish_formats={"markdown": True, "pdf": True, "docx": True},
        follow_guidelines=True,
        guidelines=[
            "Use academic writing style",
            "Include statistical data where available",
            "Cite all sources properly"
        ],
        model="gpt-4o",
        tone=Tone.ANALYTICAL,
        verbose=True
    )
    
    runner = ResearchRunner()
    result = await runner.run_research_from_config(task_config)
    
    runner.print_results_summary(result)
    return result


if __name__ == "__main__":
    asyncio.run(main())


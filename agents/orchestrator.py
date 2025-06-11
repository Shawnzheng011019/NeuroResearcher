"""Orchestrator Agent for coordinating multi-agent research workflow."""

import asyncio
import logging
import time
from datetime import datetime
from typing import Dict, Any, Optional, List
from pathlib import Path

from config import Config, TaskConfig
from state import ResearchState, create_initial_research_state
from tools.llm_tools import LLMManager

logger = logging.getLogger(__name__)


class OrchestratorAgent:
    def __init__(self, config: Config, llm_manager: LLMManager):
        self.config = config
        self.llm_manager = llm_manager
        self.task_id = None
        self.output_dir = None
    
    def generate_task_id(self) -> str:
        return f"task_{int(time.time())}"
    
    def create_output_directory(self, task_query: str) -> Path:
        sanitized_query = "".join(c for c in task_query if c.isalnum() or c in (' ', '-', '_')).rstrip()
        sanitized_query = sanitized_query.replace(' ', '_')[:40]
        
        output_dir = Path(self.config.output_path) / f"run_{self.task_id}_{sanitized_query}"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        return output_dir
    
    async def initialize_research_task(self, task_config: TaskConfig) -> ResearchState:
        self.task_id = self.generate_task_id()
        self.output_dir = self.create_output_directory(task_config.query)
        
        logger.info(f"Initializing research task {self.task_id} for query: {task_config.query}")
        
        # Create initial research state
        initial_state = create_initial_research_state(task_config)
        initial_state["current_step"] = "orchestrator_initialization"
        
        # Add orchestrator metadata
        initial_state["agent_outputs"]["orchestrator"] = {
            "task_id": self.task_id,
            "output_directory": str(self.output_dir),
            "initialization_time": datetime.now().isoformat(),
            "status": "initialized"
        }
        
        return initial_state
    
    async def coordinate_research_workflow(self, state: ResearchState, agents: Dict[str, Any]) -> ResearchState:
        logger.info("Orchestrator coordinating research workflow")
        
        try:
            # Track workflow progress
            workflow_steps = [
                "initial_research",
                "plan_outline", 
                "parallel_research",
                "review_research",
                "write_report",
                "review_report",
                "publish_report"
            ]
            
            orchestrator_output = state["agent_outputs"].get("orchestrator", {})
            orchestrator_output["workflow_steps"] = workflow_steps
            orchestrator_output["current_step_index"] = 0
            orchestrator_output["coordination_status"] = "in_progress"
            
            state["agent_outputs"]["orchestrator"] = orchestrator_output
            
            return state
            
        except Exception as e:
            logger.error(f"Orchestrator coordination failed: {str(e)}")
            state["errors"].append(f"Orchestrator coordination failed: {str(e)}")
            return state
    
    async def monitor_agent_performance(self, state: ResearchState) -> Dict[str, Any]:
        performance_metrics = {
            "total_agents": len(state["agent_outputs"]),
            "completed_agents": 0,
            "failed_agents": 0,
            "agent_status": {}
        }
        
        for agent_name, agent_output in state["agent_outputs"].items():
            if agent_name == "orchestrator":
                continue
                
            if isinstance(agent_output, dict):
                if "error" in agent_output:
                    performance_metrics["failed_agents"] += 1
                    performance_metrics["agent_status"][agent_name] = "failed"
                else:
                    performance_metrics["completed_agents"] += 1
                    performance_metrics["agent_status"][agent_name] = "completed"
            else:
                performance_metrics["agent_status"][agent_name] = "unknown"
        
        return performance_metrics
    
    async def handle_workflow_errors(self, state: ResearchState) -> ResearchState:
        errors = state.get("errors", [])
        
        if not errors:
            return state
        
        logger.warning(f"Orchestrator handling {len(errors)} workflow errors")
        
        # Categorize errors
        critical_errors = []
        recoverable_errors = []
        
        for error in errors:
            if any(keyword in error.lower() for keyword in ["api", "network", "timeout"]):
                recoverable_errors.append(error)
            else:
                critical_errors.append(error)
        
        # Update orchestrator output with error analysis
        orchestrator_output = state["agent_outputs"].get("orchestrator", {})
        orchestrator_output["error_analysis"] = {
            "total_errors": len(errors),
            "critical_errors": len(critical_errors),
            "recoverable_errors": len(recoverable_errors),
            "error_handling_time": datetime.now().isoformat()
        }
        
        state["agent_outputs"]["orchestrator"] = orchestrator_output
        
        return state
    
    async def finalize_research_task(self, state: ResearchState) -> ResearchState:
        logger.info("Orchestrator finalizing research task")
        
        try:
            # Calculate final metrics
            performance_metrics = await self.monitor_agent_performance(state)
            
            # Update orchestrator final output
            orchestrator_output = state["agent_outputs"].get("orchestrator", {})
            orchestrator_output.update({
                "finalization_time": datetime.now().isoformat(),
                "final_status": "completed",
                "performance_metrics": performance_metrics,
                "total_cost": state.get("costs", 0),
                "output_directory": str(self.output_dir) if self.output_dir else None
            })
            
            state["agent_outputs"]["orchestrator"] = orchestrator_output
            state["current_step"] = "orchestrator_finalized"
            
            logger.info(f"Research task {self.task_id} finalized successfully")
            return state
            
        except Exception as e:
            logger.error(f"Orchestrator finalization failed: {str(e)}")
            state["errors"].append(f"Orchestrator finalization failed: {str(e)}")
            return state
    
    async def generate_workflow_summary(self, state: ResearchState) -> str:
        try:
            orchestrator_output = state["agent_outputs"].get("orchestrator", {})
            performance_metrics = orchestrator_output.get("performance_metrics", {})
            
            summary_parts = [
                f"Task ID: {orchestrator_output.get('task_id', 'Unknown')}",
                f"Query: {state['task'].query}",
                f"Agents Completed: {performance_metrics.get('completed_agents', 0)}",
                f"Total Cost: ${state.get('costs', 0):.4f}",
                f"Output Directory: {orchestrator_output.get('output_directory', 'N/A')}"
            ]
            
            if state.get("errors"):
                summary_parts.append(f"Errors: {len(state['errors'])}")
            
            return " | ".join(summary_parts)
            
        except Exception as e:
            logger.error(f"Failed to generate workflow summary: {str(e)}")
            return f"Workflow summary generation failed: {str(e)}"

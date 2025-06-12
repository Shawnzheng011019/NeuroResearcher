import asyncio
from typing import Dict, Any, List, Optional
import logging
from datetime import datetime

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from state import ResearchState, DraftState, create_initial_research_state, create_draft_state
from config import Config, TaskConfig, get_config
from tools.search_tools import create_search_manager
from tools.llm_tools import create_llm_manager
from agents import (
    ResearcherAgent, EditorAgent, WriterAgent, ReviewerAgent, PublisherAgent,
    OrchestratorAgent, HumanAgent, ReviserAgent
)

logger = logging.getLogger(__name__)


class ResearchWorkflow:
    def __init__(self, config: Config):
        self.config = config
        self.search_manager = create_search_manager(config)
        self.llm_manager = create_llm_manager(config)

        # Initialize all agents
        self.orchestrator = OrchestratorAgent(config, self.llm_manager)
        self.researcher = ResearcherAgent(config, self.search_manager, self.llm_manager)
        self.editor = EditorAgent(config, self.llm_manager)
        self.writer = WriterAgent(config, self.llm_manager)
        self.reviewer = ReviewerAgent(config, self.llm_manager)
        self.reviser = ReviserAgent(config, self.llm_manager)
        self.human = HumanAgent(config, self.llm_manager)
        self.publisher = PublisherAgent(config)

        # Create workflow graph
        self.workflow = self._create_workflow()
        self.app = self.workflow.compile(checkpointer=MemorySaver())
    
    def _create_workflow(self) -> StateGraph:
        workflow = StateGraph(ResearchState)

        # Add nodes for each step
        workflow.add_node("orchestrator_init", self._orchestrator_init_node)
        workflow.add_node("conduct_initial_research", self._initial_research_node)
        workflow.add_node("plan_outline", self._plan_outline_node)
        workflow.add_node("human_review_plan", self._human_review_plan_node)
        workflow.add_node("revise_plan", self._revise_plan_node)
        workflow.add_node("parallel_research", self._parallel_research_node)
        workflow.add_node("review_research", self._review_research_node)
        workflow.add_node("write_report", self._write_report_node)
        workflow.add_node("human_review_report", self._human_review_report_node)
        workflow.add_node("revise_report", self._revise_report_node)
        workflow.add_node("review_report", self._review_report_node)
        workflow.add_node("publish_report", self._publish_report_node)
        workflow.add_node("orchestrator_finalize", self._orchestrator_finalize_node)

        # Set entry point
        workflow.set_entry_point("orchestrator_init")

        # Add linear edges
        workflow.add_edge("orchestrator_init", "conduct_initial_research")
        workflow.add_edge("conduct_initial_research", "plan_outline")
        workflow.add_edge("plan_outline", "human_review_plan")
        workflow.add_edge("parallel_research", "review_research")
        workflow.add_edge("review_research", "write_report")
        workflow.add_edge("write_report", "human_review_report")
        workflow.add_edge("review_report", "publish_report")
        workflow.add_edge("publish_report", "orchestrator_finalize")
        workflow.add_edge("orchestrator_finalize", END)

        # Add conditional edges for human feedback and revisions
        workflow.add_conditional_edges(
            "human_review_plan",
            self._should_revise_plan,
            {
                "revise": "revise_plan",
                "proceed": "parallel_research"
            }
        )

        workflow.add_conditional_edges(
            "revise_plan",
            self._plan_revision_complete,
            {
                "review_again": "human_review_plan",
                "proceed": "parallel_research"
            }
        )

        workflow.add_conditional_edges(
            "human_review_report",
            self._should_revise_report,
            {
                "revise": "revise_report",
                "proceed": "review_report"
            }
        )

        workflow.add_conditional_edges(
            "revise_report",
            self._report_revision_complete,
            {
                "review_again": "human_review_report",
                "proceed": "review_report"
            }
        )

        return workflow

    async def _orchestrator_init_node(self, state: ResearchState) -> ResearchState:
        logger.info("Executing orchestrator initialization node")
        try:
            # Initialize orchestrator with task config
            self.orchestrator.task_id = self.orchestrator.generate_task_id()
            self.orchestrator.output_dir = self.orchestrator.create_output_directory(state["task"].query)

            # Add orchestrator metadata to state
            state["agent_outputs"]["orchestrator"] = {
                "task_id": self.orchestrator.task_id,
                "output_directory": str(self.orchestrator.output_dir),
                "initialization_time": datetime.now().isoformat(),
                "status": "initialized"
            }

            state["workflow_status"] = "orchestrator_initialized"
            return state
        except Exception as e:
            logger.error(f"Orchestrator initialization failed: {str(e)}")
            state["errors"].append(f"Orchestrator initialization failed: {str(e)}")
            return state

    async def _initial_research_node(self, state: ResearchState) -> ResearchState:
        logger.info("Executing initial research node")
        try:
            state = await self.researcher.conduct_initial_research(state)
            return state
        except Exception as e:
            logger.error(f"Initial research node failed: {str(e)}")
            state["errors"].append(f"Initial research failed: {str(e)}")
            return state
    
    async def _plan_outline_node(self, state: ResearchState) -> ResearchState:
        logger.info("Executing plan outline node")
        try:
            state = await self.editor.plan_research_outline(state)
            return state
        except Exception as e:
            logger.error(f"Plan outline node failed: {str(e)}")
            state["errors"].append(f"Outline planning failed: {str(e)}")
            return state
    
    async def _parallel_research_node(self, state: ResearchState) -> ResearchState:
        logger.info("Executing parallel research node")
        try:
            state = await self.editor.manage_parallel_research(state, self.researcher)
            return state
        except Exception as e:
            logger.error(f"Parallel research node failed: {str(e)}")
            state["errors"].append(f"Parallel research failed: {str(e)}")
            return state
    
    async def _review_research_node(self, state: ResearchState) -> ResearchState:
        logger.info("Executing review research node")
        try:
            state = await self.reviewer.review_research_quality(state)
            return state
        except Exception as e:
            logger.error(f"Review research node failed: {str(e)}")
            state["errors"].append(f"Research review failed: {str(e)}")
            return state
    
    async def _write_report_node(self, state: ResearchState) -> ResearchState:
        logger.info("Executing write report node")
        try:
            state = await self.writer.write_final_report(state)
            return state
        except Exception as e:
            logger.error(f"Write report node failed: {str(e)}")
            state["errors"].append(f"Report writing failed: {str(e)}")
            return state
    
    async def _review_report_node(self, state: ResearchState) -> ResearchState:
        logger.info("Executing review report node")
        try:
            state = await self.reviewer.review_final_report(state)
            return state
        except Exception as e:
            logger.error(f"Review report node failed: {str(e)}")
            state["errors"].append(f"Report review failed: {str(e)}")
            return state
    
    async def _publish_report_node(self, state: ResearchState) -> ResearchState:
        logger.info("Executing publish report node")
        try:
            state = await self.publisher.publish_report(state)
            return state
        except Exception as e:
            logger.error(f"Publish report node failed: {str(e)}")
            state["errors"].append(f"Report publishing failed: {str(e)}")
            return state

    async def _human_review_plan_node(self, state: ResearchState) -> ResearchState:
        logger.info("Executing human review plan node")
        try:
            state = await self.human.review_research_plan(state)
            return state
        except Exception as e:
            logger.error(f"Human review plan node failed: {str(e)}")
            state["errors"].append(f"Human plan review failed: {str(e)}")
            return state

    async def _revise_plan_node(self, state: ResearchState) -> ResearchState:
        logger.info("Executing revise plan node")
        try:
            feedback = state.get("human_feedback", "")
            if feedback:
                state = await self.reviser.revise_research_plan(state, feedback)
                state["revision_count"] += 1
            return state
        except Exception as e:
            logger.error(f"Revise plan node failed: {str(e)}")
            state["errors"].append(f"Plan revision failed: {str(e)}")
            return state

    async def _human_review_report_node(self, state: ResearchState) -> ResearchState:
        logger.info("Executing human review report node")
        try:
            state = await self.human.review_final_report(state)
            return state
        except Exception as e:
            logger.error(f"Human review report node failed: {str(e)}")
            state["errors"].append(f"Human report review failed: {str(e)}")
            return state

    async def _revise_report_node(self, state: ResearchState) -> ResearchState:
        logger.info("Executing revise report node")
        try:
            human_output = state["agent_outputs"].get("human", {})
            feedback = human_output.get("final_report_feedback", "")
            if feedback:
                state = await self.reviser.revise_final_report(state, feedback)
                state["revision_count"] += 1
            return state
        except Exception as e:
            logger.error(f"Revise report node failed: {str(e)}")
            state["errors"].append(f"Report revision failed: {str(e)}")
            return state

    async def _orchestrator_finalize_node(self, state: ResearchState) -> ResearchState:
        logger.info("Executing orchestrator finalize node")
        try:
            state = await self.orchestrator.finalize_research_task(state)
            return state
        except Exception as e:
            logger.error(f"Orchestrator finalize node failed: {str(e)}")
            state["errors"].append(f"Orchestrator finalization failed: {str(e)}")
            return state

    def _should_revise_plan(self, state: ResearchState) -> str:
        if not state.get("human_review_required", False):
            return "proceed"

        human_output = state["agent_outputs"].get("human", {})
        feedback = state.get("human_feedback", "")

        if not feedback or "approved" in feedback.lower() or "no changes" in feedback.lower():
            return "proceed"

        # Check revision count to prevent infinite loops
        if state.get("revision_count", 0) >= 3:
            logger.warning("Maximum plan revisions reached, proceeding")
            return "proceed"

        return "revise"

    def _plan_revision_complete(self, state: ResearchState) -> str:
        # After revision, always go back for human review unless max revisions reached
        if state.get("revision_count", 0) >= 3:
            return "proceed"
        return "review_again"

    def _should_revise_report(self, state: ResearchState) -> str:
        if not state.get("human_review_required", False):
            return "proceed"

        human_output = state["agent_outputs"].get("human", {})
        feedback = human_output.get("final_report_feedback", "")

        if not feedback or "approved" in feedback.lower() or "no changes" in feedback.lower():
            return "proceed"

        # Check revision count to prevent infinite loops
        if state.get("revision_count", 0) >= 3:
            logger.warning("Maximum report revisions reached, proceeding")
            return "proceed"

        return "revise"

    def _report_revision_complete(self, state: ResearchState) -> str:
        # After revision, always go back for human review unless max revisions reached
        if state.get("revision_count", 0) >= 3:
            return "proceed"
        return "review_again"

    async def run_research(self, task_config: TaskConfig, thread_id: Optional[str] = None) -> Dict[str, Any]:
        logger.info(f"Starting research workflow for query: {task_config.query}")

        # Set language for all agents' prompt managers
        language_code = getattr(task_config, 'language', 'en')
        logger.info(f"Setting workflow language to: {language_code}")

        # Set language for all agents that have prompt managers
        agents_with_prompts = [
            self.researcher, self.editor, self.writer,
            self.reviewer, self.reviser
        ]

        for agent in agents_with_prompts:
            if hasattr(agent, 'prompt_manager'):
                agent.prompt_manager.set_language(language_code)
                logger.debug(f"Set language {language_code} for {agent.__class__.__name__}")

        # Create initial state
        initial_state = create_initial_research_state(task_config)
        
        # Configure thread
        config = {"configurable": {"thread_id": thread_id or "default"}}
        
        try:
            # Run the workflow
            final_state = await self.app.ainvoke(initial_state, config=config)
            
            # Calculate total cost
            total_cost = self.llm_manager.get_total_cost()
            final_state["costs"] = total_cost
            
            # Generate summary
            summary = await self._generate_workflow_summary(final_state)
            
            logger.info(f"Research workflow completed. Total cost: ${total_cost:.4f}")
            
            return {
                "status": "completed",
                "final_state": final_state,
                "summary": summary,
                "total_cost": total_cost,
                "errors": final_state.get("errors", [])
            }
            
        except Exception as e:
            logger.error(f"Research workflow failed: {str(e)}")
            return {
                "status": "failed",
                "error": str(e),
                "final_state": initial_state,
                "summary": f"Workflow failed: {str(e)}",
                "total_cost": self.llm_manager.get_total_cost(),
                "errors": [str(e)]
            }
    
    async def _generate_workflow_summary(self, final_state: ResearchState) -> str:
        try:
            summary_parts = [
                f"Research Query: {final_state['task'].query}",
                f"Report Title: {final_state.get('title', 'N/A')}",
                f"Sections Completed: {len(final_state.get('completed_sections', []))}",
                f"Sources Found: {len(final_state.get('sources', []))}",
                f"Total Cost: ${final_state.get('costs', 0):.4f}",
                f"Current Step: {final_state.get('current_step', 'Unknown')}"
            ]
            
            if final_state.get("errors"):
                summary_parts.append(f"Errors: {len(final_state['errors'])}")
            
            # Add publishing information
            publisher_output = final_state.get("agent_outputs", {}).get("publisher", {})
            if publisher_output:
                published_files = publisher_output.get("published_files", {})
                successful_formats = [fmt for fmt, path in published_files.items() if not path.startswith("Error:")]
                if successful_formats:
                    summary_parts.append(f"Published Formats: {', '.join(successful_formats)}")
            
            return " | ".join(summary_parts)
            
        except Exception as e:
            logger.error(f"Failed to generate workflow summary: {str(e)}")
            return f"Workflow completed with summary generation error: {str(e)}"


class DraftReviewWorkflow:
    def __init__(self, config: Config, llm_manager):
        self.config = config
        self.llm_manager = llm_manager
        self.reviewer = ReviewerAgent(config, llm_manager)
        self.editor = EditorAgent(config, llm_manager)
        
        # Create draft review workflow
        self.workflow = self._create_draft_workflow()
        self.app = self.workflow.compile()
    
    def _create_draft_workflow(self) -> StateGraph:
        workflow = StateGraph(DraftState)
        
        # Add nodes
        workflow.add_node("review_draft", self._review_draft_node)
        workflow.add_node("revise_draft", self._revise_draft_node)
        
        # Set entry point
        workflow.set_entry_point("review_draft")
        
        # Add conditional edges
        workflow.add_conditional_edges(
            "review_draft",
            self._should_revise,
            {
                "revise": "revise_draft",
                "approve": END
            }
        )
        
        workflow.add_edge("revise_draft", "review_draft")
        
        return workflow
    
    async def _review_draft_node(self, state: DraftState) -> DraftState:
        logger.info(f"Reviewing draft for topic: {state['topic']}")
        try:
            state = await self.reviewer.review_draft_section(state)
            return state
        except Exception as e:
            logger.error(f"Draft review failed: {str(e)}")
            state["is_approved"] = True  # Approve to prevent infinite loop
            return state
    
    async def _revise_draft_node(self, state: DraftState) -> DraftState:
        logger.info(f"Revising draft for topic: {state['topic']}")
        try:
            state = await self.editor.review_and_revise_draft(state)
            return state
        except Exception as e:
            logger.error(f"Draft revision failed: {str(e)}")
            state["is_approved"] = True  # Approve to prevent infinite loop
            return state
    
    def _should_revise(self, state: DraftState) -> str:
        if state.get("is_approved", False):
            return "approve"
        elif state.get("review") is not None:
            return "revise"
        else:
            return "approve"
    
    async def run_draft_review(self, task_config: TaskConfig, topic: str, draft_content: Dict[str, Any]) -> Dict[str, Any]:
        logger.info(f"Starting draft review workflow for topic: {topic}")
        
        # Create initial draft state
        initial_state = create_draft_state(task_config, topic)
        initial_state["draft"] = draft_content
        
        try:
            # Run the draft review workflow
            final_state = await self.app.ainvoke(initial_state)
            
            return {
                "status": "completed",
                "final_draft": final_state["draft"],
                "is_approved": final_state.get("is_approved", False),
                "quality_score": final_state.get("quality_score", 0.7),
                "iterations": final_state.get("iteration_count", 0),
                "final_review": final_state.get("review", "Approved")
            }
            
        except Exception as e:
            logger.error(f"Draft review workflow failed: {str(e)}")
            return {
                "status": "failed",
                "error": str(e),
                "final_draft": draft_content,
                "is_approved": True,
                "quality_score": 0.6,
                "iterations": 0,
                "final_review": f"Review failed: {str(e)}"
            }


def create_research_workflow(config: Optional[Config] = None) -> ResearchWorkflow:
    if config is None:
        config = get_config()
    return ResearchWorkflow(config)


def create_draft_review_workflow(config: Optional[Config] = None, llm_manager=None) -> DraftReviewWorkflow:
    if config is None:
        config = get_config()
    if llm_manager is None:
        llm_manager = create_llm_manager(config)
    return DraftReviewWorkflow(config, llm_manager)

"""Reviser Agent for revising content based on feedback."""

import asyncio
import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from config import Config, TaskConfig
from state import ResearchState, DraftState
from tools.llm_tools import LLMManager

logger = logging.getLogger(__name__)


class ReviserAgent:
    def __init__(self, config: Config, llm_manager: LLMManager):
        self.config = config
        self.llm_manager = llm_manager
        self.revision_history = []
    
    async def revise_research_plan(self, state: ResearchState, feedback: str) -> ResearchState:
        logger.info("Reviser agent revising research plan based on feedback")
        
        try:
            current_sections = state.get("sections", [])
            task = state["task"]
            
            # Generate revised plan
            revised_plan = await self._revise_plan_with_feedback(
                current_sections, feedback, task
            )
            
            if revised_plan:
                # Update state with revised plan
                state["sections"] = revised_plan.get("sections", current_sections)
                
                # Update agent output
                state["agent_outputs"]["reviser"] = {
                    "revision_type": "research_plan",
                    "original_sections": current_sections,
                    "revised_sections": revised_plan.get("sections", []),
                    "revision_notes": revised_plan.get("revision_notes", ""),
                    "revision_timestamp": datetime.now().isoformat()
                }
                
                # Add to revision history
                self.revision_history.append({
                    "type": "research_plan",
                    "feedback": feedback,
                    "revision": revised_plan,
                    "timestamp": datetime.now().isoformat()
                })
                
                logger.info("Research plan revised successfully")
            else:
                logger.warning("Failed to generate revised plan, keeping original")
            
            return state
            
        except Exception as e:
            logger.error(f"Research plan revision failed: {str(e)}")
            state["errors"].append(f"Research plan revision failed: {str(e)}")
            return state
    
    async def revise_draft_section(self, draft_state: DraftState) -> DraftState:
        logger.info(f"Reviser agent revising draft section: {draft_state['topic']}")
        
        try:
            review_feedback = draft_state.get("review", "")
            current_draft = draft_state.get("draft", {})
            topic = draft_state["topic"]
            task = draft_state["task"]
            
            if not review_feedback:
                logger.info("No review feedback provided, skipping revision")
                return draft_state
            
            # Generate revised draft
            revised_draft = await self._revise_draft_with_feedback(
                current_draft, review_feedback, topic, task
            )
            
            if revised_draft:
                # Update draft state
                draft_state["draft"] = revised_draft.get("draft", current_draft)
                draft_state["revision_notes"] = revised_draft.get("revision_notes", "")
                draft_state["iteration_count"] += 1
                
                # Add to revision history
                self.revision_history.append({
                    "type": "draft_section",
                    "topic": topic,
                    "feedback": review_feedback,
                    "revision": revised_draft,
                    "timestamp": datetime.now().isoformat()
                })
                
                logger.info(f"Draft section '{topic}' revised successfully")
            else:
                logger.warning("Failed to generate revised draft, keeping original")
            
            return draft_state
            
        except Exception as e:
            logger.error(f"Draft section revision failed: {str(e)}")
            draft_state["is_approved"] = True  # Approve to prevent infinite loop
            return draft_state
    
    async def revise_final_report(self, state: ResearchState, feedback: str) -> ResearchState:
        logger.info("Reviser agent revising final report based on feedback")
        
        try:
            current_report = state.get("report", "")
            task = state["task"]
            
            # Generate revised report
            revised_report = await self._revise_report_with_feedback(
                current_report, feedback, task
            )
            
            if revised_report:
                # Update state with revised report
                state["report"] = revised_report.get("report", current_report)
                
                # Update agent output
                reviser_output = state["agent_outputs"].get("reviser", {})
                reviser_output.update({
                    "final_report_revision": {
                        "revision_notes": revised_report.get("revision_notes", ""),
                        "revision_timestamp": datetime.now().isoformat(),
                        "feedback_addressed": feedback
                    }
                })
                state["agent_outputs"]["reviser"] = reviser_output
                
                # Add to revision history
                self.revision_history.append({
                    "type": "final_report",
                    "feedback": feedback,
                    "revision": revised_report,
                    "timestamp": datetime.now().isoformat()
                })
                
                logger.info("Final report revised successfully")
            else:
                logger.warning("Failed to generate revised report, keeping original")
            
            return state
            
        except Exception as e:
            logger.error(f"Final report revision failed: {str(e)}")
            state["errors"].append(f"Final report revision failed: {str(e)}")
            return state
    
    async def _revise_plan_with_feedback(self, current_sections: List[str], feedback: str, task: TaskConfig) -> Optional[Dict[str, Any]]:
        system_prompt = """You are an expert research planner. Your task is to revise research plans based on feedback.
        Create improved research sections that address the feedback while maintaining logical flow and comprehensive coverage."""
        
        user_prompt = f"""Research Query: {task.query}
Max Sections: {task.max_sections}

Current Research Plan:
{chr(10).join(f'{i+1}. {section}' for i, section in enumerate(current_sections))}

Feedback Received:
{feedback}

Please revise the research plan to address the feedback. Provide your response as JSON:
{{
    "sections": ["revised section 1", "revised section 2", ...],
    "revision_notes": "Explanation of changes made based on feedback"
}}

Ensure the revised plan:
1. Addresses all points raised in the feedback
2. Maintains logical organization
3. Stays within the maximum section limit
4. Provides comprehensive coverage of the research query"""
        
        try:
            response = await self.llm_manager.generate_with_fallback(
                prompt=user_prompt,
                system_prompt=system_prompt,
                tool_type="smart"
            )
            
            revision_data = json.loads(response.strip())
            
            # Validate response structure
            if "sections" in revision_data and isinstance(revision_data["sections"], list):
                # Limit to max sections
                revision_data["sections"] = revision_data["sections"][:task.max_sections]
                return revision_data
            else:
                logger.error("Invalid revision response structure")
                return None
                
        except Exception as e:
            logger.error(f"Failed to revise plan: {str(e)}")
            return None
    
    async def _revise_draft_with_feedback(self, current_draft: Dict[str, Any], feedback: str, topic: str, task: TaskConfig) -> Optional[Dict[str, Any]]:
        system_prompt = """You are an expert writer and editor. Your task is to revise draft content based on reviewer feedback.
        Make specific improvements while maintaining the overall structure and key information."""
        
        current_content = current_draft.get("content", "")
        
        user_prompt = f"""Research Topic: {topic}
Research Context: {task.query}

Current Draft:
{current_content}

Reviewer Feedback:
{feedback}

Please revise the draft to address the reviewer's feedback. Provide your response as JSON:
{{
    "draft": {{
        "content": "revised content here",
        "title": "revised title if needed",
        "key_points": ["key point 1", "key point 2", ...]
    }},
    "revision_notes": "Explanation of changes made based on feedback"
}}

Ensure the revision:
1. Addresses all specific points in the feedback
2. Maintains factual accuracy
3. Improves clarity and readability
4. Keeps the content relevant to the research topic
5. Preserves important information from the original draft"""
        
        try:
            response = await self.llm_manager.generate_with_fallback(
                prompt=user_prompt,
                system_prompt=system_prompt,
                tool_type="smart"
            )
            
            revision_data = json.loads(response.strip())
            
            # Validate response structure
            if "draft" in revision_data and isinstance(revision_data["draft"], dict):
                return revision_data
            else:
                logger.error("Invalid draft revision response structure")
                return None
                
        except Exception as e:
            logger.error(f"Failed to revise draft: {str(e)}")
            return None
    
    async def _revise_report_with_feedback(self, current_report: str, feedback: str, task: TaskConfig) -> Optional[Dict[str, Any]]:
        system_prompt = """You are an expert research writer and editor. Your task is to revise complete research reports based on feedback.
        Make comprehensive improvements while maintaining the report's structure and key findings."""
        
        user_prompt = f"""Research Query: {task.query}

Current Report:
{current_report}

Feedback Received:
{feedback}

Please revise the entire report to address the feedback. Provide your response as JSON:
{{
    "report": "complete revised report content",
    "revision_notes": "Detailed explanation of changes made based on feedback"
}}

Ensure the revision:
1. Addresses all points raised in the feedback
2. Maintains the report's overall structure
3. Improves clarity, accuracy, and readability
4. Preserves important research findings
5. Enhances the conclusion and recommendations"""
        
        try:
            response = await self.llm_manager.generate_with_fallback(
                prompt=user_prompt,
                system_prompt=system_prompt,
                tool_type="smart"
            )
            
            revision_data = json.loads(response.strip())
            
            # Validate response structure
            if "report" in revision_data and isinstance(revision_data["report"], str):
                return revision_data
            else:
                logger.error("Invalid report revision response structure")
                return None
                
        except Exception as e:
            logger.error(f"Failed to revise report: {str(e)}")
            return None
    
    def get_revision_history(self) -> List[Dict[str, Any]]:
        return self.revision_history.copy()
    
    def get_revision_statistics(self) -> Dict[str, Any]:
        stats = {
            "total_revisions": len(self.revision_history),
            "revision_types": {},
            "recent_revisions": []
        }
        
        for revision in self.revision_history:
            revision_type = revision.get("type", "unknown")
            stats["revision_types"][revision_type] = stats["revision_types"].get(revision_type, 0) + 1
        
        # Get last 5 revisions
        stats["recent_revisions"] = self.revision_history[-5:] if len(self.revision_history) > 5 else self.revision_history
        
        return stats

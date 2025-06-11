"""Human Agent for human-in-the-loop feedback and review."""

import asyncio
import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from config import Config, TaskConfig
from state import ResearchState
from tools.llm_tools import LLMManager

logger = logging.getLogger(__name__)


class HumanAgent:
    def __init__(self, config: Config, llm_manager: Optional[LLMManager] = None):
        self.config = config
        self.llm_manager = llm_manager
        self.feedback_history = []
    
    async def review_research_plan(self, state: ResearchState) -> ResearchState:
        logger.info("Human agent reviewing research plan")
        
        try:
            task = state["task"]
            sections = state.get("sections", [])
            
            # Check if human feedback is requested
            if not task.include_human_feedback:
                logger.info("Human feedback not requested, skipping review")
                state["agent_outputs"]["human"] = {
                    "feedback_requested": False,
                    "review_status": "skipped",
                    "timestamp": datetime.now().isoformat()
                }
                return state
            
            # Prepare plan summary for review
            plan_summary = self._format_plan_for_review(state)
            
            # Get human feedback
            feedback = await self._get_human_feedback(plan_summary, "research_plan")
            
            # Process feedback
            processed_feedback = await self._process_feedback(feedback, "research_plan")
            
            # Update state with human feedback
            state["human_feedback"] = feedback
            state["agent_outputs"]["human"] = {
                "feedback_type": "research_plan",
                "original_feedback": feedback,
                "processed_feedback": processed_feedback,
                "review_status": "completed",
                "timestamp": datetime.now().isoformat()
            }
            
            # Add to feedback history
            self.feedback_history.append({
                "type": "research_plan",
                "feedback": feedback,
                "timestamp": datetime.now().isoformat()
            })
            
            state["feedback_history"] = self.feedback_history
            
            logger.info("Human review of research plan completed")
            return state
            
        except Exception as e:
            logger.error(f"Human agent review failed: {str(e)}")
            state["errors"].append(f"Human review failed: {str(e)}")
            return state
    
    async def review_draft_content(self, state: ResearchState, section_name: str, draft_content: str) -> Dict[str, Any]:
        logger.info(f"Human agent reviewing draft content for section: {section_name}")
        
        try:
            # Format draft for review
            review_prompt = self._format_draft_for_review(section_name, draft_content, state["task"])
            
            # Get human feedback
            feedback = await self._get_human_feedback(review_prompt, "draft_content")
            
            # Process feedback
            processed_feedback = await self._process_feedback(feedback, "draft_content")
            
            # Determine if revision is needed
            needs_revision = self._determine_revision_need(feedback)
            
            review_result = {
                "section_name": section_name,
                "feedback": feedback,
                "processed_feedback": processed_feedback,
                "needs_revision": needs_revision,
                "review_timestamp": datetime.now().isoformat()
            }
            
            # Add to feedback history
            self.feedback_history.append({
                "type": "draft_content",
                "section": section_name,
                "feedback": feedback,
                "timestamp": datetime.now().isoformat()
            })
            
            return review_result
            
        except Exception as e:
            logger.error(f"Human draft review failed: {str(e)}")
            return {
                "section_name": section_name,
                "feedback": f"Review failed: {str(e)}",
                "needs_revision": False,
                "error": str(e)
            }
    
    async def review_final_report(self, state: ResearchState) -> ResearchState:
        logger.info("Human agent reviewing final report")
        
        try:
            if not state["task"].include_human_feedback:
                logger.info("Human feedback not requested for final report")
                return state
            
            report_content = state.get("report", "")
            
            # Format report for review
            review_prompt = self._format_report_for_review(report_content, state["task"])
            
            # Get human feedback
            feedback = await self._get_human_feedback(review_prompt, "final_report")
            
            # Process feedback
            processed_feedback = await self._process_feedback(feedback, "final_report")
            
            # Update state
            human_output = state["agent_outputs"].get("human", {})
            human_output.update({
                "final_report_feedback": feedback,
                "final_report_processed": processed_feedback,
                "final_review_status": "completed",
                "final_review_timestamp": datetime.now().isoformat()
            })
            
            state["agent_outputs"]["human"] = human_output
            
            return state
            
        except Exception as e:
            logger.error(f"Human final report review failed: {str(e)}")
            state["errors"].append(f"Human final report review failed: {str(e)}")
            return state
    
    def _format_plan_for_review(self, state: ResearchState) -> str:
        sections = state.get("sections", [])
        query = state["task"].query
        
        plan_text = f"""
Research Query: {query}

Proposed Research Plan:
"""
        
        for i, section in enumerate(sections, 1):
            plan_text += f"{i}. {section}\n"
        
        plan_text += f"""
Total Sections: {len(sections)}
Max Sections Allowed: {state["task"].max_sections}

Please review this research plan. Provide feedback on:
1. Completeness of coverage
2. Logical organization
3. Relevance to the research query
4. Any missing important aspects
5. Suggestions for improvement

If you approve the plan, respond with 'approved' or 'no changes needed'.
If you have suggestions, please provide specific feedback.
"""
        return plan_text
    
    def _format_draft_for_review(self, section_name: str, draft_content: str, task_config: TaskConfig) -> str:
        return f"""
Research Query: {task_config.query}
Section: {section_name}

Draft Content:
{draft_content}

Please review this draft section. Provide feedback on:
1. Content accuracy and relevance
2. Writing quality and clarity
3. Completeness of information
4. Logical flow and organization
5. Any factual errors or inconsistencies

If you approve the draft, respond with 'approved'.
If revision is needed, please provide specific feedback.
"""
    
    def _format_report_for_review(self, report_content: str, task_config: TaskConfig) -> str:
        return f"""
Research Query: {task_config.query}

Final Report:
{report_content[:2000]}{'...' if len(report_content) > 2000 else ''}

Please review this final research report. Provide feedback on:
1. Overall quality and completeness
2. Accuracy of information
3. Writing style and clarity
4. Logical structure and flow
5. Conclusion effectiveness
6. Any final suggestions for improvement

If you approve the report for publication, respond with 'approved'.
If changes are needed, please provide specific feedback.
"""
    
    async def _get_human_feedback(self, prompt: str, feedback_type: str) -> str:
        print(f"\n{'='*60}")
        print(f"HUMAN REVIEW REQUESTED - {feedback_type.upper()}")
        print(f"{'='*60}")
        print(prompt)
        print(f"{'='*60}")
        
        try:
            feedback = input("\nYour feedback (or 'approved' if no changes needed): ").strip()
            
            if not feedback:
                feedback = "No feedback provided"
            
            logger.info(f"Human feedback received for {feedback_type}: {feedback[:100]}...")
            return feedback
            
        except KeyboardInterrupt:
            logger.info("Human feedback interrupted by user")
            return "Review interrupted by user"
        except Exception as e:
            logger.error(f"Error getting human feedback: {str(e)}")
            return f"Error getting feedback: {str(e)}"
    
    async def _process_feedback(self, feedback: str, feedback_type: str) -> Dict[str, Any]:
        if not self.llm_manager:
            return {"processed": False, "summary": feedback}
        
        try:
            system_prompt = """You are an expert at processing human feedback for research projects. 
            Analyze the feedback and extract key points, suggestions, and action items."""
            
            user_prompt = f"""Human Feedback Type: {feedback_type}
Feedback: {feedback}

Please analyze this feedback and provide:
1. Key points raised
2. Specific suggestions
3. Priority level (high/medium/low)
4. Action items needed
5. Overall sentiment (positive/negative/neutral)

Format as JSON:
{{
    "key_points": ["point1", "point2", ...],
    "suggestions": ["suggestion1", "suggestion2", ...],
    "priority": "high/medium/low",
    "action_items": ["action1", "action2", ...],
    "sentiment": "positive/negative/neutral",
    "summary": "Brief summary of feedback"
}}"""
            
            response = await self.llm_manager.generate_with_fallback(
                prompt=user_prompt,
                system_prompt=system_prompt,
                tool_type="fast"
            )
            
            return json.loads(response.strip())
            
        except Exception as e:
            logger.error(f"Failed to process feedback: {str(e)}")
            return {
                "processed": False,
                "error": str(e),
                "summary": feedback
            }
    
    def _determine_revision_need(self, feedback: str) -> bool:
        feedback_lower = feedback.lower().strip()
        
        # Check for approval keywords
        approval_keywords = ["approved", "approve", "no changes", "looks good", "good to go"]
        if any(keyword in feedback_lower for keyword in approval_keywords):
            return False
        
        # Check for revision keywords
        revision_keywords = ["revise", "change", "improve", "fix", "error", "wrong", "missing"]
        if any(keyword in feedback_lower for keyword in revision_keywords):
            return True
        
        # If feedback is substantial (more than just "ok" or "fine"), assume revision needed
        if len(feedback.strip()) > 20 and feedback_lower not in ["ok", "fine", "good"]:
            return True
        
        return False

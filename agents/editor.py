import asyncio
from typing import Dict, Any, List, Optional
import logging
import json
from datetime import datetime

from tools.llm_tools import LLMManager
from state import ResearchState, DraftState
from config import Config

logger = logging.getLogger(__name__)


class EditorAgent:
    def __init__(self, config: Config, llm_manager: LLMManager):
        self.config = config
        self.llm_manager = llm_manager
        
    async def plan_research_outline(self, state: ResearchState) -> ResearchState:
        query = state["task"].query
        initial_research = state["initial_research"]
        max_sections = state["task"].max_sections
        
        logger.info(f"Planning research outline for query: {query}")
        
        try:
            # Generate research outline
            outline_data = await self._generate_outline(query, initial_research, max_sections)
            
            if outline_data:
                state["title"] = outline_data.get("title", query)
                state["sections"] = outline_data.get("sections", [])
                state["date"] = datetime.now().strftime("%Y-%m-%d")
                state["current_step"] = "outline_planned"
                
                logger.info(f"Research outline planned with {len(state['sections'])} sections")
            else:
                logger.warning("Failed to generate research outline")
                state["errors"].append("Failed to generate research outline")
                # Fallback: create basic sections
                state["title"] = query
                state["sections"] = [f"Analysis of {query}", f"Key Findings", f"Implications"]
                state["date"] = datetime.now().strftime("%Y-%m-%d")
            
            return state
            
        except Exception as e:
            logger.error(f"Error in planning research outline: {str(e)}")
            state["errors"].append(f"Outline planning failed: {str(e)}")
            return state
    
    async def manage_parallel_research(self, state: ResearchState, researcher_agent) -> ResearchState:
        sections = state["sections"]
        logger.info(f"Managing parallel research for {len(sections)} sections")
        
        try:
            # Create tasks for parallel research
            research_tasks = []
            for section in sections:
                task = asyncio.create_task(
                    researcher_agent.conduct_deep_research(state, section)
                )
                research_tasks.append(task)
            
            # Execute research tasks with timeout
            try:
                research_results = await asyncio.wait_for(
                    asyncio.gather(*research_tasks, return_exceptions=True),
                    timeout=300  # 5 minutes timeout
                )
            except asyncio.TimeoutError:
                logger.warning("Parallel research timed out, using partial results")
                research_results = []
                for task in research_tasks:
                    if task.done():
                        try:
                            research_results.append(task.result())
                        except Exception as e:
                            research_results.append({"error": str(e)})
                    else:
                        task.cancel()
                        research_results.append({"error": "Task timed out"})
            
            # Process research results
            processed_results = []
            for i, result in enumerate(research_results):
                if isinstance(result, Exception):
                    logger.error(f"Research task {i} failed: {str(result)}")
                    processed_results.append({
                        "topic": sections[i] if i < len(sections) else f"Section {i}",
                        "content": f"Research failed: {str(result)}",
                        "sources": [],
                        "source_count": 0
                    })
                elif isinstance(result, dict) and "error" not in result:
                    processed_results.append(result)
                else:
                    logger.error(f"Research task {i} returned error: {result}")
                    processed_results.append({
                        "topic": sections[i] if i < len(sections) else f"Section {i}",
                        "content": f"Research failed: {result.get('error', 'Unknown error')}",
                        "sources": [],
                        "source_count": 0
                    })
            
            # Update state with research results
            state["research_data"] = processed_results
            state["completed_sections"] = [result["topic"] for result in processed_results]
            state["current_step"] = "parallel_research_completed"
            
            logger.info(f"Parallel research completed for {len(processed_results)} sections")
            return state
            
        except Exception as e:
            logger.error(f"Error in managing parallel research: {str(e)}")
            state["errors"].append(f"Parallel research management failed: {str(e)}")
            return state
    
    async def review_and_revise_draft(self, draft_state: DraftState) -> DraftState:
        topic = draft_state["topic"]
        draft_content = draft_state["draft"]
        
        logger.info(f"Reviewing and revising draft for topic: {topic}")
        
        try:
            # Review the draft
            review_feedback = await self._review_draft(topic, draft_content, draft_state["task"])
            
            if review_feedback and review_feedback.get("needs_revision", False):
                # Generate revision
                revised_content = await self._revise_draft(
                    topic, 
                    draft_content, 
                    review_feedback.get("feedback", ""),
                    draft_state["task"]
                )
                
                draft_state["draft"] = revised_content
                draft_state["revision_notes"] = review_feedback.get("feedback", "")
                draft_state["iteration_count"] += 1
                
                # Check if we've reached max iterations
                if draft_state["iteration_count"] >= draft_state["max_iterations"]:
                    draft_state["is_approved"] = True
                    logger.info(f"Draft approved after {draft_state['iteration_count']} iterations (max reached)")
                else:
                    logger.info(f"Draft revised (iteration {draft_state['iteration_count']})")
            else:
                draft_state["is_approved"] = True
                draft_state["review"] = review_feedback.get("feedback", "Draft approved")
                logger.info(f"Draft approved for topic: {topic}")
            
            return draft_state
            
        except Exception as e:
            logger.error(f"Error in reviewing/revising draft for topic {topic}: {str(e)}")
            draft_state["is_approved"] = True  # Approve to prevent infinite loop
            draft_state["review"] = f"Review failed: {str(e)}"
            return draft_state
    
    async def _generate_outline(self, query: str, initial_research: str, max_sections: int) -> Optional[Dict[str, Any]]:
        system_prompt = """You are an expert research editor responsible for creating comprehensive research outlines.
        Your task is to analyze initial research findings and create a well-structured outline for a research report."""
        
        user_prompt = f"""Research Query: {query}

Initial Research Summary:
{initial_research}

Based on the research query and initial findings, create a comprehensive research outline with:
1. A clear, descriptive title for the research report
2. {max_sections} main section headers that logically organize the research topic
3. Sections should focus on substantive research topics, NOT introduction, conclusion, or references

Return your response as a JSON object with this exact structure:
{{
    "title": "Research Report Title",
    "sections": ["Section 1 Title", "Section 2 Title", "Section 3 Title", ...]
}}

Ensure the sections are:
- Comprehensive and cover key aspects of the topic
- Logically ordered
- Specific enough to guide focused research
- Relevant to answering the main research question"""
        
        try:
            response = await self.llm_manager.generate_with_fallback(
                prompt=user_prompt,
                system_prompt=system_prompt,
                tool_type="smart"
            )
            
            # Parse JSON response
            outline_data = json.loads(response.strip())
            
            # Validate structure
            if "title" in outline_data and "sections" in outline_data:
                # Limit sections to max_sections
                outline_data["sections"] = outline_data["sections"][:max_sections]
                return outline_data
            else:
                logger.error("Invalid outline structure returned")
                return None
                
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse outline JSON: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Failed to generate outline: {str(e)}")
            return None
    
    async def _review_draft(self, topic: str, draft_content: Dict[str, Any], task_config) -> Dict[str, Any]:
        content = draft_content.get("content", "")
        
        system_prompt = """You are an expert editor and reviewer. Your task is to review research draft content 
        and provide constructive feedback to improve quality, accuracy, and completeness."""
        
        user_prompt = f"""Topic: {topic}
Research Query Context: {task_config.query}

Draft Content:
{content}

Please review this draft and provide feedback on:
1. Content quality and depth
2. Accuracy and factual consistency
3. Logical structure and flow
4. Completeness of coverage
5. Writing clarity and style

Return your response as a JSON object:
{{
    "needs_revision": true/false,
    "feedback": "Detailed feedback and suggestions for improvement",
    "quality_score": 0.0-1.0
}}

If the draft is of good quality and doesn't need major revisions, set needs_revision to false."""
        
        try:
            response = await self.llm_manager.generate_with_fallback(
                prompt=user_prompt,
                system_prompt=system_prompt,
                tool_type="smart"
            )
            
            review_data = json.loads(response.strip())
            return review_data
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse review JSON: {str(e)}")
            return {"needs_revision": False, "feedback": "Review parsing failed", "quality_score": 0.7}
        except Exception as e:
            logger.error(f"Failed to review draft: {str(e)}")
            return {"needs_revision": False, "feedback": f"Review failed: {str(e)}", "quality_score": 0.7}
    
    async def _revise_draft(self, topic: str, draft_content: Dict[str, Any], feedback: str, task_config) -> Dict[str, Any]:
        content = draft_content.get("content", "")
        
        system_prompt = """You are an expert writer and editor. Your task is to revise research content 
        based on provided feedback to improve its quality, accuracy, and completeness."""
        
        user_prompt = f"""Topic: {topic}
Research Query Context: {task_config.query}

Original Draft:
{content}

Feedback for Revision:
{feedback}

Please revise the draft content based on the feedback provided. Ensure the revised version:
1. Addresses all points raised in the feedback
2. Maintains the original structure while improving content
3. Enhances clarity and readability
4. Provides more comprehensive coverage if needed
5. Maintains factual accuracy

Return the revised content as a complete, well-structured research section."""
        
        try:
            revised_content = await self.llm_manager.generate_with_fallback(
                prompt=user_prompt,
                system_prompt=system_prompt,
                tool_type="smart"
            )
            
            return {
                "content": revised_content,
                "sources": draft_content.get("sources", []),
                "source_count": draft_content.get("source_count", 0)
            }
            
        except Exception as e:
            logger.error(f"Failed to revise draft: {str(e)}")
            return draft_content  # Return original if revision fails

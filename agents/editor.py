import asyncio
from typing import Dict, Any, List, Optional
import logging
import json
from datetime import datetime

from tools.llm_tools import LLMManager
from state import ResearchState, DraftState
from config import Config
from localization.prompt_manager import MultilingualPromptManager, PromptType

logger = logging.getLogger(__name__)


class EditorAgent:
    def __init__(self, config: Config, llm_manager: LLMManager):
        self.config = config
        self.llm_manager = llm_manager

        # Initialize multilingual prompt manager
        self.prompt_manager = MultilingualPromptManager()
        
    async def plan_research_outline(self, state: ResearchState) -> ResearchState:
        query = state["task"].query
        initial_research = state["initial_research"]
        max_sections = state["task"].max_sections
        
        logger.info(f"Planning research outline for query: {query}")
        
        try:
            # Get language code from task
            language_code = state["task"].language if hasattr(state["task"], 'language') else "en"

            # Generate research outline
            outline_data = await self._generate_outline(query, initial_research, max_sections, language_code)
            
            if outline_data:
                state["title"] = outline_data.get("title", query)
                state["sections"] = outline_data.get("sections", [])
                state["date"] = datetime.now().strftime("%Y-%m-%d")
                state["current_step"] = "outline_planned"
                
                logger.info(f"Research outline planned with {len(state['sections'])} sections")
            else:
                logger.warning("Failed to generate research outline")
                state["errors"].append("Failed to generate research outline")
                # Fallback: create basic sections with localized titles
                state["title"] = query

                # Get localized section titles using section_titles
                analysis_title = self.prompt_manager.language_manager.get_section_title("analysis", language_code)
                findings_title = self.prompt_manager.language_manager.get_section_title("findings", language_code)
                discussion_title = self.prompt_manager.language_manager.get_section_title("discussion", language_code)

                state["sections"] = [f"{analysis_title} {query}", findings_title, discussion_title]
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
    
    async def _generate_outline(self, query: str, initial_research: str, max_sections: int, language_code: Optional[str] = None) -> Optional[Dict[str, Any]]:
        # Get localized prompts
        system_prompt, user_prompt = self.prompt_manager.format_prompt(
            PromptType.OUTLINE_GENERATION,
            language_code=language_code,
            query=query,
            initial_research=initial_research,
            max_sections=max_sections
        )
        
        try:
            response = await self.llm_manager.generate_with_fallback(
                prompt=user_prompt,
                system_prompt=system_prompt,
                tool_type="smart"
            )

            # Debug: Log the raw response
            logger.debug(f"Raw LLM response for outline: {response[:300] if response else 'None'}...")

            if not response or not response.strip():
                logger.error("Empty response from LLM for outline generation")
                return None

            # Clean the response - remove any potential markdown formatting
            cleaned_response = response.strip()

            # Remove markdown code blocks if present
            if cleaned_response.startswith('```json'):
                cleaned_response = cleaned_response[7:]
            if cleaned_response.startswith('```'):
                cleaned_response = cleaned_response[3:]
            if cleaned_response.endswith('```'):
                cleaned_response = cleaned_response[:-3]

            cleaned_response = cleaned_response.strip()

            # Try to find JSON in the response if it's not pure JSON
            if not cleaned_response.startswith('{'):
                json_start = cleaned_response.find('{')
                if json_start >= 0:
                    json_end = cleaned_response.rfind('}') + 1
                    if json_end > json_start:
                        cleaned_response = cleaned_response[json_start:json_end]

            logger.debug(f"Cleaned response: {cleaned_response[:200]}...")

            # Parse JSON response
            outline_data = json.loads(cleaned_response)

            # Validate structure
            if "title" in outline_data and "sections" in outline_data and isinstance(outline_data["sections"], list):
                # Limit sections to max_sections
                outline_data["sections"] = outline_data["sections"][:max_sections]
                logger.info(f"Successfully generated outline with {len(outline_data['sections'])} sections")
                return outline_data
            else:
                logger.error(f"Invalid outline structure returned: {outline_data}")
                return None

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse outline JSON: {str(e)}")
            logger.error(f"Raw response that failed to parse: {response[:500] if response else 'None'}")
            return None
        except Exception as e:
            logger.error(f"Failed to generate outline: {str(e)}")
            return None
    
    async def _review_draft(self, topic: str, draft_content: Dict[str, Any], task_config) -> Dict[str, Any]:
        content = draft_content.get("content", "")

        # Get language code from task
        language_code = task_config.language if hasattr(task_config, 'language') else "en"

        # Get localized prompts
        system_prompt, user_prompt = self.prompt_manager.format_prompt(
            PromptType.EDITOR_DRAFT_REVIEW,
            language_code=language_code,
            topic=topic,
            query=task_config.query,
            content=content
        )
        
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

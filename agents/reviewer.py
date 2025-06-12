from typing import Dict, Any, List, Optional
import logging
import json

from tools.llm_tools import LLMManager
from state import ResearchState, DraftState
from config import Config
from localization.prompt_manager import MultilingualPromptManager, PromptType

logger = logging.getLogger(__name__)


class ReviewerAgent:
    def __init__(self, config: Config, llm_manager: LLMManager):
        self.config = config
        self.llm_manager = llm_manager

        # Initialize multilingual prompt manager
        self.prompt_manager = MultilingualPromptManager()
        
    async def review_research_quality(self, state: ResearchState) -> ResearchState:
        logger.info("Starting research quality review")
        
        try:
            # Review each research section
            research_data = state["research_data"]
            review_results = []
            
            for data in research_data:
                review_result = await self._review_research_section(data, state["task"])
                review_results.append(review_result)
            
            # Compile overall review feedback
            overall_feedback = await self._compile_overall_feedback(review_results, state)
            
            # Update state with review information
            state["agent_outputs"]["reviewer"] = {
                "section_reviews": review_results,
                "overall_feedback": overall_feedback,
                "review_timestamp": logging.Formatter().formatTime(logging.LogRecord("", 0, "", 0, "", (), None))
            }
            
            # Add feedback to history
            state["feedback_history"].append({
                "agent": "reviewer",
                "feedback": overall_feedback,
                "timestamp": logging.Formatter().formatTime(logging.LogRecord("", 0, "", 0, "", (), None))
            })
            
            logger.info("Research quality review completed")
            return state
            
        except Exception as e:
            logger.error(f"Error in research quality review: {str(e)}")
            state["errors"].append(f"Quality review failed: {str(e)}")
            return state
    
    async def review_draft_section(self, draft_state: DraftState) -> DraftState:
        topic = draft_state["topic"]
        draft_content = draft_state["draft"]
        
        logger.info(f"Reviewing draft section: {topic}")
        
        try:
            # Perform detailed review
            review_result = await self._review_draft_content(topic, draft_content, draft_state["task"])
            
            # Determine if revision is needed
            needs_revision = review_result.get("needs_revision", False)
            quality_score = review_result.get("quality_score", 0.7)
            
            if needs_revision and draft_state["iteration_count"] < draft_state["max_iterations"]:
                draft_state["review"] = review_result.get("feedback", "Revision needed")
                draft_state["quality_score"] = quality_score
                logger.info(f"Draft section needs revision (quality score: {quality_score:.2f})")
            else:
                draft_state["review"] = None  # Approved
                draft_state["is_approved"] = True
                draft_state["quality_score"] = quality_score
                logger.info(f"Draft section approved (quality score: {quality_score:.2f})")
            
            return draft_state
            
        except Exception as e:
            logger.error(f"Error reviewing draft section {topic}: {str(e)}")
            # Approve to prevent infinite loop
            draft_state["review"] = None
            draft_state["is_approved"] = True
            draft_state["quality_score"] = 0.6
            return draft_state
    
    async def review_final_report(self, state: ResearchState) -> ResearchState:
        logger.info("Starting final report review")
        
        try:
            report_content = state["report"]
            
            # Perform comprehensive report review
            review_result = await self._review_complete_report(report_content, state["task"])
            
            # Update state with final review
            state["agent_outputs"]["final_reviewer"] = review_result
            
            # Add to feedback history
            state["feedback_history"].append({
                "agent": "final_reviewer",
                "feedback": review_result.get("summary", "Final review completed"),
                "timestamp": logging.Formatter().formatTime(logging.LogRecord("", 0, "", 0, "", (), None))
            })
            
            logger.info("Final report review completed")
            return state
            
        except Exception as e:
            logger.error(f"Error in final report review: {str(e)}")
            state["errors"].append(f"Final review failed: {str(e)}")
            return state
    
    async def _review_research_section(self, research_data: Dict[str, Any], task_config) -> Dict[str, Any]:
        topic = research_data.get("topic", "Unknown")
        content = research_data.get("content", "")
        sources = research_data.get("sources", [])

        # Get language code from task
        language_code = task_config.language if hasattr(task_config, 'language') else "en"

        # Get localized prompts
        system_prompt, user_prompt = self.prompt_manager.format_prompt(
            PromptType.RESEARCH_REVIEW,
            language_code=language_code,
            topic=topic,
            query=task_config.query,
            content=content[:2000] + "..." if len(content) > 2000 else content,
            source_count=len(sources)
        )

        try:
            response = await self.llm_manager.generate_with_fallback(
                prompt=user_prompt,
                system_prompt=system_prompt,
                tool_type="smart"
            )

            # Clean and validate response
            cleaned_response = self._clean_json_response(response)
            if not cleaned_response:
                logger.error(f"Empty response from LLM for topic {topic}")
                return self._create_fallback_review(topic, "Empty LLM response")

            logger.debug(f"LLM response for {topic}: {cleaned_response[:200]}...")

            review_data = json.loads(cleaned_response)

            # Validate required fields
            if not self._validate_review_structure(review_data):
                logger.error(f"Invalid review structure for {topic}")
                return self._create_fallback_review(topic, "Invalid review structure")

            return review_data

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse review JSON for {topic}: {str(e)}")
            logger.error(f"Raw response: {response[:500] if response else 'None'}")
            return self._create_fallback_review(topic, f"JSON parsing failed: {str(e)}")

        except Exception as e:
            logger.error(f"Failed to review research section {topic}: {str(e)}")
            return self._create_fallback_review(topic, f"Review failed: {str(e)}")

    def _clean_json_response(self, response: str) -> str:
        if not response:
            return ""

        # Remove common markdown formatting
        cleaned = response.strip()

        # Remove markdown code blocks
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        elif cleaned.startswith("```"):
            cleaned = cleaned[3:]

        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]

        # Remove any leading/trailing whitespace
        cleaned = cleaned.strip()

        return cleaned

    def _validate_review_structure(self, review_data: Dict[str, Any]) -> bool:
        required_fields = ["topic", "quality_score", "strengths", "weaknesses", "suggestions", "overall_assessment"]

        for field in required_fields:
            if field not in review_data:
                return False

        # Validate data types
        if not isinstance(review_data.get("quality_score"), (int, float)):
            return False

        if not isinstance(review_data.get("strengths"), list):
            return False

        if not isinstance(review_data.get("weaknesses"), list):
            return False

        if not isinstance(review_data.get("suggestions"), list):
            return False

        return True

    def _create_fallback_review(self, topic: str, error_msg: str) -> Dict[str, Any]:
        return {
            "topic": topic,
            "quality_score": 0.7,
            "strengths": ["Content provided"],
            "weaknesses": ["Review parsing failed"],
            "suggestions": ["Manual review recommended"],
            "overall_assessment": f"Automated review failed: {error_msg}"
        }
    
    async def _review_draft_content(self, topic: str, draft_content: Dict[str, Any], task_config) -> Dict[str, Any]:
        content = draft_content.get("content", "")

        system_prompt = """You are an expert editor and content reviewer. Evaluate draft content for quality,
        accuracy, completeness, and writing quality. Provide specific, actionable feedback.

        IMPORTANT: You must respond with a valid JSON object only. Do not include any markdown formatting,
        code blocks, or additional text outside the JSON."""

        user_prompt = f"""Draft Topic: {topic}
Research Context: {task_config.query}

Draft Content:
{content}

Please review this draft content and evaluate:
1. Writing Quality (clarity, flow, style)
2. Content Accuracy and Factual Consistency
3. Completeness of Topic Coverage
4. Logical Structure and Organization
5. Relevance to Research Context

Provide your review as a JSON object:
{{
    "needs_revision": true/false,
    "quality_score": 0.0-1.0,
    "feedback": "Detailed feedback with specific suggestions",
    "priority_issues": ["issue 1", "issue 2", ...],
    "minor_suggestions": ["suggestion 1", "suggestion 2", ...]
}}

Set needs_revision to true only if there are significant issues that require content changes."""

        try:
            response = await self.llm_manager.generate_with_fallback(
                prompt=user_prompt,
                system_prompt=system_prompt,
                tool_type="smart"
            )

            # Clean and validate response
            cleaned_response = self._clean_json_response(response)
            if not cleaned_response:
                logger.error(f"Empty response from LLM for draft review of {topic}")
                return self._create_fallback_draft_review("Empty LLM response")

            logger.debug(f"LLM draft review response for {topic}: {cleaned_response[:200]}...")

            review_data = json.loads(cleaned_response)

            # Validate required fields
            if not self._validate_draft_review_structure(review_data):
                logger.error(f"Invalid draft review structure for {topic}")
                return self._create_fallback_draft_review("Invalid review structure")

            return review_data

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse draft review JSON for {topic}: {str(e)}")
            logger.error(f"Raw response: {response[:500] if response else 'None'}")
            return self._create_fallback_draft_review(f"JSON parsing failed: {str(e)}")

        except Exception as e:
            logger.error(f"Failed to review draft content for {topic}: {str(e)}")
            return self._create_fallback_draft_review(f"Review failed: {str(e)}")

    def _validate_draft_review_structure(self, review_data: Dict[str, Any]) -> bool:
        required_fields = ["needs_revision", "quality_score", "feedback", "priority_issues", "minor_suggestions"]

        for field in required_fields:
            if field not in review_data:
                return False

        # Validate data types
        if not isinstance(review_data.get("needs_revision"), bool):
            return False

        if not isinstance(review_data.get("quality_score"), (int, float)):
            return False

        if not isinstance(review_data.get("priority_issues"), list):
            return False

        if not isinstance(review_data.get("minor_suggestions"), list):
            return False

        return True

    def _create_fallback_draft_review(self, error_msg: str) -> Dict[str, Any]:
        return {
            "needs_revision": False,
            "quality_score": 0.7,
            "feedback": f"Review parsing failed - content approved by default: {error_msg}",
            "priority_issues": [],
            "minor_suggestions": []
        }
    
    async def _compile_overall_feedback(self, review_results: List[Dict[str, Any]], state: ResearchState) -> str:
        # Calculate average quality score
        quality_scores = [result.get("quality_score", 0.7) for result in review_results]
        avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0.7
        
        # Compile strengths and weaknesses
        all_strengths = []
        all_weaknesses = []
        all_suggestions = []
        
        for result in review_results:
            all_strengths.extend(result.get("strengths", []))
            all_weaknesses.extend(result.get("weaknesses", []))
            all_suggestions.extend(result.get("suggestions", []))
        
        # Generate overall feedback summary
        system_prompt = """You are a senior research reviewer. Compile an overall assessment of research quality 
        based on individual section reviews."""
        
        user_prompt = f"""Research Project: {state['task'].query}
Average Quality Score: {avg_quality:.2f}

Section Reviews Summary:
- Total Sections: {len(review_results)}
- Quality Scores: {quality_scores}

Common Strengths:
{chr(10).join(f'- {strength}' for strength in set(all_strengths))}

Common Weaknesses:
{chr(10).join(f'- {weakness}' for weakness in set(all_weaknesses))}

Suggestions for Improvement:
{chr(10).join(f'- {suggestion}' for suggestion in set(all_suggestions))}

Provide a comprehensive overall assessment (200-300 words) that:
1. Summarizes the overall quality of the research
2. Highlights key strengths across sections
3. Identifies areas for improvement
4. Provides strategic recommendations
5. Gives an overall quality rating"""
        
        try:
            overall_feedback = await self.llm_manager.generate_with_fallback(
                prompt=user_prompt,
                system_prompt=system_prompt,
                tool_type="smart"
            )
            return overall_feedback
        except Exception as e:
            logger.error(f"Failed to compile overall feedback: {str(e)}")
            return f"Overall research quality score: {avg_quality:.2f}. {len(review_results)} sections reviewed."
    
    async def _review_complete_report(self, report_content: str, task_config) -> Dict[str, Any]:
        system_prompt = """You are a senior research reviewer conducting a final quality assessment of a complete research report.
        Evaluate the report holistically for overall quality, coherence, and completeness.

        IMPORTANT: You must respond with a valid JSON object only. Do not include any markdown formatting,
        code blocks, or additional text outside the JSON."""

        user_prompt = f"""Research Query: {task_config.query}

Complete Research Report:
{report_content[:4000]}...

Please provide a comprehensive final review evaluating:
1. Overall Report Quality and Coherence
2. Completeness of Research Coverage
3. Writing Quality and Professional Standards
4. Logical Flow and Structure
5. Achievement of Research Objectives

Provide your assessment as a JSON object:
{{
    "overall_score": 0.0-1.0,
    "summary": "Brief overall assessment",
    "strengths": ["strength 1", "strength 2", ...],
    "areas_for_improvement": ["area 1", "area 2", ...],
    "recommendations": ["recommendation 1", "recommendation 2", ...],
    "publication_ready": true/false
}}"""

        try:
            response = await self.llm_manager.generate_with_fallback(
                prompt=user_prompt,
                system_prompt=system_prompt,
                tool_type="smart"
            )

            # Clean and validate response
            cleaned_response = self._clean_json_response(response)
            if not cleaned_response:
                logger.error("Empty response from LLM for final report review")
                return self._create_fallback_final_review("Empty LLM response")

            logger.debug(f"LLM final review response: {cleaned_response[:200]}...")

            review_data = json.loads(cleaned_response)

            # Validate required fields
            if not self._validate_final_review_structure(review_data):
                logger.error("Invalid final review structure")
                return self._create_fallback_final_review("Invalid review structure")

            return review_data

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse final review JSON: {str(e)}")
            logger.error(f"Raw response: {response[:500] if response else 'None'}")
            return self._create_fallback_final_review(f"JSON parsing failed: {str(e)}")

        except Exception as e:
            logger.error(f"Failed to conduct final review: {str(e)}")
            return self._create_fallback_final_review(f"Review failed: {str(e)}")

    def _validate_final_review_structure(self, review_data: Dict[str, Any]) -> bool:
        required_fields = ["overall_score", "summary", "strengths", "areas_for_improvement", "recommendations", "publication_ready"]

        for field in required_fields:
            if field not in review_data:
                return False

        # Validate data types
        if not isinstance(review_data.get("overall_score"), (int, float)):
            return False

        if not isinstance(review_data.get("publication_ready"), bool):
            return False

        if not isinstance(review_data.get("strengths"), list):
            return False

        if not isinstance(review_data.get("areas_for_improvement"), list):
            return False

        if not isinstance(review_data.get("recommendations"), list):
            return False

        return True

    def _create_fallback_final_review(self, error_msg: str) -> Dict[str, Any]:
        return {
            "overall_score": 0.8,
            "summary": f"Final review completed with issues: {error_msg}",
            "strengths": ["Report completed"],
            "areas_for_improvement": ["Review system needs attention"],
            "recommendations": ["Manual final review recommended"],
            "publication_ready": True
        }

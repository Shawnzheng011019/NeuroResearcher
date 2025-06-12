import asyncio
from typing import Dict, Any, List, Optional
import logging
from datetime import datetime

from tools.llm_tools import LLMManager
from tools.document_tools import ContentDeduplicator
from state import ResearchState
from config import Config
from localization.prompt_manager import MultilingualPromptManager, PromptType

logger = logging.getLogger(__name__)


class WriterAgent:
    def __init__(self, config: Config, llm_manager: LLMManager):
        self.config = config
        self.llm_manager = llm_manager

        # Initialize multilingual prompt manager
        self.prompt_manager = MultilingualPromptManager()

        # Initialize content deduplicator
        self.deduplicator = ContentDeduplicator()
        
    async def write_final_report(self, state: ResearchState) -> ResearchState:
        logger.info("Starting final report writing")
        
        try:
            # Generate table of contents
            toc = await self._generate_table_of_contents(state)
            state["table_of_contents"] = toc
            
            # Write introduction
            introduction = await self._write_introduction(state)
            state["introduction"] = introduction
            
            # Compile main content from research data
            main_content = await self._compile_main_content(state)
            
            # Write conclusion
            conclusion = await self._write_conclusion(state, main_content)
            state["conclusion"] = conclusion
            
            # Compile sources
            sources = self._compile_sources(state)
            state["sources"] = sources
            
            # Assemble final report
            final_report = await self._assemble_final_report(state, main_content)
            state["report"] = final_report
            state["current_step"] = "report_completed"
            
            logger.info("Final report writing completed")
            return state
            
        except Exception as e:
            logger.error(f"Error in writing final report: {str(e)}")
            state["errors"].append(f"Report writing failed: {str(e)}")
            return state
    
    async def _generate_table_of_contents(self, state: ResearchState) -> str:
        title = state["title"]
        sections = state["sections"]

        # Get language code from task
        language_code = state["task"].language if hasattr(state["task"], 'language') else "en"

        # Get localized section titles
        toc_title = self.prompt_manager.language_manager.translate("table_of_contents", language_code)
        intro_title = self.prompt_manager.language_manager.translate("introduction", language_code)
        conclusion_title = self.prompt_manager.language_manager.translate("conclusion", language_code)
        references_title = self.prompt_manager.language_manager.translate("references", language_code)

        toc_lines = [
            f"# {toc_title}\n",
            f"1. {intro_title}",
        ]

        for i, section in enumerate(sections, 2):
            toc_lines.append(f"{i}. {section}")

        toc_lines.extend([
            f"{len(sections) + 2}. {conclusion_title}",
            f"{len(sections) + 3}. {references_title}"
        ])

        return "\n".join(toc_lines)
    
    async def _write_introduction(self, state: ResearchState) -> str:
        query = state["task"].query
        title = state["title"]
        sections = state["sections"]
        initial_research = state["initial_research"]

        # Get language code from task
        language_code = state["task"].language if hasattr(state["task"], 'language') else "en"

        # Get localized prompts
        system_prompt, user_prompt = self.prompt_manager.format_prompt(
            PromptType.INTRODUCTION_WRITING,
            language_code=language_code,
            title=title,
            query=query,
            sections="\n".join(f"- {section}" for section in sections),
            initial_research=initial_research[:1000] + "..." if len(initial_research) > 1000 else initial_research
        )

        try:
            introduction = await self.llm_manager.generate_with_fallback(
                prompt=user_prompt,
                system_prompt=system_prompt,
                tool_type="smart"
            )
            return introduction
        except Exception as e:
            logger.error(f"Failed to write introduction: {str(e)}")
            # Use localized fallback text
            intro_title = self.prompt_manager.language_manager.translate("introduction", language_code)
            return f"# {intro_title}\n\nThis report examines {query} through comprehensive research and analysis."
    
    async def _compile_main_content(self, state: ResearchState) -> str:
        research_data = state["research_data"]

        if not research_data:
            return "No research content available."

        content_sections = []

        for data in research_data:
            topic = data.get("topic", "Unknown Topic")
            content = data.get("content", "No content available")

            # Clean and process content to remove redundant sections
            cleaned_content = await self._clean_section_content(content, topic, state)

            # Format as a main section
            section_content = f"## {topic}\n\n{cleaned_content}\n"
            content_sections.append(section_content)

        return "\n".join(content_sections)

    async def _clean_section_content(self, content: str, topic: str, state: ResearchState) -> str:
        """Clean section content to remove redundant introductions, basic concepts, and conclusions"""
        if not content or len(content.strip()) < 100:
            return content

        # Get language code from task
        language_code = state["task"].language if hasattr(state["task"], 'language') else "en"

        # Create system prompt for content cleaning
        system_prompt = """You are an expert content editor. Your task is to clean and refine a research section by removing redundant content that doesn't belong in a focused section of a larger report.

Remove or minimize:
1. General introductions about the field or topic
2. Basic concept explanations that belong in an overview section
3. Standalone conclusions (the report will have its own conclusion)
4. Repetitive background information
5. Generic statements that don't add specific value

Keep and enhance:
1. Specific findings and analysis related to the topic
2. Evidence-based insights
3. Detailed technical information
4. Comparative analysis
5. Topic-specific applications and examples

The result should be a focused, substantive section that directly addresses the specific topic without redundant content."""

        user_prompt = f"""Topic: {topic}
Main Research Question: {state["task"].query}

Original Content:
{content}

Please clean and refine this content to create a focused section that:
1. Removes redundant introductions, basic concepts, and standalone conclusions
2. Keeps specific findings, analysis, and insights related to the topic
3. Maintains academic rigor while being concise
4. Focuses on the specific topic without general background

Return the cleaned content that directly addresses the topic without redundant elements."""

        try:
            cleaned_content = await self.llm_manager.generate_with_fallback(
                prompt=user_prompt,
                system_prompt=system_prompt,
                tool_type="smart"
            )
            return cleaned_content
        except Exception as e:
            logger.error(f"Failed to clean section content for topic {topic}: {str(e)}")
            # Return original content if cleaning fails
            return content

    async def _write_conclusion(self, state: ResearchState, main_content: str) -> str:
        query = state["task"].query
        title = state["title"]

        # Prepare content summary for conclusion
        content_summary = main_content[:3000] if len(main_content) > 3000 else main_content

        # Get language code from task
        language_code = state["task"].language if hasattr(state["task"], 'language') else "en"

        # Get localized prompts
        system_prompt, user_prompt = self.prompt_manager.format_prompt(
            PromptType.CONCLUSION_WRITING,
            language_code=language_code,
            title=title,
            query=query,
            content_summary=content_summary
        )

        try:
            conclusion = await self.llm_manager.generate_with_fallback(
                prompt=user_prompt,
                system_prompt=system_prompt,
                tool_type="smart"
            )
            return conclusion
        except Exception as e:
            logger.error(f"Failed to write conclusion: {str(e)}")
            # Use localized fallback text
            conclusion_title = self.prompt_manager.language_manager.translate("conclusion", language_code)
            return f"# {conclusion_title}\n\nThis research has provided insights into {query} through comprehensive analysis."
    
    def _compile_sources(self, state: ResearchState) -> List[str]:
        sources = []
        research_data = state["research_data"]
        
        for data in research_data:
            data_sources = data.get("sources", [])
            for source in data_sources:
                url = source.get("url", "")
                title = source.get("title", "")
                domain = source.get("domain", "")
                
                if url and url not in [s.split(" - ")[0] if " - " in s else s for s in sources]:
                    if title:
                        source_entry = f"{url} - {title}"
                    else:
                        source_entry = url
                    sources.append(source_entry)
        
        return sources
    
    async def _assemble_final_report(self, state: ResearchState, main_content: str) -> str:
        title = state["title"]
        date = state["date"]
        table_of_contents = state["table_of_contents"]
        introduction = state["introduction"]
        conclusion = state["conclusion"]
        sources = state["sources"]

        # Get language code from task
        language_code = state["task"].language if hasattr(state["task"], 'language') else "en"

        # Get localized section titles
        intro_title = self.prompt_manager.language_manager.translate("introduction", language_code)
        conclusion_title = self.prompt_manager.language_manager.translate("conclusion", language_code)
        references_title = self.prompt_manager.language_manager.translate("references", language_code)
        date_label = self.prompt_manager.language_manager.translate("date", language_code)
        query_label = self.prompt_manager.language_manager.translate("research_query", language_code)

        # Format date according to language
        lang_config = self.prompt_manager.language_manager.get_language(language_code)
        formatted_date = date
        if lang_config and hasattr(lang_config, 'date_format'):
            try:
                date_obj = datetime.strptime(date, "%Y-%m-%d")
                formatted_date = date_obj.strftime(lang_config.date_format)
            except:
                formatted_date = date

        # Assemble the complete report
        report_parts = [
            f"# {title}\n",
            f"**{date_label}:** {formatted_date}\n",
            f"**{query_label}:** {state['task'].query}\n",
            "---\n",
            table_of_contents,
            "\n---\n",
            f"# {intro_title}\n",
            introduction,
            "\n---\n",
            main_content,
            "\n---\n",
            f"# {conclusion_title}\n",
            conclusion,
            "\n---\n",
            f"# {references_title}\n"
        ]
        
        # Add sources
        if sources:
            for i, source in enumerate(sources, 1):
                report_parts.append(f"{i}. {source}")
        else:
            report_parts.append("No sources available.")
        
        # Add metadata with localized labels
        generated_on_label = self.prompt_manager.language_manager.translate("generated_on", language_code)

        report_parts.extend([
            "\n---\n",
            f"## {self.prompt_manager.language_manager.translate('report_metadata', language_code)}\n",
            f"- **{generated_on_label}:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"- **Total sections:** {len(state['sections'])}",
            f"- **Total sources:** {len(sources)}",
            f"- **Research cost:** ${state['costs']:.4f}" if state['costs'] > 0 else "- **Research cost:** Not tracked"
        ])
        
        final_report = "\n".join(report_parts)

        # Remove duplicate headings and sections
        final_report = self.deduplicator.clean_content(final_report)

        # Enhance report formatting if needed
        enhanced_report = await self._enhance_report_formatting(final_report, state)

        return enhanced_report
    
    async def _enhance_report_formatting(self, report: str, state: ResearchState) -> str:
        # Check if guidelines require specific formatting
        guidelines = state["task"].guidelines
        
        if not guidelines or not state["task"].follow_guidelines:
            return report
        
        system_prompt = """You are an expert document formatter. Your task is to reformat a research report 
        according to specific guidelines while maintaining all the content and structure."""
        
        user_prompt = f"""Research Report:
{report}

Formatting Guidelines:
{chr(10).join(f'- {guideline}' for guideline in guidelines)}

Please reformat the report according to the provided guidelines. Ensure:
1. All original content is preserved
2. The structure remains logical and readable
3. Guidelines are followed as closely as possible
4. Professional formatting is maintained

Return the complete reformatted report."""
        
        try:
            enhanced_report = await self.llm_manager.generate_with_fallback(
                prompt=user_prompt,
                system_prompt=system_prompt,
                tool_type="smart"
            )
            # Apply deduplication after formatting enhancement
            enhanced_report = self.deduplicator.clean_content(enhanced_report)
            return enhanced_report
        except Exception as e:
            logger.error(f"Failed to enhance report formatting: {str(e)}")
            return report  # Return original if enhancement fails

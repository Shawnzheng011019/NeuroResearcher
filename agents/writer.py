import asyncio
from typing import Dict, Any, List, Optional
import logging
from datetime import datetime

from tools.llm_tools import LLMManager
from state import ResearchState
from config import Config

logger = logging.getLogger(__name__)


class WriterAgent:
    def __init__(self, config: Config, llm_manager: LLMManager):
        self.config = config
        self.llm_manager = llm_manager
        
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
        
        toc_lines = [
            "# Table of Contents\n",
            "1. Introduction",
        ]
        
        for i, section in enumerate(sections, 2):
            toc_lines.append(f"{i}. {section}")
        
        toc_lines.extend([
            f"{len(sections) + 2}. Conclusion",
            f"{len(sections) + 3}. References"
        ])
        
        return "\n".join(toc_lines)
    
    async def _write_introduction(self, state: ResearchState) -> str:
        query = state["task"].query
        title = state["title"]
        sections = state["sections"]
        initial_research = state["initial_research"]
        
        system_prompt = """You are an expert academic writer. Write a compelling and informative introduction 
        for a research report that sets the context, explains the importance of the topic, and outlines 
        what the report will cover."""
        
        user_prompt = f"""Research Topic: {title}
Research Question: {query}

Report Sections to be Covered:
{chr(10).join(f'- {section}' for section in sections)}

Background Research Summary:
{initial_research[:1000]}...

Write a comprehensive introduction (300-500 words) that:
1. Introduces the research topic and its significance
2. Provides necessary background context
3. Clearly states the research question or objective
4. Outlines the structure and scope of the report
5. Engages the reader and establishes the importance of the research

The introduction should be professional, well-structured, and set appropriate expectations for the report."""
        
        try:
            introduction = await self.llm_manager.generate_with_fallback(
                prompt=user_prompt,
                system_prompt=system_prompt,
                tool_type="smart"
            )
            return introduction
        except Exception as e:
            logger.error(f"Failed to write introduction: {str(e)}")
            return f"# Introduction\n\nThis report examines {query} through comprehensive research and analysis."
    
    async def _compile_main_content(self, state: ResearchState) -> str:
        research_data = state["research_data"]
        
        if not research_data:
            return "No research content available."
        
        content_sections = []
        
        for data in research_data:
            topic = data.get("topic", "Unknown Topic")
            content = data.get("content", "No content available")
            
            # Format as a main section
            section_content = f"## {topic}\n\n{content}\n"
            content_sections.append(section_content)
        
        return "\n".join(content_sections)
    
    async def _write_conclusion(self, state: ResearchState, main_content: str) -> str:
        query = state["task"].query
        title = state["title"]
        
        # Prepare content summary for conclusion
        content_summary = main_content[:3000] if len(main_content) > 3000 else main_content
        
        system_prompt = """You are an expert academic writer. Write a comprehensive conclusion that synthesizes 
        the research findings, draws meaningful insights, and provides a satisfying closure to the research report."""
        
        user_prompt = f"""Research Topic: {title}
Research Question: {query}

Main Research Content Summary:
{content_summary}

Write a comprehensive conclusion (400-600 words) that:
1. Summarizes the key findings from the research
2. Synthesizes insights across different aspects of the topic
3. Addresses the original research question
4. Discusses implications and significance of the findings
5. Identifies any limitations or areas for future research
6. Provides a strong, memorable closing

The conclusion should tie together all the research findings and provide clear answers or insights 
related to the original research question."""
        
        try:
            conclusion = await self.llm_manager.generate_with_fallback(
                prompt=user_prompt,
                system_prompt=system_prompt,
                tool_type="smart"
            )
            return conclusion
        except Exception as e:
            logger.error(f"Failed to write conclusion: {str(e)}")
            return f"# Conclusion\n\nThis research has provided insights into {query} through comprehensive analysis."
    
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
        
        # Assemble the complete report
        report_parts = [
            f"# {title}\n",
            f"**Date:** {date}\n",
            f"**Research Query:** {state['task'].query}\n",
            "---\n",
            table_of_contents,
            "\n---\n",
            "# Introduction\n",
            introduction,
            "\n---\n",
            main_content,
            "\n---\n",
            "# Conclusion\n",
            conclusion,
            "\n---\n",
            "# References\n"
        ]
        
        # Add sources
        if sources:
            for i, source in enumerate(sources, 1):
                report_parts.append(f"{i}. {source}")
        else:
            report_parts.append("No sources available.")
        
        # Add metadata
        report_parts.extend([
            "\n---\n",
            "## Report Metadata\n",
            f"- **Generated on:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"- **Total sections:** {len(state['sections'])}",
            f"- **Total sources:** {len(sources)}",
            f"- **Research cost:** ${state['costs']:.4f}" if state['costs'] > 0 else "- **Research cost:** Not tracked"
        ])
        
        final_report = "\n".join(report_parts)
        
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
            return enhanced_report
        except Exception as e:
            logger.error(f"Failed to enhance report formatting: {str(e)}")
            return report  # Return original if enhancement fails

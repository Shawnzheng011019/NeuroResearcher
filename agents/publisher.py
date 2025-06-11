import asyncio
from typing import Dict, Any, List, Optional
import logging
from datetime import datetime
import os

from tools.document_tools import DocumentPublisher
from templates import create_template_manager
from localization import create_language_manager
from state import ResearchState, PublishState
from config import Config

logger = logging.getLogger(__name__)


class PublisherAgent:
    def __init__(self, config: Config):
        self.config = config
        self.template_manager = create_template_manager()
        self.language_manager = create_language_manager()
        self.document_publisher = DocumentPublisher(
            config.output_path,
            self.template_manager,
            self.language_manager
        )
        
    async def publish_report(self, state: ResearchState) -> ResearchState:
        logger.info("Starting report publishing")

        try:
            report_content = state["report"]
            title = state["title"]
            publish_formats = state["task"].publish_formats

            # Get template and language settings from task config
            template_name = getattr(state["task"], "template_name", "default")
            language_code = getattr(state["task"], "language", "en")

            # Prepare metadata
            metadata = {
                "date": state["date"],
                "query": state["task"].query,
                "sources": state["sources"],
                "sections": state["sections"],
                "total_cost": state["costs"]
            }

            # Publish in requested formats with template and localization
            publish_results = await self.document_publisher.publish_all_formats(
                content=report_content,
                title=title,
                formats=publish_formats,
                metadata=metadata,
                template_name=template_name,
                language_code=language_code
            )
            
            # Update state with publishing results
            state["agent_outputs"]["publisher"] = {
                "published_files": publish_results,
                "publish_timestamp": datetime.now().isoformat(),
                "formats_requested": publish_formats,
                "publish_status": "completed"
            }
            
            # Log successful publications
            successful_formats = [fmt for fmt, path in publish_results.items() if not path.startswith("Error:")]
            failed_formats = [fmt for fmt, path in publish_results.items() if path.startswith("Error:")]
            
            if successful_formats:
                logger.info(f"Successfully published in formats: {', '.join(successful_formats)}")
            
            if failed_formats:
                logger.warning(f"Failed to publish in formats: {', '.join(failed_formats)}")
                for fmt in failed_formats:
                    state["errors"].append(f"Publishing failed for {fmt}: {publish_results[fmt]}")
            
            state["current_step"] = "publishing_completed"
            return state
            
        except Exception as e:
            logger.error(f"Error in report publishing: {str(e)}")
            state["errors"].append(f"Publishing failed: {str(e)}")
            return state
    
    async def create_publication_summary(self, state: ResearchState) -> Dict[str, Any]:
        logger.info("Creating publication summary")
        
        try:
            publisher_output = state["agent_outputs"].get("publisher", {})
            published_files = publisher_output.get("published_files", {})
            
            # Calculate file sizes
            file_info = {}
            for format_type, file_path in published_files.items():
                if not file_path.startswith("Error:") and os.path.exists(file_path):
                    file_size = os.path.getsize(file_path)
                    file_info[format_type] = {
                        "path": file_path,
                        "size_bytes": file_size,
                        "size_mb": round(file_size / (1024 * 1024), 2)
                    }
                else:
                    file_info[format_type] = {
                        "path": file_path,
                        "error": True
                    }
            
            # Create summary
            summary = {
                "publication_date": datetime.now().isoformat(),
                "research_query": state["task"].query,
                "report_title": state["title"],
                "total_sections": len(state["sections"]),
                "total_sources": len(state["sources"]),
                "research_cost": state["costs"],
                "published_formats": file_info,
                "output_directory": self.config.output_path,
                "publication_status": "completed" if file_info else "failed"
            }
            
            return summary
            
        except Exception as e:
            logger.error(f"Error creating publication summary: {str(e)}")
            return {
                "publication_date": datetime.now().isoformat(),
                "error": str(e),
                "publication_status": "error"
            }
    
    async def generate_publication_report(self, state: ResearchState) -> str:
        logger.info("Generating publication report")
        
        try:
            summary = await self.create_publication_summary(state)
            publisher_output = state["agent_outputs"].get("publisher", {})
            
            # Create publication report
            report_lines = [
                "# Publication Report",
                f"**Generated:** {summary['publication_date']}",
                "",
                "## Research Information",
                f"- **Query:** {summary['research_query']}",
                f"- **Title:** {summary['report_title']}",
                f"- **Sections:** {summary['total_sections']}",
                f"- **Sources:** {summary['total_sources']}",
                f"- **Research Cost:** ${summary['research_cost']:.4f}",
                "",
                "## Publication Results"
            ]
            
            # Add file information
            published_formats = summary.get("published_formats", {})
            if published_formats:
                for format_type, info in published_formats.items():
                    if info.get("error"):
                        report_lines.append(f"- **{format_type.upper()}:** ❌ {info['path']}")
                    else:
                        report_lines.append(f"- **{format_type.upper()}:** ✅ {info['path']} ({info['size_mb']} MB)")
            else:
                report_lines.append("- No files were successfully published")
            
            # Add output directory
            report_lines.extend([
                "",
                f"**Output Directory:** {summary['output_directory']}",
                f"**Status:** {summary['publication_status'].upper()}"
            ])
            
            # Add errors if any
            if state["errors"]:
                report_lines.extend([
                    "",
                    "## Errors Encountered",
                    *[f"- {error}" for error in state["errors"]]
                ])
            
            # Add agent feedback if available
            if state["feedback_history"]:
                report_lines.extend([
                    "",
                    "## Quality Review Summary"
                ])
                
                for feedback in state["feedback_history"]:
                    agent = feedback.get("agent", "Unknown")
                    feedback_text = feedback.get("feedback", "No feedback")
                    report_lines.append(f"- **{agent.title()}:** {feedback_text[:200]}...")
            
            publication_report = "\n".join(report_lines)
            
            # Save publication report
            report_filename = f"publication_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
            report_path = os.path.join(self.config.output_path, report_filename)
            
            os.makedirs(self.config.output_path, exist_ok=True)
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(publication_report)
            
            logger.info(f"Publication report saved: {report_path}")
            return publication_report
            
        except Exception as e:
            logger.error(f"Error generating publication report: {str(e)}")
            return f"Publication report generation failed: {str(e)}"
    
    async def cleanup_temporary_files(self, state: ResearchState) -> None:
        logger.info("Cleaning up temporary files")
        
        try:
            # This method can be extended to clean up any temporary files
            # created during the research and publishing process
            
            # For now, just log the cleanup attempt
            logger.info("Temporary file cleanup completed")
            
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")
    
    async def validate_published_files(self, state: ResearchState) -> Dict[str, bool]:
        logger.info("Validating published files")
        
        validation_results = {}
        
        try:
            publisher_output = state["agent_outputs"].get("publisher", {})
            published_files = publisher_output.get("published_files", {})
            
            for format_type, file_path in published_files.items():
                if file_path.startswith("Error:"):
                    validation_results[format_type] = False
                    continue
                
                # Check if file exists and has content
                if os.path.exists(file_path):
                    file_size = os.path.getsize(file_path)
                    validation_results[format_type] = file_size > 0
                    
                    if validation_results[format_type]:
                        logger.info(f"✅ {format_type.upper()} file validated: {file_path}")
                    else:
                        logger.warning(f"❌ {format_type.upper()} file is empty: {file_path}")
                else:
                    validation_results[format_type] = False
                    logger.warning(f"❌ {format_type.upper()} file not found: {file_path}")
            
            return validation_results
            
        except Exception as e:
            logger.error(f"Error validating published files: {str(e)}")
            return {}
    
    async def create_shareable_links(self, state: ResearchState) -> Dict[str, str]:
        logger.info("Creating shareable links")
        
        try:
            # This method can be extended to create shareable links
            # for cloud storage, web hosting, etc.
            
            publisher_output = state["agent_outputs"].get("publisher", {})
            published_files = publisher_output.get("published_files", {})
            
            shareable_links = {}
            
            for format_type, file_path in published_files.items():
                if not file_path.startswith("Error:") and os.path.exists(file_path):
                    # For now, just return local file paths
                    # This can be extended to upload to cloud storage and return URLs
                    shareable_links[format_type] = f"file://{os.path.abspath(file_path)}"
            
            return shareable_links
            
        except Exception as e:
            logger.error(f"Error creating shareable links: {str(e)}")
            return {}

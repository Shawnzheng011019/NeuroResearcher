"""Complete pipeline configuration for 8-agent research workflow."""

from typing import Dict, List, Any
from enum import Enum


class WorkflowStage(str, Enum):
    INITIALIZATION = "initialization"
    RESEARCH = "research"
    PLANNING = "planning"
    HUMAN_REVIEW = "human_review"
    REVISION = "revision"
    WRITING = "writing"
    QUALITY_CONTROL = "quality_control"
    PUBLISHING = "publishing"
    FINALIZATION = "finalization"


class AgentRole(str, Enum):
    ORCHESTRATOR = "orchestrator"
    RESEARCHER = "researcher"
    EDITOR = "editor"
    WRITER = "writer"
    REVIEWER = "reviewer"
    REVISER = "reviser"
    HUMAN = "human"
    PUBLISHER = "publisher"


class PipelineConfig:
    """Configuration for the complete 8-agent research pipeline."""
    
    def __init__(self):
        self.agents = self._define_agents()
        self.workflow_stages = self._define_workflow_stages()
        self.agent_interactions = self._define_agent_interactions()
        self.quality_gates = self._define_quality_gates()
        self.fallback_strategies = self._define_fallback_strategies()
    
    def _define_agents(self) -> Dict[str, Dict[str, Any]]:
        return {
            AgentRole.ORCHESTRATOR: {
                "description": "Coordinates the entire research workflow and manages agent interactions",
                "responsibilities": [
                    "Initialize research task",
                    "Monitor workflow progress",
                    "Handle errors and exceptions",
                    "Coordinate agent communication",
                    "Finalize research output"
                ],
                "inputs": ["task_config", "workflow_state"],
                "outputs": ["coordination_status", "performance_metrics", "workflow_summary"]
            },
            
            AgentRole.RESEARCHER: {
                "description": "Conducts initial and deep research on specified topics",
                "responsibilities": [
                    "Perform initial research",
                    "Conduct deep topic-specific research",
                    "Gather and validate sources",
                    "Extract relevant content",
                    "Synthesize research findings"
                ],
                "inputs": ["research_query", "topic_list", "search_parameters"],
                "outputs": ["research_data", "sources", "content_summaries"]
            },
            
            AgentRole.EDITOR: {
                "description": "Plans research structure and manages parallel research execution",
                "responsibilities": [
                    "Create research outline",
                    "Plan section structure",
                    "Manage parallel research tasks",
                    "Coordinate research activities",
                    "Ensure comprehensive coverage"
                ],
                "inputs": ["initial_research", "task_requirements"],
                "outputs": ["research_outline", "section_plan", "research_coordination"]
            },
            
            AgentRole.WRITER: {
                "description": "Writes and structures the final research report",
                "responsibilities": [
                    "Write report sections",
                    "Create introduction and conclusion",
                    "Structure content logically",
                    "Ensure coherent narrative",
                    "Format final report"
                ],
                "inputs": ["research_data", "outline", "writing_guidelines"],
                "outputs": ["draft_sections", "final_report", "content_structure"]
            },
            
            AgentRole.REVIEWER: {
                "description": "Reviews content quality and provides feedback",
                "responsibilities": [
                    "Review research quality",
                    "Assess content accuracy",
                    "Evaluate writing quality",
                    "Provide improvement suggestions",
                    "Score content quality"
                ],
                "inputs": ["research_content", "draft_sections", "quality_criteria"],
                "outputs": ["quality_scores", "review_feedback", "improvement_suggestions"]
            },
            
            AgentRole.REVISER: {
                "description": "Revises content based on feedback and review comments",
                "responsibilities": [
                    "Revise research plans",
                    "Update draft content",
                    "Address review feedback",
                    "Improve content quality",
                    "Track revision history"
                ],
                "inputs": ["original_content", "review_feedback", "revision_guidelines"],
                "outputs": ["revised_content", "revision_notes", "improvement_tracking"]
            },
            
            AgentRole.HUMAN: {
                "description": "Provides human oversight and feedback in the research process",
                "responsibilities": [
                    "Review research plans",
                    "Provide feedback on drafts",
                    "Approve final content",
                    "Guide research direction",
                    "Ensure quality standards"
                ],
                "inputs": ["research_plans", "draft_content", "review_prompts"],
                "outputs": ["human_feedback", "approval_status", "guidance_notes"]
            },
            
            AgentRole.PUBLISHER: {
                "description": "Publishes research output in multiple formats",
                "responsibilities": [
                    "Generate multiple formats",
                    "Apply formatting styles",
                    "Create publication files",
                    "Manage output directories",
                    "Provide publication reports"
                ],
                "inputs": ["final_report", "format_requirements", "metadata"],
                "outputs": ["published_files", "format_outputs", "publication_status"]
            }
        }
    
    def _define_workflow_stages(self) -> Dict[str, Dict[str, Any]]:
        return {
            WorkflowStage.INITIALIZATION: {
                "description": "Initialize the research workflow and set up coordination",
                "primary_agent": AgentRole.ORCHESTRATOR,
                "supporting_agents": [],
                "inputs": ["task_config"],
                "outputs": ["initialized_state", "coordination_setup"],
                "success_criteria": ["task_id_generated", "output_directory_created"]
            },
            
            WorkflowStage.RESEARCH: {
                "description": "Conduct initial research and gather preliminary information",
                "primary_agent": AgentRole.RESEARCHER,
                "supporting_agents": [AgentRole.ORCHESTRATOR],
                "inputs": ["research_query", "search_parameters"],
                "outputs": ["initial_research", "source_list", "preliminary_findings"],
                "success_criteria": ["sources_found", "content_extracted", "relevance_validated"]
            },
            
            WorkflowStage.PLANNING: {
                "description": "Plan research structure and create detailed outline",
                "primary_agent": AgentRole.EDITOR,
                "supporting_agents": [AgentRole.RESEARCHER],
                "inputs": ["initial_research", "task_requirements"],
                "outputs": ["research_outline", "section_structure", "research_plan"],
                "success_criteria": ["outline_created", "sections_defined", "coverage_validated"]
            },
            
            WorkflowStage.HUMAN_REVIEW: {
                "description": "Human review of plans and content for quality assurance",
                "primary_agent": AgentRole.HUMAN,
                "supporting_agents": [AgentRole.ORCHESTRATOR],
                "inputs": ["research_plans", "draft_content"],
                "outputs": ["human_feedback", "approval_decisions", "improvement_guidance"],
                "success_criteria": ["feedback_provided", "decisions_made", "guidance_clear"]
            },
            
            WorkflowStage.REVISION: {
                "description": "Revise content based on feedback and review comments",
                "primary_agent": AgentRole.REVISER,
                "supporting_agents": [AgentRole.EDITOR, AgentRole.WRITER],
                "inputs": ["original_content", "feedback", "revision_requirements"],
                "outputs": ["revised_content", "revision_notes", "improvement_tracking"],
                "success_criteria": ["feedback_addressed", "quality_improved", "changes_documented"]
            },
            
            WorkflowStage.WRITING: {
                "description": "Write comprehensive research report with all sections",
                "primary_agent": AgentRole.WRITER,
                "supporting_agents": [AgentRole.EDITOR, AgentRole.RESEARCHER],
                "inputs": ["research_data", "approved_outline", "writing_guidelines"],
                "outputs": ["complete_report", "section_content", "narrative_structure"],
                "success_criteria": ["all_sections_written", "coherent_narrative", "guidelines_followed"]
            },
            
            WorkflowStage.QUALITY_CONTROL: {
                "description": "Review and validate final report quality",
                "primary_agent": AgentRole.REVIEWER,
                "supporting_agents": [AgentRole.HUMAN],
                "inputs": ["final_report", "quality_criteria", "review_standards"],
                "outputs": ["quality_assessment", "final_feedback", "publication_readiness"],
                "success_criteria": ["quality_validated", "standards_met", "ready_for_publication"]
            },
            
            WorkflowStage.PUBLISHING: {
                "description": "Publish research output in requested formats",
                "primary_agent": AgentRole.PUBLISHER,
                "supporting_agents": [AgentRole.ORCHESTRATOR],
                "inputs": ["approved_report", "format_requirements", "publication_metadata"],
                "outputs": ["published_files", "format_outputs", "publication_report"],
                "success_criteria": ["formats_generated", "files_saved", "publication_successful"]
            },
            
            WorkflowStage.FINALIZATION: {
                "description": "Finalize workflow and generate completion report",
                "primary_agent": AgentRole.ORCHESTRATOR,
                "supporting_agents": [],
                "inputs": ["workflow_state", "all_outputs", "performance_data"],
                "outputs": ["completion_report", "performance_metrics", "final_summary"],
                "success_criteria": ["workflow_completed", "metrics_calculated", "summary_generated"]
            }
        }
    
    def _define_agent_interactions(self) -> Dict[str, List[Dict[str, Any]]]:
        return {
            "orchestrator_to_all": [
                {"type": "coordination", "frequency": "continuous", "purpose": "workflow_management"},
                {"type": "monitoring", "frequency": "per_stage", "purpose": "progress_tracking"},
                {"type": "error_handling", "frequency": "as_needed", "purpose": "exception_management"}
            ],
            
            "researcher_to_editor": [
                {"type": "data_transfer", "frequency": "after_research", "purpose": "research_planning"},
                {"type": "collaboration", "frequency": "during_parallel", "purpose": "deep_research"}
            ],
            
            "editor_to_writer": [
                {"type": "outline_transfer", "frequency": "after_planning", "purpose": "writing_guidance"},
                {"type": "structure_guidance", "frequency": "during_writing", "purpose": "content_organization"}
            ],
            
            "reviewer_to_reviser": [
                {"type": "feedback_transfer", "frequency": "after_review", "purpose": "content_improvement"},
                {"type": "quality_guidance", "frequency": "during_revision", "purpose": "quality_enhancement"}
            ],
            
            "human_to_reviser": [
                {"type": "feedback_provision", "frequency": "after_human_review", "purpose": "human_guided_improvement"},
                {"type": "approval_decisions", "frequency": "per_review_cycle", "purpose": "quality_control"}
            ],
            
            "writer_to_publisher": [
                {"type": "content_transfer", "frequency": "after_writing", "purpose": "publication_preparation"},
                {"type": "format_coordination", "frequency": "during_publishing", "purpose": "output_generation"}
            ]
        }
    
    def _define_quality_gates(self) -> Dict[str, Dict[str, Any]]:
        return {
            "research_quality": {
                "stage": WorkflowStage.RESEARCH,
                "criteria": ["source_credibility", "content_relevance", "information_completeness"],
                "threshold": 0.7,
                "fallback": "additional_research"
            },
            
            "plan_approval": {
                "stage": WorkflowStage.HUMAN_REVIEW,
                "criteria": ["human_approval", "coverage_adequacy", "logical_structure"],
                "threshold": 0.8,
                "fallback": "plan_revision"
            },
            
            "content_quality": {
                "stage": WorkflowStage.QUALITY_CONTROL,
                "criteria": ["writing_quality", "factual_accuracy", "coherence"],
                "threshold": 0.8,
                "fallback": "content_revision"
            },
            
            "publication_readiness": {
                "stage": WorkflowStage.PUBLISHING,
                "criteria": ["format_compliance", "content_completeness", "metadata_accuracy"],
                "threshold": 0.9,
                "fallback": "format_correction"
            }
        }
    
    def _define_fallback_strategies(self) -> Dict[str, Dict[str, Any]]:
        return {
            "research_failure": {
                "triggers": ["no_sources_found", "search_api_failure", "content_extraction_error"],
                "strategy": "alternative_search_methods",
                "max_retries": 3,
                "escalation": "human_intervention"
            },
            
            "quality_failure": {
                "triggers": ["low_quality_score", "review_rejection", "human_disapproval"],
                "strategy": "iterative_revision",
                "max_retries": 3,
                "escalation": "manual_override"
            },
            
            "agent_failure": {
                "triggers": ["agent_error", "timeout", "resource_exhaustion"],
                "strategy": "agent_restart",
                "max_retries": 2,
                "escalation": "workflow_termination"
            },
            
            "human_unavailable": {
                "triggers": ["no_human_response", "review_timeout"],
                "strategy": "automated_approval",
                "max_retries": 1,
                "escalation": "skip_human_review"
            }
        }
    
    def get_workflow_sequence(self) -> List[str]:
        """Get the complete workflow sequence."""
        return [
            WorkflowStage.INITIALIZATION,
            WorkflowStage.RESEARCH,
            WorkflowStage.PLANNING,
            WorkflowStage.HUMAN_REVIEW,
            WorkflowStage.REVISION,  # Conditional
            WorkflowStage.WRITING,
            WorkflowStage.HUMAN_REVIEW,  # Second review
            WorkflowStage.REVISION,  # Conditional
            WorkflowStage.QUALITY_CONTROL,
            WorkflowStage.PUBLISHING,
            WorkflowStage.FINALIZATION
        ]
    
    def get_agent_dependencies(self) -> Dict[str, List[str]]:
        """Get agent dependency mapping."""
        return {
            AgentRole.ORCHESTRATOR: [],  # No dependencies
            AgentRole.RESEARCHER: [AgentRole.ORCHESTRATOR],
            AgentRole.EDITOR: [AgentRole.RESEARCHER],
            AgentRole.WRITER: [AgentRole.EDITOR, AgentRole.RESEARCHER],
            AgentRole.REVIEWER: [AgentRole.WRITER],
            AgentRole.REVISER: [AgentRole.REVIEWER, AgentRole.HUMAN],
            AgentRole.HUMAN: [AgentRole.EDITOR, AgentRole.WRITER],
            AgentRole.PUBLISHER: [AgentRole.WRITER, AgentRole.REVIEWER]
        }

"""State definitions for the GPT Researcher LangGraph implementation."""

from typing import TypedDict, List, Dict, Optional, Any
from config import TaskConfig


class ResearchState(TypedDict):
    # Task configuration
    task: TaskConfig

    # Research process state
    initial_research: str
    sections: List[str]
    research_data: List[Dict[str, Any]]
    human_feedback: Optional[str]

    # Report layout
    title: str
    headers: Dict[str, Any]
    date: str
    table_of_contents: str
    introduction: str
    conclusion: str
    sources: List[str]
    report: str

    # Process tracking
    current_step: str
    completed_sections: List[str]
    errors: List[str]
    costs: float

    # Agent communication
    agent_outputs: Dict[str, Any]
    feedback_history: List[Dict[str, Any]]

    # Workflow coordination
    workflow_status: str
    revision_count: int
    human_review_required: bool

    # Template and localization
    template_config: Optional[Dict[str, Any]]
    language_config: Optional[Dict[str, Any]]
    localized_sections: Dict[str, str]


class DraftState(TypedDict):
    # Task and topic information
    task: TaskConfig
    topic: str
    
    # Draft content
    draft: Dict[str, Any]
    review: Optional[str]
    revision_notes: Optional[str]
    
    # Process tracking
    iteration_count: int
    max_iterations: int
    is_approved: bool
    
    # Quality metrics
    quality_score: Optional[float]
    feedback_summary: Optional[str]


class SearchState(TypedDict):
    # Search parameters
    query: str
    search_results: List[Dict[str, Any]]
    filtered_results: List[Dict[str, Any]]
    
    # Content extraction
    scraped_content: List[Dict[str, Any]]
    processed_content: List[Dict[str, Any]]
    
    # Quality assessment
    relevance_scores: List[float]
    source_credibility: List[float]


class WritingState(TypedDict):
    # Content structure
    outline: Dict[str, Any]
    sections: Dict[str, str]
    
    # Writing process
    current_section: str
    draft_content: str
    final_content: str
    
    # Review and revision
    review_feedback: List[str]
    revision_history: List[Dict[str, Any]]
    
    # Formatting
    format_type: str
    styled_content: str


class PublishState(TypedDict):
    # Content to publish
    final_report: str
    metadata: Dict[str, Any]
    
    # Output formats
    markdown_output: Optional[str]
    pdf_output: Optional[bytes]
    docx_output: Optional[bytes]
    
    # Publishing results
    output_paths: List[str]
    publish_status: Dict[str, bool]
    publish_errors: List[str]


def create_initial_research_state(task: TaskConfig) -> ResearchState:
    return ResearchState(
        task=task,
        initial_research="",
        sections=[],
        research_data=[],
        human_feedback=None,
        title="",
        headers={},
        date="",
        table_of_contents="",
        introduction="",
        conclusion="",
        sources=[],
        report="",
        current_step="initialization",
        completed_sections=[],
        errors=[],
        costs=0.0,
        agent_outputs={},
        feedback_history=[],
        workflow_status="initialized",
        revision_count=0,
        human_review_required=task.include_human_feedback,
        template_config=None,
        language_config=None,
        localized_sections={}
    )


def create_draft_state(task: TaskConfig, topic: str) -> DraftState:
    return DraftState(
        task=task,
        topic=topic,
        draft={},
        review=None,
        revision_notes=None,
        iteration_count=0,
        max_iterations=3,
        is_approved=False,
        quality_score=None,
        feedback_summary=None
    )


def update_state_step(state: ResearchState, step: str) -> ResearchState:
    state["current_step"] = step
    return state


def add_error_to_state(state: ResearchState, error: str) -> ResearchState:
    state["errors"].append(error)
    return state


def add_cost_to_state(state: ResearchState, cost: float) -> ResearchState:
    state["costs"] += cost
    return state


def add_agent_output(state: ResearchState, agent: str, output: Any) -> ResearchState:
    state["agent_outputs"][agent] = output
    return state

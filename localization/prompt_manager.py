"""Multilingual Prompt Manager for consistent language support across all agents."""

import json
import logging
from typing import Dict, Any, Optional, List
from pathlib import Path
from enum import Enum

from .language_manager import SupportedLanguage, LanguageManager

logger = logging.getLogger(__name__)


class PromptType(str, Enum):
    RESEARCH_SUMMARY = "research_summary"
    RESEARCH_QUERY_GENERATION = "research_query_generation"
    RESEARCH_DRAFT = "research_draft"
    INTRODUCTION_WRITING = "introduction_writing"
    CONCLUSION_WRITING = "conclusion_writing"
    RESEARCH_REVIEW = "research_review"
    DRAFT_REVIEW = "draft_review"
    FINAL_REVIEW = "final_review"
    OVERALL_FEEDBACK = "overall_feedback"
    OUTLINE_GENERATION = "outline_generation"
    EDITOR_DRAFT_REVIEW = "editor_draft_review"


class MultilingualPromptManager:
    def __init__(self, localization_dir: str = "./localization"):
        self.localization_dir = Path(localization_dir)
        self.prompts_dir = self.localization_dir / "prompts"
        self.prompts_dir.mkdir(parents=True, exist_ok=True)
        
        self.language_manager = LanguageManager(localization_dir)
        self.prompts: Dict[str, Dict[str, Dict[str, str]]] = {}
        self._load_prompts()
    
    def _load_prompts(self):
        try:
            self._create_default_prompt_files()
            self._load_prompt_files()
        except Exception as e:
            logger.error(f"Failed to load prompts: {str(e)}")
            self._create_fallback_prompts()
    
    def _create_default_prompt_files(self):
        """Create default prompt files for all supported languages."""
        prompt_configs = {
            SupportedLanguage.ENGLISH: self._get_english_prompts(),
            SupportedLanguage.CHINESE_SIMPLIFIED: self._get_chinese_simplified_prompts(),
            SupportedLanguage.CHINESE_TRADITIONAL: self._get_chinese_traditional_prompts(),
            SupportedLanguage.JAPANESE: self._get_japanese_prompts(),
            SupportedLanguage.KOREAN: self._get_korean_prompts()
        }
        
        for lang_code, prompts in prompt_configs.items():
            file_path = self.prompts_dir / f"{lang_code.value}_prompts.json"
            if not file_path.exists():
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(prompts, f, indent=2, ensure_ascii=False)
                logger.info(f"Created prompt file: {file_path}")
    
    def _get_english_prompts(self) -> Dict[str, Dict[str, str]]:
        return {
            PromptType.RESEARCH_SUMMARY: {
                "system": "You are a research analyst tasked with creating a comprehensive summary of research findings. Your goal is to synthesize information from multiple sources into a coherent, well-structured summary. Focus on key insights, important facts, and relevant details that address the research query.",
                "user_template": "Research Query: {query}\n\nResearch Content from Multiple Sources:\n{content_summary}\n\nPlease create a comprehensive research summary that:\n1. Addresses the main research query\n2. Synthesizes key findings from the sources\n3. Identifies important patterns or themes\n4. Highlights any conflicting information\n5. Provides a balanced perspective\n\nFormat the summary in clear, well-structured paragraphs."
            },
            PromptType.RESEARCH_QUERY_GENERATION: {
                "system": "You are a research query specialist. Generate specific, targeted search queries that will help gather comprehensive information about a given topic in the context of the main research question.",
                "user_template": "Main Research Query: {main_query}\nSpecific Topic: {topic}\n\nGenerate 3-5 specific search queries that would help gather detailed information about this topic in relation to the main research question. Each query should be:\n1. Specific and focused\n2. Likely to return relevant results\n3. Different from the others to cover various aspects\n\nReturn only the queries, one per line, without numbering or additional text."
            },
            PromptType.RESEARCH_DRAFT: {
                "system": "You are an expert researcher and writer. Create a comprehensive, well-structured research section that thoroughly covers the given topic based on the provided research data. Your writing should be:\n- Academically rigorous but accessible\n- Well-organized with clear structure\n- Factual and evidence-based\n- Properly contextualized within the main research question",
                "user_template": "Main Research Question: {main_query}\nSection Topic: {topic}\n\nResearch Data:\n{content_summary}\n\nWrite a comprehensive research section that:\n1. Thoroughly covers the topic\n2. Integrates findings from multiple sources\n3. Maintains academic rigor\n4. Provides clear analysis and insights\n5. Connects to the main research question\n\nStructure the content with clear headings and logical flow."
            },
            PromptType.INTRODUCTION_WRITING: {
                "system": "You are an expert academic writer. Write a compelling and informative introduction for a research report that sets the context, explains the importance of the topic, and outlines what the report will cover.",
                "user_template": "Research Topic: {title}\nResearch Question: {query}\n\nPlanned Report Sections:\n{sections}\n\nInitial Research Context:\n{initial_research}\n\nWrite a comprehensive introduction that:\n1. Establishes the context and importance of the topic\n2. Clearly states the research question\n3. Outlines the scope and structure of the report\n4. Engages the reader with compelling opening\n5. Sets appropriate expectations\n\nThe introduction should be professional, well-structured, and set appropriate expectations for the report."
            },
            PromptType.CONCLUSION_WRITING: {
                "system": "You are an expert academic writer. Write a comprehensive conclusion that synthesizes the research findings, draws meaningful insights, and provides a satisfying closure to the research report.",
                "user_template": "Research Topic: {title}\nResearch Question: {query}\n\nMain Report Content Summary:\n{content_summary}\n\nWrite a comprehensive conclusion that:\n1. Synthesizes key findings from the research\n2. Addresses the original research question\n3. Draws meaningful insights and implications\n4. Acknowledges limitations where appropriate\n5. Suggests areas for future research or action\n\nThe conclusion should tie together all the research findings and provide clear answers or insights related to the original research question."
            },
            PromptType.RESEARCH_REVIEW: {
                "system": "You are an expert research reviewer with expertise in evaluating research quality, accuracy, and completeness. Provide detailed, constructive feedback on research content. IMPORTANT: You must respond with a valid JSON object only. Do not include any markdown formatting, code blocks, or additional text outside the JSON.",
                "user_template": "Research Topic: {topic}\nMain Research Query: {query}\n\nResearch Content:\n{content}\n\nNumber of Sources: {source_count}\n\nPlease evaluate this research section on the following criteria:\n1. Content Quality (depth, accuracy, relevance)\n2. Source Coverage (sufficient sources, credible sources)\n3. Logical Structure and Flow\n4. Completeness of Topic Coverage\n5. Alignment with Main Research Query\n\nProvide your review as a JSON object:\n{{\n    \"topic\": \"{topic}\",\n    \"quality_score\": 0.0-1.0,\n    \"strengths\": [\"strength 1\", \"strength 2\", ...],\n    \"weaknesses\": [\"weakness 1\", \"weakness 2\", ...],\n    \"suggestions\": [\"suggestion 1\", \"suggestion 2\", ...],\n    \"overall_assessment\": \"Brief overall assessment\"\n}}"
            },
            PromptType.DRAFT_REVIEW: {
                "system": "You are an expert editor and content reviewer. Evaluate draft content for quality, accuracy, completeness, and writing quality. Provide specific, actionable feedback. IMPORTANT: You must respond with a valid JSON object only. Do not include any markdown formatting, code blocks, or additional text outside the JSON.",
                "user_template": "Draft Topic: {topic}\nResearch Context: {query}\n\nDraft Content:\n{content}\n\nPlease review this draft content and evaluate:\n1. Writing Quality (clarity, flow, style)\n2. Content Accuracy and Factual Consistency\n3. Completeness of Topic Coverage\n4. Logical Structure and Organization\n5. Relevance to Research Context\n\nProvide your review as a JSON object:\n{{\n    \"needs_revision\": true/false,\n    \"quality_score\": 0.0-1.0,\n    \"feedback\": \"Detailed feedback with specific suggestions\",\n    \"priority_issues\": [\"issue 1\", \"issue 2\", ...],\n    \"minor_suggestions\": [\"suggestion 1\", \"suggestion 2\", ...]\n}}\n\nSet needs_revision to true only if there are significant issues that require content changes."
            },
            PromptType.FINAL_REVIEW: {
                "system": "You are a senior research reviewer conducting a final quality assessment of a complete research report. Evaluate the report holistically for overall quality, coherence, and completeness. IMPORTANT: You must respond with a valid JSON object only. Do not include any markdown formatting, code blocks, or additional text outside the JSON.",
                "user_template": "Research Query: {query}\n\nComplete Research Report:\n{content}\n\nPlease provide a comprehensive final review evaluating:\n1. Overall Report Quality and Coherence\n2. Completeness of Research Coverage\n3. Writing Quality and Professional Standards\n4. Logical Flow and Structure\n5. Achievement of Research Objectives\n\nProvide your assessment as a JSON object:\n{{\n    \"overall_score\": 0.0-1.0,\n    \"summary\": \"Brief overall assessment\",\n    \"strengths\": [\"strength 1\", \"strength 2\", ...],\n    \"areas_for_improvement\": [\"area 1\", \"area 2\", ...],\n    \"recommendations\": [\"recommendation 1\", \"recommendation 2\", ...],\n    \"publication_ready\": true/false\n}}"
            },
            PromptType.OVERALL_FEEDBACK: {
                "system": "You are a senior research reviewer. Compile an overall assessment of research quality based on individual section reviews.",
                "user_template": "Research Project: {query}\nAverage Quality Score: {avg_quality}\n\nSection Reviews Summary:\n- Total Sections: {total_sections}\n- Quality Scores: {quality_scores}\n\nCommon Strengths:\n{strengths}\n\nCommon Weaknesses:\n{weaknesses}\n\nSuggestions for Improvement:\n{suggestions}\n\nProvide a comprehensive overall assessment (200-300 words) that:\n1. Summarizes the overall quality of the research\n2. Highlights key strengths across sections\n3. Identifies areas for improvement\n4. Provides strategic recommendations\n5. Gives an overall quality rating"
            },
            PromptType.OUTLINE_GENERATION: {
                "system": "You are an expert research editor responsible for creating comprehensive research outlines. Your task is to analyze initial research findings and create a well-structured outline for a research report. CRITICAL: You MUST respond with ONLY valid JSON. Do not include any explanatory text, markdown formatting, or additional content. Your entire response must be parseable as JSON.",
                "user_template": "Research Query: {query}\n\nInitial Research Summary:\n{initial_research}\n\nBased on the research query and initial findings, create a comprehensive research outline with:\n1. A clear, descriptive title for the research report\n2. {max_sections} main section headers that logically organize the research topic\n3. Sections should focus on substantive research topics, NOT introduction, conclusion, or references\n\nRESPOND WITH ONLY THIS JSON STRUCTURE (no other text):\n{{\n    \"title\": \"Research Report Title\",\n    \"sections\": [\"Section 1 Title\", \"Section 2 Title\", \"Section 3 Title\"]\n}}\n\nRequirements for sections:\n- Comprehensive and cover key aspects of the topic\n- Logically ordered\n- Specific enough to guide focused research\n- Relevant to answering the main research question\n\nIMPORTANT: Your response must start with {{ and end with }}. No explanations, no markdown, no additional text."
            },
            PromptType.EDITOR_DRAFT_REVIEW: {
                "system": "You are an expert editor and reviewer. Your task is to review research draft content and provide constructive feedback to improve quality, accuracy, and completeness.",
                "user_template": "Topic: {topic}\nResearch Query Context: {query}\n\nDraft Content:\n{content}\n\nPlease review this draft and provide feedback on:\n1. Content quality and depth\n2. Accuracy and factual consistency\n3. Logical structure and flow\n4. Completeness of coverage\n5. Writing clarity and style\n\nReturn your response as a JSON object:\n{{\n    \"needs_revision\": true/false,\n    \"feedback\": \"Detailed feedback and suggestions for improvement\",\n    \"quality_score\": 0.0-1.0\n}}\n\nIf the draft is of good quality and doesn't need major revisions, set needs_revision to false."
            }
        }
    
    def _get_chinese_simplified_prompts(self) -> Dict[str, Dict[str, str]]:
        return {
            PromptType.RESEARCH_SUMMARY: {
                "system": "你是一名研究分析师，负责创建全面的研究发现摘要。你的目标是将来自多个来源的信息综合成连贯、结构良好的摘要。重点关注关键见解、重要事实和与研究查询相关的详细信息。",
                "user_template": "研究查询：{query}\n\n来自多个来源的研究内容：\n{content_summary}\n\n请创建一个全面的研究摘要，包括：\n1. 回答主要研究查询\n2. 综合来源的关键发现\n3. 识别重要模式或主题\n4. 突出任何冲突信息\n5. 提供平衡的观点\n\n以清晰、结构良好的段落格式化摘要。"
            },
            PromptType.RESEARCH_QUERY_GENERATION: {
                "system": "你是一名研究查询专家。生成具体、有针对性的搜索查询，这些查询将有助于在主要研究问题的背景下收集关于给定主题的全面信息。",
                "user_template": "主要研究查询：{main_query}\n具体主题：{topic}\n\n生成3-5个具体的搜索查询，这些查询将有助于收集与主要研究问题相关的该主题的详细信息。每个查询应该：\n1. 具体且有针对性\n2. 可能返回相关结果\n3. 与其他查询不同以涵盖各个方面\n\n只返回查询，每行一个，不要编号或额外文本。"
            },
            PromptType.RESEARCH_DRAFT: {
                "system": "你是一名专业研究员和作家。基于提供的研究数据，创建一个全面、结构良好的研究部分，彻底涵盖给定主题。你的写作应该：\n- 学术严谨但易于理解\n- 组织良好，结构清晰\n- 基于事实和证据\n- 在主要研究问题的背景下适当定位",
                "user_template": "主要研究问题：{main_query}\n部分主题：{topic}\n\n研究数据：\n{content_summary}\n\n写一个全面的研究部分，包括：\n1. 彻底涵盖主题\n2. 整合来自多个来源的发现\n3. 保持学术严谨性\n4. 提供清晰的分析和见解\n5. 与主要研究问题相关联\n\n用清晰的标题和逻辑流程构建内容。"
            },
            PromptType.INTRODUCTION_WRITING: {
                "system": "你是一名专业学术作家。为研究报告写一个引人入胜且信息丰富的引言，设定背景，解释主题的重要性，并概述报告将涵盖的内容。",
                "user_template": "研究主题：{title}\n研究问题：{query}\n\n计划的报告部分：\n{sections}\n\n初始研究背景：\n{initial_research}\n\n写一个全面的引言，包括：\n1. 建立主题的背景和重要性\n2. 清楚地陈述研究问题\n3. 概述报告的范围和结构\n4. 以引人入胜的开头吸引读者\n5. 设定适当的期望\n\n引言应该专业、结构良好，并为报告设定适当的期望。"
            },
            PromptType.CONCLUSION_WRITING: {
                "system": "你是一名专业学术作家。写一个全面的结论，综合研究发现，得出有意义的见解，并为研究报告提供令人满意的结尾。",
                "user_template": "研究主题：{title}\n研究问题：{query}\n\n主要报告内容摘要：\n{content_summary}\n\n写一个全面的结论，包括：\n1. 综合研究的关键发现\n2. 回答原始研究问题\n3. 得出有意义的见解和影响\n4. 在适当的地方承认局限性\n5. 建议未来研究或行动的领域\n\n结论应该将所有研究发现联系在一起，并提供与原始研究问题相关的清晰答案或见解。"
            },
            PromptType.RESEARCH_REVIEW: {
                "system": "你是一名专业研究评审员，具有评估研究质量、准确性和完整性的专业知识。对研究内容提供详细、建设性的反馈。重要提示：你必须只返回有效的JSON对象。不要包含任何markdown格式、代码块或JSON之外的额外文本。",
                "user_template": "研究主题：{topic}\n主要研究查询：{query}\n\n研究内容：\n{content}\n\n来源数量：{source_count}\n\n请根据以下标准评估此研究部分：\n1. 内容质量（深度、准确性、相关性）\n2. 来源覆盖（充足的来源、可信的来源）\n3. 逻辑结构和流程\n4. 主题覆盖的完整性\n5. 与主要研究查询的一致性\n\n以JSON对象形式提供你的评审：\n{{\n    \"topic\": \"{topic}\",\n    \"quality_score\": 0.0-1.0,\n    \"strengths\": [\"优势1\", \"优势2\", ...],\n    \"weaknesses\": [\"弱点1\", \"弱点2\", ...],\n    \"suggestions\": [\"建议1\", \"建议2\", ...],\n    \"overall_assessment\": \"简要整体评估\"\n}}"
            },
            PromptType.DRAFT_REVIEW: {
                "system": "你是一名专业编辑和内容评审员。评估草稿内容的质量、准确性、完整性和写作质量。提供具体、可操作的反馈。重要提示：你必须只返回有效的JSON对象。不要包含任何markdown格式、代码块或JSON之外的额外文本。",
                "user_template": "草稿主题：{topic}\n研究背景：{query}\n\n草稿内容：\n{content}\n\n请评审此草稿内容并评估：\n1. 写作质量（清晰度、流畅性、风格）\n2. 内容准确性和事实一致性\n3. 主题覆盖的完整性\n4. 逻辑结构和组织\n5. 与研究背景的相关性\n\n以JSON对象形式提供你的评审：\n{{\n    \"needs_revision\": true/false,\n    \"quality_score\": 0.0-1.0,\n    \"feedback\": \"详细反馈和具体建议\",\n    \"priority_issues\": [\"问题1\", \"问题2\", ...],\n    \"minor_suggestions\": [\"建议1\", \"建议2\", ...]\n}}\n\n只有在存在需要内容修改的重大问题时，才将needs_revision设置为true。"
            },
            PromptType.FINAL_REVIEW: {
                "system": "你是一名高级研究评审员，对完整的研究报告进行最终质量评估。从整体上评估报告的质量、连贯性和完整性。重要提示：你必须只返回有效的JSON对象。不要包含任何markdown格式、代码块或JSON之外的额外文本。",
                "user_template": "研究查询：{query}\n\n完整研究报告：\n{content}\n\n请提供全面的最终评审，评估：\n1. 整体报告质量和连贯性\n2. 研究覆盖的完整性\n3. 写作质量和专业标准\n4. 逻辑流程和结构\n5. 研究目标的实现\n\n以JSON对象形式提供你的评估：\n{{\n    \"overall_score\": 0.0-1.0,\n    \"summary\": \"简要整体评估\",\n    \"strengths\": [\"优势1\", \"优势2\", ...],\n    \"areas_for_improvement\": [\"改进领域1\", \"改进领域2\", ...],\n    \"recommendations\": [\"建议1\", \"建议2\", ...],\n    \"publication_ready\": true/false\n}}"
            },
            PromptType.OVERALL_FEEDBACK: {
                "system": "你是一名高级研究评审员。基于各个部分的评审结果，编制研究质量的整体评估。",
                "user_template": "研究项目：{query}\n平均质量分数：{avg_quality}\n\n部分评审摘要：\n- 总部分数：{total_sections}\n- 质量分数：{quality_scores}\n\n共同优势：\n{strengths}\n\n共同弱点：\n{weaknesses}\n\n改进建议：\n{suggestions}\n\n提供一个全面的整体评估（200-300字），包括：\n1. 总结研究的整体质量\n2. 突出各部分的关键优势\n3. 识别需要改进的领域\n4. 提供战略建议\n5. 给出整体质量评级"
            },
            PromptType.OUTLINE_GENERATION: {
                "system": "你是一名专业研究编辑，负责创建全面的研究大纲。你的任务是分析初始研究发现并为研究报告创建结构良好的大纲。重要提示：你必须只返回有效的JSON。不要包含任何解释性文本、markdown格式或额外内容。你的整个回复必须可以解析为JSON。",
                "user_template": "研究查询：{query}\n\n初始研究摘要：\n{initial_research}\n\n基于研究查询和初始发现，创建一个全面的研究大纲，包括：\n1. 研究报告的清晰、描述性标题\n2. {max_sections}个主要部分标题，逻辑地组织研究主题\n3. 部分应专注于实质性研究主题，而不是引言、结论或参考文献\n\n只返回此JSON结构（无其他文本）：\n{{\n    \"title\": \"研究报告标题\",\n    \"sections\": [\"部分1标题\", \"部分2标题\", \"部分3标题\"]\n}}\n\n部分要求：\n- 全面涵盖主题的关键方面\n- 逻辑有序\n- 足够具体以指导重点研究\n- 与回答主要研究问题相关\n\n重要：你的回复必须以{{开始，以}}结束。不要解释，不要markdown，不要额外文本。"
            },
            PromptType.EDITOR_DRAFT_REVIEW: {
                "system": "你是一名专业编辑和评审员。你的任务是评审研究草稿内容，并提供建设性反馈以提高质量、准确性和完整性。",
                "user_template": "主题：{topic}\n研究查询背景：{query}\n\n草稿内容：\n{content}\n\n请评审此草稿并提供以下方面的反馈：\n1. 内容质量和深度\n2. 准确性和事实一致性\n3. 逻辑结构和流程\n4. 覆盖的完整性\n5. 写作清晰度和风格\n\n以JSON对象形式返回你的回复：\n{{\n    \"needs_revision\": true/false,\n    \"feedback\": \"详细反馈和改进建议\",\n    \"quality_score\": 0.0-1.0\n}}\n\n如果草稿质量良好且不需要重大修订，请将needs_revision设置为false。"
            }
        }
    
    def _get_chinese_traditional_prompts(self) -> Dict[str, Dict[str, str]]:
        return {
            PromptType.RESEARCH_SUMMARY: {
                "system": "你是一名研究分析師，負責創建全面的研究發現摘要。你的目標是將來自多個來源的信息綜合成連貫、結構良好的摘要。重點關注關鍵見解、重要事實和與研究查詢相關的詳細信息。",
                "user_template": "研究查詢：{query}\n\n來自多個來源的研究內容：\n{content_summary}\n\n請創建一個全面的研究摘要，包括：\n1. 回答主要研究查詢\n2. 綜合來源的關鍵發現\n3. 識別重要模式或主題\n4. 突出任何衝突信息\n5. 提供平衡的觀點\n\n以清晰、結構良好的段落格式化摘要。"
            },
            PromptType.RESEARCH_QUERY_GENERATION: {
                "system": "你是一名研究查詢專家。生成具體、有針對性的搜索查詢，這些查詢將有助於在主要研究問題的背景下收集關於給定主題的全面信息。",
                "user_template": "主要研究查詢：{main_query}\n具體主題：{topic}\n\n生成3-5個具體的搜索查詢，這些查詢將有助於收集與主要研究問題相關的該主題的詳細信息。每個查詢應該：\n1. 具體且有針對性\n2. 可能返回相關結果\n3. 與其他查詢不同以涵蓋各個方面\n\n只返回查詢，每行一個，不要編號或額外文本。"
            },
            PromptType.RESEARCH_DRAFT: {
                "system": "你是一名專業研究員和作家。基於提供的研究數據，創建一個全面、結構良好的研究部分，徹底涵蓋給定主題。你的寫作應該：\n- 學術嚴謹但易於理解\n- 組織良好，結構清晰\n- 基於事實和證據\n- 在主要研究問題的背景下適當定位",
                "user_template": "主要研究問題：{main_query}\n部分主題：{topic}\n\n研究數據：\n{content_summary}\n\n寫一個全面的研究部分，包括：\n1. 徹底涵蓋主題\n2. 整合來自多個來源的發現\n3. 保持學術嚴謹性\n4. 提供清晰的分析和見解\n5. 與主要研究問題相關聯\n\n用清晰的標題和邏輯流程構建內容。"
            },
            PromptType.INTRODUCTION_WRITING: {
                "system": "你是一名專業學術作家。為研究報告寫一個引人入勝且信息豐富的引言，設定背景，解釋主題的重要性，並概述報告將涵蓋的內容。",
                "user_template": "研究主題：{title}\n研究問題：{query}\n\n計劃的報告部分：\n{sections}\n\n初始研究背景：\n{initial_research}\n\n寫一個全面的引言，包括：\n1. 建立主題的背景和重要性\n2. 清楚地陳述研究問題\n3. 概述報告的範圍和結構\n4. 以引人入勝的開頭吸引讀者\n5. 設定適當的期望\n\n引言應該專業、結構良好，並為報告設定適當的期望。"
            },
            PromptType.CONCLUSION_WRITING: {
                "system": "你是一名專業學術作家。寫一個全面的結論，綜合研究發現，得出有意義的見解，並為研究報告提供令人滿意的結尾。",
                "user_template": "研究主題：{title}\n研究問題：{query}\n\n主要報告內容摘要：\n{content_summary}\n\n寫一個全面的結論，包括：\n1. 綜合研究的關鍵發現\n2. 回答原始研究問題\n3. 得出有意義的見解和影響\n4. 在適當的地方承認局限性\n5. 建議未來研究或行動的領域\n\n結論應該將所有研究發現聯繫在一起，並提供與原始研究問題相關的清晰答案或見解。"
            },
            PromptType.OUTLINE_GENERATION: {
                "system": "你是一名專業研究編輯，負責創建全面的研究大綱。你的任務是分析初始研究發現並為研究報告創建結構良好的大綱。重要提示：你必須只返回有效的JSON。不要包含任何解釋性文本、markdown格式或額外內容。你的整個回復必須可以解析為JSON。",
                "user_template": "研究查詢：{query}\n\n初始研究摘要：\n{initial_research}\n\n基於研究查詢和初始發現，創建一個全面的研究大綱，包括：\n1. 研究報告的清晰、描述性標題\n2. {max_sections}個主要部分標題，邏輯地組織研究主題\n3. 部分應專注於實質性研究主題，而不是引言、結論或參考文獻\n\n只返回此JSON結構（無其他文本）：\n{{\n    \"title\": \"研究報告標題\",\n    \"sections\": [\"部分1標題\", \"部分2標題\", \"部分3標題\"]\n}}\n\n部分要求：\n- 全面涵蓋主題的關鍵方面\n- 邏輯有序\n- 足夠具體以指導重點研究\n- 與回答主要研究問題相關\n\n重要：你的回復必須以{{開始，以}}結束。不要解釋，不要markdown，不要額外文本。"
            },
            PromptType.EDITOR_DRAFT_REVIEW: {
                "system": "你是一名專業編輯和評審員。你的任務是評審研究草稿內容，並提供建設性反饋以提高質量、準確性和完整性。",
                "user_template": "主題：{topic}\n研究查詢背景：{query}\n\n草稿內容：\n{content}\n\n請評審此草稿並提供以下方面的反饋：\n1. 內容質量和深度\n2. 準確性和事實一致性\n3. 邏輯結構和流程\n4. 覆蓋的完整性\n5. 寫作清晰度和風格\n\n以JSON對象形式返回你的回復：\n{{\n    \"needs_revision\": true/false,\n    \"feedback\": \"詳細反饋和改進建議\",\n    \"quality_score\": 0.0-1.0\n}}\n\n如果草稿質量良好且不需要重大修訂，請將needs_revision設置為false。"
            }
        }

    def _get_japanese_prompts(self) -> Dict[str, Dict[str, str]]:
        return {
            PromptType.RESEARCH_SUMMARY: {
                "system": "あなたは研究分析者として、研究結果の包括的な要約を作成する任務を負っています。あなたの目標は、複数のソースからの情報を一貫性があり、よく構造化された要約に統合することです。研究クエリに対応する重要な洞察、重要な事実、関連する詳細に焦点を当ててください。",
                "user_template": "研究クエリ：{query}\n\n複数のソースからの研究内容：\n{content_summary}\n\n以下を含む包括的な研究要約を作成してください：\n1. 主要な研究クエリに対応する\n2. ソースからの重要な発見を統合する\n3. 重要なパターンやテーマを特定する\n4. 矛盾する情報を強調する\n5. バランスの取れた視点を提供する\n\n明確で構造化された段落で要約をフォーマットしてください。"
            },
            PromptType.RESEARCH_QUERY_GENERATION: {
                "system": "あなたは研究クエリの専門家です。主要な研究質問の文脈で、与えられたトピックについて包括的な情報を収集するのに役立つ、具体的で対象を絞った検索クエリを生成してください。",
                "user_template": "主要な研究クエリ：{main_query}\n具体的なトピック：{topic}\n\n主要な研究質問に関連してこのトピックの詳細情報を収集するのに役立つ3-5の具体的な検索クエリを生成してください。各クエリは以下であるべきです：\n1. 具体的で焦点を絞った\n2. 関連する結果を返す可能性が高い\n3. 様々な側面をカバーするために他のものと異なる\n\nクエリのみを返し、1行に1つ、番号付けや追加テキストなしで。"
            },
            PromptType.RESEARCH_DRAFT: {
                "system": "あなたは専門の研究者兼作家です。提供された研究データに基づいて、与えられたトピックを徹底的にカバーする包括的で構造化された研究セクションを作成してください。あなたの執筆は以下であるべきです：\n- 学術的に厳密だが理解しやすい\n- よく組織され、明確な構造を持つ\n- 事実と証拠に基づく\n- 主要な研究質問の文脈で適切に位置づけられる",
                "user_template": "主要な研究質問：{main_query}\nセクションのトピック：{topic}\n\n研究データ：\n{content_summary}\n\n以下を含む包括的な研究セクションを書いてください：\n1. トピックを徹底的にカバーする\n2. 複数のソースからの発見を統合する\n3. 学術的厳密性を維持する\n4. 明確な分析と洞察を提供する\n5. 主要な研究質問に関連付ける\n\n明確な見出しと論理的な流れでコンテンツを構成してください。"
            },
            PromptType.INTRODUCTION_WRITING: {
                "system": "あなたは専門の学術作家です。文脈を設定し、トピックの重要性を説明し、レポートがカバーする内容を概説する、研究レポートの魅力的で情報豊富な序論を書いてください。",
                "user_template": "研究トピック：{title}\n研究質問：{query}\n\n計画されたレポートセクション：\n{sections}\n\n初期研究の文脈：\n{initial_research}\n\n以下を含む包括的な序論を書いてください：\n1. トピックの文脈と重要性を確立する\n2. 研究質問を明確に述べる\n3. レポートの範囲と構造を概説する\n4. 魅力的な開始で読者を引き込む\n5. 適切な期待を設定する\n\n序論は専門的で構造化され、レポートに適切な期待を設定するべきです。"
            },
            PromptType.CONCLUSION_WRITING: {
                "system": "あなたは専門の学術作家です。研究結果を統合し、意味のある洞察を導き出し、研究レポートに満足のいく結論を提供する包括的な結論を書いてください。",
                "user_template": "研究トピック：{title}\n研究質問：{query}\n\n主要なレポート内容の要約：\n{content_summary}\n\n以下を含む包括的な結論を書いてください：\n1. 研究の重要な発見を統合する\n2. 元の研究質問に対応する\n3. 意味のある洞察と含意を導き出す\n4. 適切な場合は限界を認める\n5. 将来の研究や行動の領域を提案する\n\n結論はすべての研究結果をまとめ、元の研究質問に関連する明確な答えや洞察を提供するべきです。"
            },
            PromptType.OUTLINE_GENERATION: {
                "system": "あなたは包括的な研究アウトラインの作成を担当する専門の研究編集者です。あなたの任務は、初期研究結果を分析し、研究レポートのための構造化されたアウトラインを作成することです。重要：有効なJSONのみで応答する必要があります。説明テキスト、マークダウン形式、または追加コンテンツを含めないでください。あなたの応答全体がJSONとして解析可能である必要があります。",
                "user_template": "研究クエリ：{query}\n\n初期研究要約：\n{initial_research}\n\n研究クエリと初期発見に基づいて、以下を含む包括的な研究アウトラインを作成してください：\n1. 研究レポートの明確で説明的なタイトル\n2. 研究トピックを論理的に整理する{max_sections}つの主要セクションヘッダー\n3. セクションは序論、結論、参考文献ではなく、実質的な研究トピックに焦点を当てるべきです\n\nこのJSON構造のみを返してください（他のテキストなし）：\n{{\n    \"title\": \"研究レポートタイトル\",\n    \"sections\": [\"セクション1タイトル\", \"セクション2タイトル\", \"セクション3タイトル\"]\n}}\n\nセクションの要件：\n- トピックの主要な側面を包括的にカバーする\n- 論理的に順序付けられている\n- 焦点を絞った研究を導くのに十分具体的\n- 主要な研究質問への回答に関連している\n\n重要：あなたの応答は{{で始まり}}で終わる必要があります。説明なし、マークダウンなし、追加テキストなし。"
            },
            PromptType.EDITOR_DRAFT_REVIEW: {
                "system": "あなたは専門の編集者兼レビュアーです。あなたの任務は、研究草稿の内容をレビューし、品質、正確性、完全性を向上させるための建設的なフィードバックを提供することです。",
                "user_template": "トピック：{topic}\n研究クエリの背景：{query}\n\n草稿内容：\n{content}\n\nこの草稿をレビューし、以下の点についてフィードバックを提供してください：\n1. 内容の質と深さ\n2. 正確性と事実の一貫性\n3. 論理的構造と流れ\n4. カバレッジの完全性\n5. 文章の明確さとスタイル\n\nJSONオブジェクトとして応答を返してください：\n{{\n    \"needs_revision\": true/false,\n    \"feedback\": \"詳細なフィードバックと改善提案\",\n    \"quality_score\": 0.0-1.0\n}}\n\n草稿が良質で大幅な修正が不要な場合は、needs_revisionをfalseに設定してください。"
            }
        }

    def _get_korean_prompts(self) -> Dict[str, Dict[str, str]]:
        return {
            PromptType.RESEARCH_SUMMARY: {
                "system": "당신은 연구 결과의 포괄적인 요약을 작성하는 임무를 맡은 연구 분석가입니다. 당신의 목표는 여러 출처의 정보를 일관성 있고 잘 구조화된 요약으로 종합하는 것입니다. 연구 쿼리와 관련된 핵심 통찰, 중요한 사실, 관련 세부사항에 집중하세요.",
                "user_template": "연구 쿼리: {query}\n\n여러 출처의 연구 내용:\n{content_summary}\n\n다음을 포함하는 포괄적인 연구 요약을 작성하세요:\n1. 주요 연구 쿼리에 대응\n2. 출처의 핵심 발견 종합\n3. 중요한 패턴이나 주제 식별\n4. 상충하는 정보 강조\n5. 균형 잡힌 관점 제공\n\n명확하고 잘 구조화된 단락으로 요약을 형식화하세요."
            },
            PromptType.RESEARCH_QUERY_GENERATION: {
                "system": "당신은 연구 쿼리 전문가입니다. 주요 연구 질문의 맥락에서 주어진 주제에 대한 포괄적인 정보를 수집하는 데 도움이 될 구체적이고 표적화된 검색 쿼리를 생성하세요.",
                "user_template": "주요 연구 쿼리: {main_query}\n구체적인 주제: {topic}\n\n주요 연구 질문과 관련하여 이 주제의 상세한 정보를 수집하는 데 도움이 될 3-5개의 구체적인 검색 쿼리를 생성하세요. 각 쿼리는 다음과 같아야 합니다:\n1. 구체적이고 집중된\n2. 관련 결과를 반환할 가능성이 높은\n3. 다양한 측면을 다루기 위해 다른 것들과 다른\n\n쿼리만 반환하고, 한 줄에 하나씩, 번호나 추가 텍스트 없이."
            },
            PromptType.RESEARCH_DRAFT: {
                "system": "당신은 전문 연구자이자 작가입니다. 제공된 연구 데이터를 바탕으로 주어진 주제를 철저히 다루는 포괄적이고 잘 구조화된 연구 섹션을 작성하세요. 당신의 글쓰기는 다음과 같아야 합니다:\n- 학술적으로 엄격하지만 접근 가능한\n- 잘 조직되고 명확한 구조를 가진\n- 사실과 증거에 기반한\n- 주요 연구 질문의 맥락에서 적절히 위치한",
                "user_template": "주요 연구 질문: {main_query}\n섹션 주제: {topic}\n\n연구 데이터:\n{content_summary}\n\n다음을 포함하는 포괄적인 연구 섹션을 작성하세요:\n1. 주제를 철저히 다루기\n2. 여러 출처의 발견을 통합하기\n3. 학술적 엄격성 유지하기\n4. 명확한 분석과 통찰 제공하기\n5. 주요 연구 질문과 연결하기\n\n명확한 제목과 논리적 흐름으로 내용을 구성하세요."
            },
            PromptType.INTRODUCTION_WRITING: {
                "system": "당신은 전문 학술 작가입니다. 맥락을 설정하고, 주제의 중요성을 설명하며, 보고서가 다룰 내용을 개요하는 연구 보고서의 매력적이고 정보가 풍부한 서론을 작성하세요.",
                "user_template": "연구 주제: {title}\n연구 질문: {query}\n\n계획된 보고서 섹션:\n{sections}\n\n초기 연구 맥락:\n{initial_research}\n\n다음을 포함하는 포괄적인 서론을 작성하세요:\n1. 주제의 맥락과 중요성 확립\n2. 연구 질문을 명확히 진술\n3. 보고서의 범위와 구조 개요\n4. 매력적인 시작으로 독자 참여\n5. 적절한 기대 설정\n\n서론은 전문적이고 잘 구조화되어야 하며, 보고서에 대한 적절한 기대를 설정해야 합니다."
            },
            PromptType.CONCLUSION_WRITING: {
                "system": "당신은 전문 학술 작가입니다. 연구 결과를 종합하고, 의미 있는 통찰을 도출하며, 연구 보고서에 만족스러운 결론을 제공하는 포괄적인 결론을 작성하세요.",
                "user_template": "연구 주제: {title}\n연구 질문: {query}\n\n주요 보고서 내용 요약:\n{content_summary}\n\n다음을 포함하는 포괄적인 결론을 작성하세요:\n1. 연구의 핵심 발견 종합\n2. 원래 연구 질문에 대응\n3. 의미 있는 통찰과 함의 도출\n4. 적절한 경우 한계 인정\n5. 미래 연구나 행동 영역 제안\n\n결론은 모든 연구 결과를 연결하고 원래 연구 질문과 관련된 명확한 답변이나 통찰을 제공해야 합니다."
            },
            PromptType.OUTLINE_GENERATION: {
                "system": "당신은 포괄적인 연구 개요 작성을 담당하는 전문 연구 편집자입니다. 당신의 임무는 초기 연구 결과를 분석하고 연구 보고서를 위한 잘 구조화된 개요를 작성하는 것입니다. 중요: 유효한 JSON으로만 응답해야 합니다. 설명 텍스트, 마크다운 형식 또는 추가 콘텐츠를 포함하지 마세요. 전체 응답이 JSON으로 파싱 가능해야 합니다.",
                "user_template": "연구 쿼리: {query}\n\n초기 연구 요약:\n{initial_research}\n\n연구 쿼리와 초기 발견을 바탕으로 다음을 포함하는 포괄적인 연구 개요를 작성하세요:\n1. 연구 보고서의 명확하고 설명적인 제목\n2. 연구 주제를 논리적으로 구성하는 {max_sections}개의 주요 섹션 헤더\n3. 섹션은 서론, 결론, 참고문헌이 아닌 실질적인 연구 주제에 집중해야 합니다\n\n이 JSON 구조만 반환하세요(다른 텍스트 없이):\n{{\n    \"title\": \"연구 보고서 제목\",\n    \"sections\": [\"섹션 1 제목\", \"섹션 2 제목\", \"섹션 3 제목\"]\n}}\n\n섹션 요구사항:\n- 주제의 핵심 측면을 포괄적으로 다루기\n- 논리적으로 순서가 정해진\n- 집중된 연구를 안내할 만큼 구체적\n- 주요 연구 질문 답변과 관련된\n\n중요: 응답은 {{로 시작하고 }}로 끝나야 합니다. 설명 없음, 마크다운 없음, 추가 텍스트 없음."
            },
            PromptType.EDITOR_DRAFT_REVIEW: {
                "system": "당신은 전문 편집자이자 검토자입니다. 당신의 임무는 연구 초안 내용을 검토하고 품질, 정확성, 완전성을 향상시키기 위한 건설적인 피드백을 제공하는 것입니다.",
                "user_template": "주제: {topic}\n연구 쿼리 배경: {query}\n\n초안 내용:\n{content}\n\n이 초안을 검토하고 다음 사항에 대한 피드백을 제공하세요:\n1. 내용 품질과 깊이\n2. 정확성과 사실 일관성\n3. 논리적 구조와 흐름\n4. 커버리지의 완전성\n5. 글쓰기 명확성과 스타일\n\nJSON 객체로 응답을 반환하세요:\n{{\n    \"needs_revision\": true/false,\n    \"feedback\": \"상세한 피드백과 개선 제안\",\n    \"quality_score\": 0.0-1.0\n}}\n\n초안이 양질이고 주요 수정이 필요하지 않다면 needs_revision을 false로 설정하세요."
            }
        }

    def _load_prompt_files(self):
        """Load prompt files from disk."""
        for prompt_file in self.prompts_dir.glob("*_prompts.json"):
            try:
                lang_code = prompt_file.stem.replace("_prompts", "")
                with open(prompt_file, 'r', encoding='utf-8') as f:
                    prompt_data = json.load(f)
                    self.prompts[lang_code] = prompt_data
                logger.info(f"Loaded prompts for language: {lang_code}")
            except Exception as e:
                logger.warning(f"Failed to load prompt file {prompt_file}: {str(e)}")

    def _create_fallback_prompts(self):
        """Create fallback English prompts if loading fails."""
        self.prompts["en"] = self._get_english_prompts()
        logger.info("Created fallback English prompts")

    def get_prompt(self, prompt_type: PromptType, language_code: Optional[str] = None) -> Dict[str, str]:
        """Get a prompt template for the specified type and language."""
        if language_code is None:
            language_code = self.language_manager.current_language.value

        # Try to get prompt for requested language
        if language_code in self.prompts and prompt_type in self.prompts[language_code]:
            return self.prompts[language_code][prompt_type]

        # Fallback to English
        if "en" in self.prompts and prompt_type in self.prompts["en"]:
            logger.warning(f"Prompt {prompt_type} not found for {language_code}, using English fallback")
            return self.prompts["en"][prompt_type]

        # Ultimate fallback
        logger.error(f"Prompt {prompt_type} not found for any language")
        return {
            "system": "You are a helpful assistant.",
            "user_template": "{query}"
        }

    def format_prompt(self, prompt_type: PromptType, language_code: Optional[str] = None, **kwargs) -> tuple[str, str]:
        """Format a prompt with the provided parameters."""
        prompt_template = self.get_prompt(prompt_type, language_code)

        system_prompt = prompt_template.get("system", "")
        user_template = prompt_template.get("user_template", "{query}")

        try:
            user_prompt = user_template.format(**kwargs)
        except KeyError as e:
            logger.error(f"Missing parameter for prompt formatting: {str(e)}")
            user_prompt = user_template

        return system_prompt, user_prompt

    def set_language(self, language_code: str) -> bool:
        """Set the current language for prompt generation."""
        return self.language_manager.set_language(language_code)

    def get_current_language(self) -> str:
        """Get the current language code."""
        return self.language_manager.current_language.value

    def list_supported_languages(self) -> List[Dict[str, str]]:
        """List all supported languages."""
        return self.language_manager.list_supported_languages()


def create_prompt_manager(localization_dir: str = "./localization") -> MultilingualPromptManager:
    """Factory function to create a MultilingualPromptManager instance."""
    return MultilingualPromptManager(localization_dir)

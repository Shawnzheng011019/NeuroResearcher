import asyncio
import logging
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from templates import create_template_manager, DocumentTemplate, SectionTemplate, CitationTemplate, CitationStyle
from localization import create_language_manager, SupportedLanguage
from config import TaskConfig, Tone
from main import ResearchRunner

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def demo_template_management():
    print("🔧 Template Management Demo")
    print("=" * 50)
    
    # Create template manager
    template_manager = create_template_manager()
    
    # List available templates
    templates = template_manager.list_templates()
    print(f"Available templates: {templates}")
    
    # Get default template
    default_template = template_manager.get_default_template()
    print(f"Default template: {default_template.name}")
    print(f"Sections: {[s.name for s in default_template.sections]}")
    
    # Create custom template
    custom_sections = [
        SectionTemplate("overview", "Overview", 1),
        SectionTemplate("analysis", "Detailed Analysis", 2),
        SectionTemplate("implications", "Implications", 3),
        SectionTemplate("recommendations", "Recommendations", 4)
    ]
    
    custom_citation = CitationTemplate(
        style=CitationStyle.IEEE,
        format_string="[{number}] {author}, \"{title},\" {source}, {year}.",
        bibliography_format="[{number}] {author}, \"{title},\" {source}, {year}.",
        in_text_format="[{number}]"
    )
    
    custom_template = DocumentTemplate(
        name="custom_research",
        description="Custom research template for demo",
        sections=custom_sections,
        citation=custom_citation
    )
    
    # Add and save custom template
    template_manager.add_template(custom_template)
    template_manager.save_template(custom_template)
    print(f"Created and saved custom template: {custom_template.name}")


async def demo_language_management():
    print("\n🌍 Language Management Demo")
    print("=" * 50)
    
    # Create language manager
    language_manager = create_language_manager()
    
    # List supported languages
    languages = language_manager.list_supported_languages()
    print("Supported languages:")
    for lang in languages:
        print(f"  - {lang['name']} ({lang['code']}): {lang['native_name']}")
    
    # Test translations
    test_keys = ["title", "introduction", "conclusion", "references"]
    
    for lang_code in ["en", "zh-cn", "ja", "ko"]:
        language_manager.set_language(lang_code)
        lang_config = language_manager.get_current_language()
        print(f"\n{lang_config.native_name} translations:")
        
        for key in test_keys:
            translation = language_manager.translate(key)
            print(f"  {key}: {translation}")


async def demo_multilingual_research():
    print("\n📝 Multilingual Research Demo")
    print("=" * 50)
    
    # Test different languages
    test_configs = [
        {
            "query": "What are the latest developments in artificial intelligence?",
            "language": "en",
            "template": "default"
        },
        {
            "query": "人工智能的最新发展是什么？",
            "language": "zh-cn",
            "template": "academic"
        },
        {
            "query": "人工知能の最新の発展は何ですか？",
            "language": "ja",
            "template": "default"
        }
    ]
    
    runner = ResearchRunner()
    
    for i, config in enumerate(test_configs, 1):
        print(f"\nTest {i}: {config['language'].upper()}")
        print(f"Query: {config['query']}")
        print(f"Template: {config['template']}")
        
        try:
            # Create task configuration
            task_config = TaskConfig(
                query=config["query"],
                max_sections=3,
                publish_formats={"markdown": True},
                model="gpt-4o-mini",
                tone=Tone.OBJECTIVE,
                verbose=False,
                template_name=config["template"],
                language=config["language"]
            )
            
            # Note: This would run actual research - commented out for demo
            # result = await runner.run_research_from_config(task_config)
            # print(f"Research completed: {result.get('status', 'unknown')}")
            
            print("✅ Configuration created successfully")
            
        except Exception as e:
            print(f"❌ Error: {str(e)}")


async def demo_custom_template_research():
    print("\n🎨 Custom Template Research Demo")
    print("=" * 50)
    
    # Load custom template from file
    custom_template_path = Path("examples/custom_template_example.yaml")
    
    if custom_template_path.exists():
        print(f"Loading custom template from: {custom_template_path}")
        
        # Create task with custom template
        task_config = TaskConfig(
            query="Market analysis of electric vehicle industry",
            max_sections=5,
            publish_formats={"markdown": True, "pdf": True},
            model="gpt-4o-mini",
            tone=Tone.ANALYTICAL,
            verbose=False,
            template_name="business_report",
            language="en",
            citation_style="harvard"
        )
        
        print("✅ Custom template task configuration created")
        print(f"Template: {task_config.template_name}")
        print(f"Language: {task_config.language}")
        print(f"Citation style: {task_config.citation_style}")
    else:
        print(f"❌ Custom template file not found: {custom_template_path}")


async def main():
    print("🚀 Template and Localization System Demo")
    print("=" * 60)
    
    try:
        await demo_template_management()
        await demo_language_management()
        await demo_multilingual_research()
        await demo_custom_template_research()
        
        print("\n✅ Demo completed successfully!")
        print("\nFeatures demonstrated:")
        print("  - Template management and customization")
        print("  - Multi-language support (EN, ZH-CN, ZH-TW, JA, KO)")
        print("  - Custom citation styles")
        print("  - Localized section titles and metadata")
        print("  - YAML/JSON template configuration")
        
    except Exception as e:
        print(f"\n❌ Demo failed: {str(e)}")
        logger.exception("Demo error details:")


if __name__ == "__main__":
    asyncio.run(main())

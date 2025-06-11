#!/usr/bin/env python3
"""
Long Text Processing Demo

This script demonstrates the enhanced long text processing capabilities
with chunked summarization and merging strategies.
"""

import asyncio
import logging
import sys
import os
from pathlib import Path

# Add the parent directory to the path to import modules
sys.path.append(str(Path(__file__).parent.parent))

from config import get_config
from tools.long_text_processor import create_long_text_processor
from tools.summarization_tools import create_summarization_tool
from tools.text_chunking_strategies import create_chunking_strategy

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def demo_chunking_strategies():
    """Demonstrate different chunking strategies"""
    print("\n" + "="*60)
    print("CHUNKING STRATEGIES DEMO")
    print("="*60)
    
    # Sample long text
    sample_text = """
    Artificial Intelligence (AI) has emerged as one of the most transformative technologies of the 21st century. 
    From its humble beginnings in the 1950s with Alan Turing's seminal work on machine intelligence, AI has evolved 
    into a sophisticated field encompassing machine learning, deep learning, natural language processing, and computer vision.
    
    The current landscape of AI is dominated by large language models (LLMs) such as GPT-4, Claude, and Gemini. 
    These models have demonstrated remarkable capabilities in understanding and generating human-like text, 
    solving complex problems, and even exhibiting forms of reasoning that were previously thought to be 
    uniquely human capabilities.
    
    Machine learning, a subset of AI, focuses on algorithms that can learn and improve from experience without 
    being explicitly programmed. Deep learning, a further subset of machine learning, uses neural networks 
    with multiple layers to model and understand complex patterns in data. This approach has been particularly 
    successful in image recognition, speech processing, and natural language understanding.
    
    Natural Language Processing (NLP) is another crucial area of AI that deals with the interaction between 
    computers and human language. Recent advances in NLP have led to the development of sophisticated chatbots, 
    translation systems, and text analysis tools that can understand context, sentiment, and even generate 
    creative content.
    
    Computer vision, the field concerned with enabling machines to interpret and understand visual information, 
    has seen tremendous progress with the advent of convolutional neural networks (CNNs) and transformer 
    architectures. Applications range from autonomous vehicles to medical image analysis and facial recognition systems.
    
    The ethical implications of AI development cannot be overlooked. Issues such as bias in AI systems, 
    privacy concerns, job displacement, and the potential for misuse of AI technologies have sparked important 
    discussions about responsible AI development and deployment. Organizations and governments worldwide are 
    working to establish guidelines and regulations to ensure AI is developed and used in ways that benefit humanity.
    
    Looking towards the future, AI is expected to continue its rapid evolution. Emerging areas such as 
    quantum machine learning, neuromorphic computing, and artificial general intelligence (AGI) promise 
    to push the boundaries of what's possible with AI. The integration of AI into various sectors including 
    healthcare, education, finance, and entertainment will likely accelerate, bringing both opportunities 
    and challenges.
    
    The democratization of AI tools and platforms has made it easier for individuals and organizations 
    to leverage AI capabilities without requiring deep technical expertise. This trend is expected to 
    continue, making AI more accessible and fostering innovation across diverse fields and applications.
    """ * 3  # Repeat to make it longer
    
    metadata = {
        "doc_id": "ai_overview_demo",
        "source": "demo_text",
        "type": "educational"
    }
    
    strategies = ["semantic", "document_type", "adaptive"]
    
    for strategy_name in strategies:
        print(f"\n--- {strategy_name.upper()} CHUNKING STRATEGY ---")
        
        strategy = create_chunking_strategy(strategy_name, max_chunk_size=1000)
        chunks = await strategy.chunk_text(sample_text, metadata)
        
        print(f"Number of chunks created: {len(chunks)}")
        print(f"Average chunk size: {sum(len(c['content']) for c in chunks) / len(chunks):.0f} characters")
        
        # Show first chunk as example
        if chunks:
            first_chunk = chunks[0]
            print(f"First chunk preview: {first_chunk['content'][:200]}...")
            print(f"Chunk metadata: {first_chunk['metadata'].get('chunk_type', 'N/A')}")


async def demo_summarization_strategies():
    """Demonstrate different summarization strategies"""
    print("\n" + "="*60)
    print("SUMMARIZATION STRATEGIES DEMO")
    print("="*60)
    
    config = get_config()
    summarization_tool = create_summarization_tool(config)
    
    # Sample text for summarization
    sample_text = """
    Climate change represents one of the most pressing challenges facing humanity in the 21st century. 
    The scientific consensus is clear: human activities, particularly the emission of greenhouse gases 
    from burning fossil fuels, are driving unprecedented changes in Earth's climate system.
    
    The evidence for climate change is overwhelming and multifaceted. Global average temperatures 
    have risen by approximately 1.1 degrees Celsius since the late 19th century, with the most 
    rapid warming occurring in recent decades. Arctic sea ice is declining at a rate of about 
    13% per decade, and glaciers worldwide are retreating at accelerating rates.
    
    The impacts of climate change are already being felt across the globe. More frequent and 
    intense heatwaves, droughts, and extreme weather events are affecting agriculture, water 
    resources, and human health. Sea level rise threatens coastal communities and infrastructure, 
    while changing precipitation patterns are altering ecosystems and biodiversity.
    
    Addressing climate change requires urgent and coordinated action at all levels of society. 
    The transition to renewable energy sources, improvement in energy efficiency, and development 
    of carbon capture technologies are essential components of climate mitigation strategies. 
    Additionally, adaptation measures are needed to help communities and ecosystems cope with 
    the changes that are already underway.
    
    International cooperation through agreements like the Paris Climate Accord provides a 
    framework for global action, but implementation remains challenging. Individual actions, 
    while important, must be complemented by systemic changes in policy, technology, and 
    economic structures to achieve the scale of transformation required.
    """
    
    strategies = ["extractive", "abstractive", "hybrid", "topic_aware"]
    
    for strategy in strategies:
        print(f"\n--- {strategy.upper()} SUMMARIZATION ---")
        
        try:
            result = await summarization_tool.summarize_text(
                sample_text, 
                strategy=strategy, 
                max_length=300
            )
            
            print(f"Summary: {result['summary']}")
            print(f"Compression ratio: {result['metadata'].compression_ratio:.2f}")
            print(f"Quality score: {result['metadata'].quality_score:.2f}")
            print(f"Processing time: {result['metadata'].processing_time:.2f}s")
            
        except Exception as e:
            print(f"Error with {strategy} strategy: {str(e)}")


async def demo_long_text_processing():
    """Demonstrate complete long text processing pipeline"""
    print("\n" + "="*60)
    print("LONG TEXT PROCESSING PIPELINE DEMO")
    print("="*60)
    
    config = get_config()
    
    # Check if we have API keys configured
    if not config.openai_api_key and not config.anthropic_api_key:
        print("⚠️  No API keys configured. Please set OPENAI_API_KEY or ANTHROPIC_API_KEY in your .env file")
        print("This demo requires LLM access for summarization.")
        return
    
    processor = create_long_text_processor(config)
    
    # Create a longer sample text
    long_text = """
    The field of quantum computing represents a paradigm shift in computational capabilities, 
    promising to solve certain classes of problems exponentially faster than classical computers. 
    Unlike classical bits that exist in definite states of 0 or 1, quantum bits (qubits) can 
    exist in superposition states, allowing them to represent both 0 and 1 simultaneously.
    
    This quantum mechanical property, along with entanglement and interference, enables quantum 
    computers to perform certain calculations with unprecedented efficiency. Quantum algorithms 
    such as Shor's algorithm for factoring large numbers and Grover's algorithm for searching 
    unsorted databases demonstrate the potential for quantum advantage in specific domains.
    
    The development of quantum computing faces significant technical challenges. Quantum states 
    are extremely fragile and susceptible to decoherence from environmental interference. 
    Maintaining quantum coherence requires sophisticated error correction techniques and 
    ultra-low temperature environments, often approaching absolute zero.
    
    Current quantum computing approaches include superconducting circuits, trapped ions, 
    topological qubits, and photonic systems. Each approach has its own advantages and 
    challenges in terms of scalability, error rates, and operational requirements. 
    Companies like IBM, Google, and IonQ are leading the development of different quantum 
    computing platforms.
    
    The potential applications of quantum computing span numerous fields. In cryptography, 
    quantum computers could break current encryption methods while enabling new forms of 
    quantum-safe cryptography. In drug discovery, quantum simulations could model molecular 
    interactions with unprecedented accuracy. Financial modeling, optimization problems, 
    and machine learning could all benefit from quantum acceleration.
    
    However, we are still in the early stages of quantum computing development. Current 
    quantum computers are in the Noisy Intermediate-Scale Quantum (NISQ) era, characterized 
    by limited qubit counts and high error rates. Achieving fault-tolerant quantum computing 
    with millions of logical qubits remains a significant engineering challenge.
    
    The quantum computing ecosystem is rapidly evolving, with increasing investment from 
    governments and private companies. Quantum programming languages, development frameworks, 
    and cloud-based quantum computing services are making the technology more accessible 
    to researchers and developers.
    
    As quantum computing matures, it will likely complement rather than replace classical 
    computing. Hybrid quantum-classical algorithms are being developed to leverage the 
    strengths of both paradigms. The future of computing may well be quantum-enhanced, 
    with quantum processors handling specific computational tasks while classical computers 
    manage the overall system orchestration.
    
    Education and workforce development in quantum computing are becoming increasingly 
    important. Universities are establishing quantum computing programs, and companies 
    are investing in quantum literacy for their technical teams. The quantum advantage 
    will ultimately depend not just on hardware advances but also on our ability to 
    develop quantum algorithms and applications that solve real-world problems.
    """ * 4  # Make it even longer
    
    metadata = {
        "doc_id": "quantum_computing_overview",
        "source": "demo_document",
        "context": "Educational material on quantum computing",
        "type": "technical"
    }
    
    processing_options = {
        "strategy": "hybrid",
        "max_summary_length": 500
    }
    
    print(f"Processing text with {len(long_text)} characters...")
    
    try:
        result = await processor.process_long_text(
            long_text, 
            metadata, 
            processing_options
        )
        
        print(f"\n--- PROCESSING RESULTS ---")
        print(f"Original length: {result.processing_metadata['original_length']} characters")
        print(f"Final summary length: {result.processing_metadata['final_summary_length']} characters")
        print(f"Compression ratio: {result.processing_metadata['compression_ratio']:.3f}")
        print(f"Number of chunks: {result.processing_metadata['chunk_count']}")
        print(f"Processing time: {result.processing_metadata['processing_time']:.2f} seconds")
        
        print(f"\n--- FINAL SUMMARY ---")
        print(result.final_summary)
        
        print(f"\n--- CHUNK SUMMARIES ---")
        for i, chunk_summary in enumerate(result.chunk_summaries[:3]):  # Show first 3
            print(f"Chunk {i+1} summary: {chunk_summary['summary'][:200]}...")
        
        if len(result.chunk_summaries) > 3:
            print(f"... and {len(result.chunk_summaries) - 3} more chunk summaries")
        
        # Show processing stats
        stats = await processor.get_processing_stats()
        print(f"\n--- PROCESSING STATS ---")
        print(f"Total LLM cost: ${stats['total_cost']:.4f}")
        print(f"Configuration used: {stats['config']}")
        
    except Exception as e:
        print(f"Error during long text processing: {str(e)}")
        logger.exception("Long text processing failed")


async def main():
    """Main demo function"""
    print("🚀 Long Text Processing Demo")
    print("This demo showcases enhanced text chunking and summarization capabilities")
    
    try:
        # Demo 1: Chunking strategies
        await demo_chunking_strategies()
        
        # Demo 2: Summarization strategies  
        await demo_summarization_strategies()
        
        # Demo 3: Complete long text processing pipeline
        await demo_long_text_processing()
        
        print("\n" + "="*60)
        print("✅ Demo completed successfully!")
        print("="*60)
        
    except Exception as e:
        print(f"\n❌ Demo failed with error: {str(e)}")
        logger.exception("Demo execution failed")


if __name__ == "__main__":
    asyncio.run(main())

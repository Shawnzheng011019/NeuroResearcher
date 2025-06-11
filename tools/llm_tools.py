import asyncio
from typing import Dict, Any, Optional, List
from abc import ABC, abstractmethod
import openai
import anthropic
import logging
from config import Config

logger = logging.getLogger(__name__)


class LLMTool(ABC):
    def __init__(self, model: str, max_tokens: int = 4000, temperature: float = 0.7):
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.cost = 0.0
    
    @abstractmethod
    async def generate(self, prompt: str, system_prompt: Optional[str] = None, **kwargs) -> str:
        pass
    
    @abstractmethod
    def calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        pass
    
    def get_total_cost(self) -> float:
        return self.cost


class OpenAITool(LLMTool):
    def __init__(self, api_key: str, model: str = "gpt-4o", max_tokens: int = 4000, temperature: float = 0.7):
        super().__init__(model, max_tokens, temperature)
        self.client = openai.AsyncOpenAI(api_key=api_key)
        
        # Pricing per 1K tokens (as of 2024)
        self.pricing = {
            "gpt-4o": {"input": 0.005, "output": 0.015},
            "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
            "gpt-4": {"input": 0.03, "output": 0.06},
            "gpt-3.5-turbo": {"input": 0.001, "output": 0.002}
        }
    
    async def generate(self, prompt: str, system_prompt: Optional[str] = None, **kwargs) -> str:
        try:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                **kwargs
            )
            
            # Calculate and track cost
            usage = response.usage
            if usage:
                cost = self.calculate_cost(usage.prompt_tokens, usage.completion_tokens)
                self.cost += cost
                logger.info(f"OpenAI API call cost: ${cost:.4f} (Total: ${self.cost:.4f})")
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"OpenAI API error: {str(e)}")
            raise
    
    def calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        model_pricing = self.pricing.get(self.model, self.pricing["gpt-4o"])
        input_cost = (input_tokens / 1000) * model_pricing["input"]
        output_cost = (output_tokens / 1000) * model_pricing["output"]
        return input_cost + output_cost


class AnthropicTool(LLMTool):
    def __init__(self, api_key: str, model: str = "claude-3-sonnet-20240229", max_tokens: int = 4000, temperature: float = 0.7):
        super().__init__(model, max_tokens, temperature)
        self.client = anthropic.AsyncAnthropic(api_key=api_key)
        
        # Pricing per 1K tokens (as of 2024)
        self.pricing = {
            "claude-3-opus-20240229": {"input": 0.015, "output": 0.075},
            "claude-3-sonnet-20240229": {"input": 0.003, "output": 0.015},
            "claude-3-haiku-20240307": {"input": 0.00025, "output": 0.00125}
        }
    
    async def generate(self, prompt: str, system_prompt: Optional[str] = None, **kwargs) -> str:
        try:
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                system=system_prompt or "",
                messages=[{"role": "user", "content": prompt}],
                **kwargs
            )
            
            # Calculate and track cost
            usage = response.usage
            if usage:
                cost = self.calculate_cost(usage.input_tokens, usage.output_tokens)
                self.cost += cost
                logger.info(f"Anthropic API call cost: ${cost:.4f} (Total: ${self.cost:.4f})")
            
            return response.content[0].text
            
        except Exception as e:
            logger.error(f"Anthropic API error: {str(e)}")
            raise
    
    def calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        model_pricing = self.pricing.get(self.model, self.pricing["claude-3-sonnet-20240229"])
        input_cost = (input_tokens / 1000) * model_pricing["input"]
        output_cost = (output_tokens / 1000) * model_pricing["output"]
        return input_cost + output_cost


class LLMManager:
    def __init__(self, config: Config):
        self.config = config
        self.tools = {}
        self._initialize_tools()
    
    def _initialize_tools(self):
        # Initialize OpenAI tools
        if self.config.openai_api_key:
            self.tools["openai_fast"] = OpenAITool(
                api_key=self.config.openai_api_key,
                model=self.config.fast_llm_model,
                temperature=0.7
            )
            self.tools["openai_smart"] = OpenAITool(
                api_key=self.config.openai_api_key,
                model=self.config.smart_llm_model,
                temperature=0.7
            )
            self.tools["openai_strategic"] = OpenAITool(
                api_key=self.config.openai_api_key,
                model=self.config.strategic_llm_model,
                temperature=0.3
            )
        
        # Initialize Anthropic tools
        if self.config.anthropic_api_key:
            self.tools["anthropic"] = AnthropicTool(
                api_key=self.config.anthropic_api_key,
                model="claude-3-sonnet-20240229",
                temperature=0.7
            )
    
    def get_tool(self, tool_type: str = "smart") -> LLMTool:
        if self.config.llm_provider.value == "openai":
            tool_key = f"openai_{tool_type}"
        elif self.config.llm_provider.value == "anthropic":
            tool_key = "anthropic"
        else:
            tool_key = f"openai_{tool_type}"  # Default fallback
        
        tool = self.tools.get(tool_key)
        if not tool:
            # Fallback to any available tool
            if self.tools:
                tool = list(self.tools.values())[0]
                logger.warning(f"Requested tool '{tool_key}' not available, using fallback: {type(tool).__name__}")
            else:
                raise ValueError("No LLM tools available. Please configure API keys.")
        
        return tool
    
    async def generate_with_fallback(self, prompt: str, system_prompt: Optional[str] = None, tool_type: str = "smart") -> str:
        primary_tool = self.get_tool(tool_type)
        
        try:
            return await primary_tool.generate(prompt, system_prompt)
        except Exception as e:
            logger.warning(f"Primary LLM tool failed: {str(e)}, trying fallback")
            
            # Try other available tools
            for tool_name, tool in self.tools.items():
                if tool != primary_tool:
                    try:
                        return await tool.generate(prompt, system_prompt)
                    except Exception as fallback_error:
                        logger.warning(f"Fallback tool {tool_name} also failed: {str(fallback_error)}")
                        continue
            
            # If all tools fail, raise the original exception
            raise e
    
    def get_total_cost(self) -> float:
        return sum(tool.get_total_cost() for tool in self.tools.values())


def create_llm_manager(config: Config) -> LLMManager:
    return LLMManager(config)

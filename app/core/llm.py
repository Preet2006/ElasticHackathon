"""
LLM Client with Tiered Fallback Strategy (Resilience Upgrade)
Tier 1: Groq (llama-3.3-70b-versatile) - Fast and smart
Tier 2: HuggingFace Serverless (Mistral-7B-Instruct-v0.2) - Reliable and free
"""

from typing import Optional, Any, Dict, Union
from langchain_groq import ChatGroq
from langchain_huggingface import ChatHuggingFace, HuggingFaceEndpoint
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
    after_log
)
import logging
from app.core.config import get_settings

# Configure logging
logger = logging.getLogger(__name__)


class LLMError(Exception):
    """Base exception for LLM-related errors"""
    pass


class RateLimitError(LLMError):
    """Raised when rate limit is exceeded"""
    pass


class APITimeoutError(LLMError):
    """Raised when API request times out"""
    pass


def get_primary_llm() -> ChatGroq:
    """
    Get the primary (Tier 1) LLM - Groq with llama-3.3-70b-versatile
    
    Returns:
        ChatGroq: Primary LLM instance
    """
    settings = get_settings()
    if not settings.groq_api_key:
        raise ValueError("GROQ_API_KEY not found in environment")
    
    return ChatGroq(
        model=settings.llm_model,
        temperature=settings.llm_temperature,
        groq_api_key=settings.groq_api_key,
        max_retries=0  # We handle retries manually
    )


def get_fallback_llm() -> ChatHuggingFace:
    """
    Get the fallback (Tier 2) LLM - HuggingFace Serverless with chat endpoint
    
    Returns:
        ChatHuggingFace: Fallback LLM instance using conversational API
    """
    import os
    hf_token = os.getenv("HUGGINGFACEHUB_API_TOKEN")
    
    if not hf_token:
        raise ValueError("HUGGINGFACEHUB_API_TOKEN not found in environment")
    
    # Use HuggingFace's free serverless inference with conversational task
    # This wraps the endpoint to work with LangChain's chat interface
    llm = HuggingFaceEndpoint(
        repo_id="meta-llama/Llama-3.2-3B-Instruct",
        huggingfacehub_api_token=hf_token,
        max_new_tokens=2048,
        temperature=0.1
    )
    
    # Wrap with ChatHuggingFace to handle conversational format
    return ChatHuggingFace(llm=llm)


def _is_retryable_error(exception: Exception) -> bool:
    """
    Determine if an exception should trigger a retry
    
    Args:
        exception: The exception to check
        
    Returns:
        bool: True if the error is retryable
    """
    retryable_types = (RateLimitError, APITimeoutError, ConnectionError, TimeoutError)
    
    if isinstance(exception, retryable_types):
        return True
    
    # Check for common rate limit indicators in error messages
    error_msg = str(exception).lower()
    rate_limit_indicators = [
        "rate limit",
        "too many requests",
        "429",
        "quota exceeded",
        "timeout"
    ]
    
    return any(indicator in error_msg for indicator in rate_limit_indicators)


@retry(
    retry=retry_if_exception_type((RateLimitError, APITimeoutError, ConnectionError, TimeoutError)),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    after=after_log(logger, logging.INFO)
)
def _invoke_with_retry(llm: Union[ChatGroq, ChatHuggingFace], messages: Union[list[BaseMessage], str]) -> Any:
    """
    Invoke LLM with automatic retry logic
    
    Args:
        llm: The LLM instance (ChatGroq or ChatHuggingFace)
        messages: Messages to send (list for both ChatGroq and ChatHuggingFace)
        
    Returns:
        The LLM response
        
    Raises:
        RateLimitError: If rate limit is exceeded after retries
        APITimeoutError: If timeout occurs after retries
    """
    try:
        response = llm.invoke(messages)
        return response
    except Exception as e:
        # Convert common errors to our custom types for retry logic
        error_msg = str(e).lower()
        
        if "rate limit" in error_msg or "429" in error_msg or "too many requests" in error_msg:
            logger.warning(f"Rate limit encountered: {e}")
            raise RateLimitError(f"Rate limit exceeded: {e}") from e
        elif "timeout" in error_msg:
            logger.warning(f"Timeout encountered: {e}")
            raise APITimeoutError(f"API timeout: {e}") from e
        elif "connection" in error_msg:
            logger.warning(f"Connection error encountered: {e}")
            raise ConnectionError(f"Connection failed: {e}") from e
        else:
            # Non-retryable error
            logger.error(f"Non-retryable LLM error: {e}")
            raise


def completion_with_fallback(
    messages: Union[list[BaseMessage], str],
    system_message: Optional[str] = None
) -> str:
    """
    Execute LLM completion with Tiered Fallback Strategy
    
    Tier 1 (Primary): Groq (llama-3.3-70b-versatile) - Fast and smart
    Tier 2 (Fallback): HuggingFace Serverless (Llama-3.2-3B) - Reliable and free
    
    Args:
        messages: Messages to send (list of BaseMessage or simple string)
        system_message: Optional system message
        
    Returns:
        str: The LLM response content
        
    Raises:
        LLMError: If both tiers fail
    """
    # Convert string to messages if needed
    if isinstance(messages, str):
        msg_list = []
        if system_message:
            msg_list.append(SystemMessage(content=system_message))
        msg_list.append(HumanMessage(content=messages))
        user_prompt = messages
    else:
        msg_list = messages
        if system_message:
            msg_list.insert(0, SystemMessage(content=system_message))
        # Extract user prompt from messages for HuggingFace format
        user_prompt = ""
        for msg in msg_list:
            if isinstance(msg, HumanMessage):
                user_prompt = msg.content
                break
    
    # Tier 1: Try Primary LLM (Groq)
    primary_error = None
    try:
        logger.info("🚀 Tier 1: Attempting Primary LLM (Groq)")
        primary_llm = get_primary_llm()
        response = _invoke_with_retry(primary_llm, msg_list)
        logger.info("✅ Tier 1: Primary LLM succeeded")
        return response.content
    except Exception as e:
        primary_error = e
        logger.warning(f"⚠️ Tier 1 Failed: {e}")
        logger.warning("🔄 Switching to Fallback LLM (HuggingFace Llama-3.2-3B)...")
        print(f"\n⚠️  PRIMARY LLM FAILED - Switching to Fallback (HuggingFace)\n")
    
    # Tier 2: Fallback LLM (HuggingFace)
    try:
        logger.info("🔄 Tier 2: Attempting Fallback LLM (HuggingFace)")
        fallback_llm = get_fallback_llm()
        
        # ChatHuggingFace uses the same message format as ChatGroq
        response = _invoke_with_retry(fallback_llm, msg_list)
        logger.info("✅ Tier 2: Fallback LLM succeeded")
        print(f"✅ Fallback LLM completed successfully\n")
        
        # Both ChatGroq and ChatHuggingFace return response with .content
        # Handle case where response might already be a string (e.g., in tests)
        if isinstance(response, str):
            return response
        return response.content
    except Exception as fallback_error:
        logger.error(f"❌ Tier 2 Failed: {fallback_error}")
        raise LLMError(
            f"All LLM tiers failed. Tier 1 (Groq): {primary_error}. Tier 2 (HuggingFace): {fallback_error}"
        ) from fallback_error


class LLMClient:
    """
    Resilient LLM client with tiered fallback strategy
    
    Features:
    - Tier 1: Groq (fast and smart)
    - Tier 2: HuggingFace (reliable fallback)
    - Automatic retry with exponential backoff
    - Rate limit handling
    - Logging of all tier switches
    """
    
    def __init__(
        self,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        api_key: Optional[str] = None
    ):
        """
        Initialize LLM client with resilience features
        
        Args:
            model: Model name (uses config default if not provided)
            temperature: Temperature setting (uses config default if not provided)
            api_key: API key (uses config if not provided)
        """
        settings = get_settings()
        
        self.model = model or settings.llm_model
        self.temperature = temperature if temperature is not None else settings.llm_temperature
        self.api_key = api_key or settings.groq_api_key
        
        logger.info(f"Initialized LLM client with tiered fallback (Primary: {self.model}, Fallback: Qwen2.5-Coder-32B)")
    
    def invoke(
        self,
        messages: list[BaseMessage] | str,
        system_message: Optional[str] = None
    ) -> str:
        """Llama-3.2-3
        Invoke LLM with tiered fallback strategy
        
        Args:
            messages: Messages to send (list of BaseMessage or simple string)
            system_message: Optional system message
            
        Returns:
            str: The LLM response content
            
        Raises:
            LLMError: If all tiers fail
        """
        return completion_with_fallback(messages, system_message)
    
    def analyze_vulnerability(self, function_code: str) -> Dict:
        """
        Analyze a code function for security vulnerabilities
        
        Args:
            function_code: The function code to analyze
            
        Returns:
            Dictionary with vulnerability analysis:
            {
                'vulnerable': bool,
                'risk_score': int (0-10),
                'type': str,
                'description': str
            }
            
        Raises:
            LLMError: If analysis fails
        """
        import json
        import re
        
        system_prompt = """You are a Senior Application Security Engineer with expertise in identifying security vulnerabilities.
Your task is to analyze code for security issues including but not limited to:
- SQL injection
- Command injection
- Path traversal
- Insecure deserialization
- Hardcoded credentials
- Insecure random number generation
- XML external entity (XXE) attacks
- Server-side request forgery (SSRF)
- Cross-site scripting (XSS)
- Authentication and authorization issues

Return ONLY valid JSON in this exact format (no markdown, no code blocks):
{
    "vulnerable": true/false,
    "risk_score": 0-10,
    "type": "vulnerability type or 'none'",
    "description": "detailed description"
}

If no vulnerability is found, return:
{
    "vulnerable": false,
    "risk_score": 0,
    "type": "none",
    "description": "No significant security vulnerabilities detected."
}"""

        user_prompt = f"""Analyze this Python function for security vulnerabilities:

```python
{function_code}
```

Return your analysis as JSON."""

        try:
            # Get LLM response
            response = self.invoke(user_prompt, system_message=system_prompt)
            
            # Clean up response - remove markdown code blocks if present
            response = response.strip()
            
            # Remove markdown code fences
            response = re.sub(r'^```json\s*', '', response)
            response = re.sub(r'^```\s*', '', response)
            response = re.sub(r'\s*```$', '', response)
            response = response.strip()
            
            # Parse JSON
            try:
                result = json.loads(response)
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse JSON response, attempting to extract: {e}")
                # Try to find JSON object in response
                json_match = re.search(r'\{[^}]+\}', response, re.DOTALL)
                if json_match:
                    result = json.loads(json_match.group(0))
                else:
                    # Return safe default
                    logger.error(f"Could not extract JSON from response: {response[:200]}")
                    return {
                        "vulnerable": False,
                        "risk_score": 0,
                        "type": "error",
                        "description": "Failed to parse LLM response"
                    }
            
            # Validate required fields
            required_fields = ["vulnerable", "risk_score", "type", "description"]
            for field in required_fields:
                if field not in result:
                    logger.warning(f"Missing field '{field}' in response")
                    result[field] = False if field == "vulnerable" else (0 if field == "risk_score" else "unknown")
            
            # Ensure risk_score is in valid range
            result["risk_score"] = max(0, min(10, int(result["risk_score"])))
            
            # Ensure vulnerable is boolean
            result["vulnerable"] = bool(result["vulnerable"])
            
            return result
            
        except Exception as e:
            logger.error(f"Vulnerability analysis failed: {e}")
            raise LLMError(f"Vulnerability analysis failed: {e}") from e


def get_llm(
    model: Optional[str] = None,
    temperature: Optional[float] = None,
    **kwargs
) -> LLMClient:
    """
    Factory function to create an LLM client with tiered fallback
    
    Args:
        model: Model name
        temperature: Temperature setting
        **kwargs: Additional arguments for LLMClient
        
    Returns:
        LLMClient: Configured LLM client with tier resilience
    """
    return LLMClient(model=model, temperature=temperature, **kwargs)

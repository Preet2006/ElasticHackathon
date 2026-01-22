"""
LLM Client with Resilience and Fallback Strategy
Uses Tenacity for retry logic with exponential backoff
"""

from typing import Optional, Any, Dict
from langchain_groq import ChatGroq
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
def _invoke_with_retry(llm: ChatGroq, messages: list[BaseMessage]) -> Any:
    """
    Invoke LLM with automatic retry logic
    
    Args:
        llm: The LLM instance
        messages: Messages to send to the LLM
        
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


class LLMClient:
    """
    Resilient LLM client with fallback strategies
    
    Features:
    - Automatic retry with exponential backoff
    - Rate limit handling
    - Configurable fallback models
    - Logging of all retry attempts
    """
    
    def __init__(
        self,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        api_key: Optional[str] = None,
        fallback_models: Optional[list[str]] = None
    ):
        """
        Initialize LLM client with resilience features
        
        Args:
            model: Model name (uses config default if not provided)
            temperature: Temperature setting (uses config default if not provided)
            api_key: API key (uses config if not provided)
            fallback_models: List of fallback models to try if primary fails
        """
        settings = get_settings()
        
        self.model = model or settings.llm_model
        self.temperature = temperature if temperature is not None else settings.llm_temperature
        self.api_key = api_key or settings.groq_api_key
        self.fallback_models = fallback_models or ["llama-3.1-70b-versatile", "mixtral-8x7b-32768"]
        
        if not self.api_key:
            raise ValueError(
                "No API key provided. Set GROQ_API_KEY environment variable or pass api_key parameter."
            )
        
        self._llm = self._create_llm(self.model)
        logger.info(f"Initialized LLM client with model: {self.model}")
    
    def _create_llm(self, model: str) -> ChatGroq:
        """
        Create a ChatGroq instance
        
        Args:
            model: Model name
            
        Returns:
            ChatGroq instance
        """
        return ChatGroq(
            model=model,
            temperature=self.temperature,
            groq_api_key=self.api_key,
            max_retries=0  # We handle retries with tenacity
        )
    
    def invoke(
        self,
        messages: list[BaseMessage] | str,
        system_message: Optional[str] = None
    ) -> str:
        """
        Invoke LLM with automatic retry and fallback
        
        Args:
            messages: Messages to send (list of BaseMessage or simple string)
            system_message: Optional system message
            
        Returns:
            str: The LLM response content
            
        Raises:
            LLMError: If all retry attempts and fallbacks fail
        """
        # Convert string to messages if needed
        if isinstance(messages, str):
            msg_list = []
            if system_message:
                msg_list.append(SystemMessage(content=system_message))
            msg_list.append(HumanMessage(content=messages))
        else:
            msg_list = messages
            if system_message:
                msg_list.insert(0, SystemMessage(content=system_message))
        
        # Try primary model
        try:
            logger.debug(f"Invoking LLM with model: {self.model}")
            response = _invoke_with_retry(self._llm, msg_list)
            return response.content
        except Exception as e:
            logger.error(f"Primary model {self.model} failed after retries: {e}")
            
            # Try fallback models
            for fallback_model in self.fallback_models:
                try:
                    logger.info(f"Attempting fallback model: {fallback_model}")
                    fallback_llm = self._create_llm(fallback_model)
                    response = _invoke_with_retry(fallback_llm, msg_list)
                    logger.info(f"Fallback model {fallback_model} succeeded")
                    return response.content
                except Exception as fallback_error:
                    logger.error(f"Fallback model {fallback_model} failed: {fallback_error}")
                    continue
            
            # All attempts failed
            raise LLMError(f"All LLM invocation attempts failed. Last error: {e}") from e
    
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
    Factory function to create an LLM client
    
    Args:
        model: Model name
        temperature: Temperature setting
        **kwargs: Additional arguments for LLMClient
        
    Returns:
        LLMClient: Configured LLM client with resilience features
    """
    return LLMClient(model=model, temperature=temperature, **kwargs)

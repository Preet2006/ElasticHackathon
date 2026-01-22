"""
Test LLM Fallback System
Verifies that the tiered fallback works correctly when primary LLM fails
"""

import pytest
from unittest.mock import patch, MagicMock
from app.core.llm import completion_with_fallback, get_primary_llm, get_fallback_llm, LLMError


def test_fallback_on_primary_failure():
    """Test that fallback LLM is called when primary fails"""
    
    # Mock the primary LLM to raise an exception
    with patch('app.core.llm.get_primary_llm') as mock_primary:
        mock_primary.side_effect = Exception("Primary LLM failed (simulated rate limit)")
        
        # Mock the fallback LLM to succeed
        with patch('app.core.llm.get_fallback_llm') as mock_fallback:
            mock_fallback_instance = MagicMock()
            mock_fallback_instance.invoke.return_value = "Fallback response"
            mock_fallback.return_value = mock_fallback_instance
            
            # Call completion_with_fallback
            result = completion_with_fallback("Test prompt", system_message="Test system")
            
            # Assertions
            assert mock_primary.called, "Primary LLM should be attempted"
            assert mock_fallback.called, "Fallback LLM should be called when primary fails"
            assert result == "Fallback response", "Should return fallback response"


def test_primary_success_no_fallback():
    """Test that fallback is not called when primary succeeds"""
    
    # Mock the primary LLM to succeed
    with patch('app.core.llm.get_primary_llm') as mock_primary:
        mock_primary_instance = MagicMock()
        mock_primary_response = MagicMock()
        mock_primary_response.content = "Primary response"
        mock_primary_instance.invoke.return_value = mock_primary_response
        mock_primary.return_value = mock_primary_instance
        
        # Mock the fallback LLM (should not be called)
        with patch('app.core.llm.get_fallback_llm') as mock_fallback:
            # Call completion_with_fallback
            result = completion_with_fallback("Test prompt")
            
            # Assertions
            assert mock_primary.called, "Primary LLM should be attempted"
            assert not mock_fallback.called, "Fallback should not be called when primary succeeds"
            assert result == "Primary response", "Should return primary response"


def test_both_llms_fail():
    """Test that LLMError is raised when both tiers fail"""
    
    # Mock both LLMs to fail
    with patch('app.core.llm.get_primary_llm') as mock_primary:
        mock_primary.side_effect = Exception("Primary failed")
        
        with patch('app.core.llm.get_fallback_llm') as mock_fallback:
            mock_fallback.side_effect = Exception("Fallback failed")
            
            # Should raise LLMError
            with pytest.raises(LLMError) as exc_info:
                completion_with_fallback("Test prompt")
            
            # Check error message contains both failures
            error_msg = str(exc_info.value)
            assert "Tier 1" in error_msg or "Primary" in error_msg
            assert "Tier 2" in error_msg or "Fallback" in error_msg


def test_message_format_conversion():
    """Test that message format is passed correctly to fallback LLM"""
    
    # Mock primary to fail
    with patch('app.core.llm.get_primary_llm') as mock_primary:
        mock_primary.side_effect = Exception("Primary failed")
        
        # Mock fallback to succeed and capture the prompt
        with patch('app.core.llm.get_fallback_llm') as mock_fallback:
            mock_fallback_instance = MagicMock()
            mock_fallback_instance.invoke.return_value = "Fallback response"
            mock_fallback.return_value = mock_fallback_instance
            
            # Call with system message
            result = completion_with_fallback(
                "User message",
                system_message="System instruction"
            )
            
            # Check that fallback was called
            assert mock_fallback_instance.invoke.called
            call_args = mock_fallback_instance.invoke.call_args[0][0]
            
            # Should be a list of message objects (both ChatGroq and ChatHuggingFace use same format)
            assert isinstance(call_args, list)
            assert len(call_args) == 2  # System + Human message
            assert call_args[0].content == "System instruction"
            assert call_args[1].content == "User message"
            assert result == "Fallback response"


def test_logging_on_switch(caplog):
    """Test that tier switch is logged clearly"""
    
    with patch('app.core.llm.get_primary_llm') as mock_primary:
        mock_primary.side_effect = Exception("Rate limit exceeded")
        
        with patch('app.core.llm.get_fallback_llm') as mock_fallback:
            mock_fallback_instance = MagicMock()
            mock_fallback_instance.invoke.return_value = "Fallback response"
            mock_fallback.return_value = mock_fallback_instance
            
            # Call completion
            with caplog.at_level('WARNING'):
                result = completion_with_fallback("Test")
            
            # Check logs
            assert any("Switching to Fallback" in record.message for record in caplog.records), \
                "Should log when switching to fallback"
            assert any("Tier 1 Failed" in record.message or "PRIMARY LLM FAILED" in record.message 
                      for record in caplog.records), \
                "Should log primary failure"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

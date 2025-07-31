"""
Google Generative AI (Gemini) Service

This module provides integration with Google's Generative AI (Gemini) API for
content generation and processing. It includes functions for making API calls
with timeout handling, retry logic, and response validation.

The service is designed for robust AI content generation with features like:
- Timeout handling to prevent hanging requests
- Automatic retry logic for failed requests
- JSON response validation when required
- Empty response detection and handling
- Comprehensive error logging and recovery

Features:
- Configurable timeout periods for API calls
- Automatic retry mechanism for failed requests
- JSON validation for structured responses
- Empty response detection and retry logic
- Detailed error logging and debugging information

Dependencies:
- google.genai: Google Generative AI client
- src.utils.text_utils: JSON validation utilities
- src.utils.timeout_utils: Timeout handling utilities
- src.utils.file_utils: File interaction utilities

Configuration:
- Requires Google API key for authentication
- Supports various Gemini models (gemini-pro, gemini-pro-vision, etc.)
- Configurable generation parameters via GenerateContentConfig

Example Usage:
    from src.services import gemini_generate_text, custom_gemini_generate_content
    
    # Simple text generation
    response = gemini_generate_text(client, "gemini-pro", prompt, config)
    
    # Advanced generation with validation
    response = custom_gemini_generate_content(prompt, config, "gemini-pro", api_key)
"""

from google import genai
from google.genai import types
from google.genai.types import GenerateContentConfig, GenerateContentResponse
from typing import Optional

from src.utils.text_utils import is_valid_json, clean_text
from src.utils.timeout_utils import run_with_timeout, TimeoutError
from src.utils.file_utils import edit_prompt_interactively

def gemini_generate_text(client: genai.Client, model: str, prompt: str, config: GenerateContentConfig, timeout_seconds: int = 60) -> GenerateContentResponse:
    """
    Make a Gemini API call with timeout protection.
    
    This function wraps the Gemini API call with timeout handling to prevent
    the application from hanging indefinitely. It uses the run_with_timeout
    utility to ensure the API call completes within the specified time limit.
    
    The function is designed for reliability and provides:
    - Configurable timeout periods
    - Automatic timeout detection and handling
    - Consistent error handling across different models
    - Support for various content types (text, images, etc.)
    
    Args:
        client (genai.Client): Google AI client instance
        model (str): Model name (e.g., "gemini-pro", "gemini-pro-vision")
        prompt (str): Content to send to the model
        config (GenerateContentConfig): Configuration for the generation
        timeout_seconds (int): Timeout in seconds (default: 60 seconds)
    
    Returns:
        GenerateContentResponse: API response object
        
    Raises:
        TimeoutError: If the API call exceeds the timeout period
        Exception: For other API-related errors
        
    Example:
        client = genai.Client(api_key="your-api-key")
        config = GenerateContentConfig(temperature=0.7)
        response = gemini_generate_text(client, "gemini-pro", "Hello world", config)
    """
    def api_call():
        """Inner function to make the actual API call."""
        return client.models.generate_content(
            model=model,
            contents=prompt,
            config=config
        )
    
    return run_with_timeout(api_call, timeout_seconds)


def custom_gemini_generate_content(prompt: str, config: GenerateContentConfig, model: str, google_api_key: str) -> Optional[GenerateContentResponse]:
    """
    Generate content using Gemini API with comprehensive validation and retry logic.
    
    This function provides a robust interface for content generation with multiple
    layers of validation and error handling. It includes:
    - Automatic retry logic for failed requests
    - JSON response validation when required
    - Empty response detection and retry
    - Comprehensive error logging
    - Timeout handling with extended periods
    
    The function implements a sophisticated retry strategy:
    1. Attempt the API call with extended timeout (120 seconds)
    2. Validate response structure and content
    3. Check for JSON validity if required
    4. Detect empty responses and retry if needed
    5. Log detailed error information for debugging
    
    Args:
        prompt (str): The input prompt for content generation
        config (GenerateContentConfig): Configuration for the generation process
        model (str): Model identifier (e.g., "gemini-pro")
        google_api_key (str): API key for Google AI authentication
        
    Returns:
        Optional[GenerateContentResponse]: Response object if successful, None if all attempts fail
        
    Example:
        config = GenerateContentConfig(
            temperature=0.7,
            response_mime_type="application/json"
        )
        response = custom_gemini_generate_content(
            "Generate event data", config, "gemini-pro", api_key
        )
    """
    client = genai.Client(api_key=google_api_key)
    max_attempts = 2
    
    for attempt in range(max_attempts):
        attempt_num = attempt + 1
        try:
            # Step 1: Generate Response with extended timeout
            response = gemini_generate_text(
                client=client,
                model=model,
                prompt=prompt,
                config=config,
                timeout_seconds=120  # Extended timeout for complex requests
            )
            
            # Step 2: Basic Response Validation
            # Check if response has the expected structure and content
            if not hasattr(response, 'text') or not response.text:
                print(f"│ │ [GenerativeLanguage.custom_gemini_generate_content]: Empty response text")
                continue
                
            # Step 3: JSON Validation (if required)
            # If the config specifies JSON response, validate the format
            if hasattr(config, 'response_mime_type') and config.response_mime_type == 'application/json':
                is_valid, error_msg, _ = is_valid_json(clean_text(response.text))
                if not is_valid:
                    print(f"│ │ [GenerativeLanguage.custom_gemini_generate_content] Invalid JSON: {error_msg}")
                    continue
                
            # Step 4: Check for Empty Events
            # Detect if the response indicates no events were found
            if response.text == "[]":
                if attempt_num < max_attempts:
                    print(f"│ │ [GenerativeLanguage.custom_gemini_generate_content] No events detected, retrying...")
                    continue
                print(f"│ │ [GenerativeLanguage.custom_gemini_generate_content] No events detected after {max_attempts} attempts")
                return None

            # All validations passed - return the successful response
            return response
                
        except TimeoutError:
            print(f"│ │ [GenerativeLanguage.custom_gemini_generate_content] Timeout after 120 seconds")
            continue
        except Exception as e:
            print(f"│ │ [GenerativeLanguage.custom_gemini_generate_content] Error: {str(e)}")
            continue
            
    # All attempts exhausted
    print("│ │ [GenerativeLanguage.custom_gemini_generate_content] All attempts exhausted")
    return None
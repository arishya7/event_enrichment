from google import genai
from google.genai import types
from google.genai.types import GenerateContentConfig, GenerateContentResponse
from typing import Optional

from src.utils.text_utils import is_valid_json, clean_text
from src.utils.timeout_utils import run_with_timeout, TimeoutError
from src.utils.file_utils import edit_prompt_interactively

def gemini_generate_text(client: genai.Client, model: str, prompt: str, config: GenerateContentConfig, timeout_seconds: int = 60) -> GenerateContentResponse:
    """Make a Gemini API call with timeout.
    
    Args:
        client (genai.Client): Google AI client
        model (str): Model name
        prompt (str): Content to send
        config (GenerateContentConfig): Configuration for the generation
        timeout_seconds (int): Timeout in seconds (default 60 seconds)
    
    Returns:
        GenerateContentResponse: API response
        
    Raises:
        TimeoutError: If the API call times out
    """
    def api_call():
        return client.models.generate_content(
            model=model,
            contents=prompt,
            config=config
        )
    
    return run_with_timeout(api_call, timeout_seconds)



def custom_gemini_generate_content(prompt: str, config: GenerateContentConfig, model: str, google_api_key: str) -> Optional[GenerateContentResponse]:
    """Generate content using Gemini API with JSON validation when needed.
    
    Args:
        prompt (str): The input prompt
        config (GenerateContentConfig): Configuration for the generation
        model (str): Model identifier
        google_api_key (str): API key for authentication
        
    Returns:
        Optional[GenerateContentResponse]: Response object if successful, None if failed
    """
    client = genai.Client(api_key=google_api_key)
    max_attempts = 2
    
    for attempt in range(max_attempts):
        attempt_num = attempt + 1
        try:
            # 1. Generate Response
            response = gemini_generate_text(
                client=client,
                model=model,
                prompt=prompt,
                config=config,
                timeout_seconds=120
            )
            
            # 2. Basic Response Validation
            if not hasattr(response, 'text') or not response.text:
                print(f"│ │ [GenerativeLanguage.custom_gemini_generate_content]: Empty response text")
                continue
                
            # 3. JSON Validation (if required) - Check first
            if hasattr(config, 'response_mime_type') and config.response_mime_type == 'application/json':
                is_valid, error_msg, _ = is_valid_json(clean_text(response.text))
                if not is_valid:
                    print(f"│ │ [GenerativeLanguage.custom_gemini_generate_content] Invalid JSON: {error_msg}")
                    continue
                
            # 4. Check for Empty Events
            if response.text == "[]":
                if attempt_num < max_attempts:
                    print(f"│ │ [GenerativeLanguage.custom_gemini_generate_content] No events detected, retrying...")
                    continue
                print(f"│ │ [GenerativeLanguage.custom_gemini_generate_content] No events detected after {max_attempts} attempts")
                return None

            # All validations passed
            return response
                
        except TimeoutError:
            print(f"│ │ [GenerativeLanguage.custom_gemini_generate_content] Timeout after 120 seconds")
            continue
        except Exception as e:
            print(f"│ │ [GenerativeLanguage.custom_gemini_generate_content] Error: {str(e)}")
            continue
            
    print("│ │ [GenerativeLanguage.custom_gemini_generate_content] All attempts exhausted")
    return None
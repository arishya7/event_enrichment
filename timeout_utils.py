import threading
import time
import platform
import signal
from functools import wraps

class TimeoutError(Exception):
    """Custom timeout exception"""
    pass

def timeout_handler(signum, frame):
    """Signal handler for Unix systems"""
    raise TimeoutError("Operation timed out")

def run_with_timeout(func, timeout_seconds, *args, **kwargs):
    """
    Run a function with a timeout using threading (cross-platform)
    
    Args:
        func: Function to run
        timeout_seconds: Timeout in seconds
        *args, **kwargs: Arguments to pass to the function
    
    Returns:
        Result of the function
    
    Raises:
        TimeoutError: If the function doesn't complete within timeout
    """
    result = []
    exception = []
    
    def target():
        try:
            result.append(func(*args, **kwargs))
        except Exception as e:
            exception.append(e)
    
    thread = threading.Thread(target=target)
    thread.daemon = True
    thread.start()
    thread.join(timeout_seconds)
    
    if thread.is_alive():
        # Thread is still running, timeout occurred
        raise TimeoutError(f"Operation timed out after {timeout_seconds} seconds")
    
    if exception:
        raise exception[0]
    
    return result[0]

def timeout_decorator(timeout_seconds):
    """
    Decorator to add timeout functionality to any function
    
    Args:
        timeout_seconds: Timeout in seconds
    
    Returns:
        Decorated function with timeout
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            return run_with_timeout(func, timeout_seconds, *args, **kwargs)
        return wrapper
    return decorator

def api_call_with_timeout(client, model, contents, config, timeout_seconds=300):
    """
    Make an API call with timeout
    
    Args:
        client: Google AI client
        model: Model name
        contents: Content to send
        config: Configuration
        timeout_seconds: Timeout in seconds (default 5 minutes)
    
    Returns:
        API response
    
    Raises:
        TimeoutError: If the API call times out
    """
    def api_call():
        return client.models.generate_content(
            model=model,
            contents=contents,
            config=config
        )
    
    return run_with_timeout(api_call, timeout_seconds) 
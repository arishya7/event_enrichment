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

def gemini_generate_text(client, model, prompt, config, timeout_seconds=300):
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
            contents=prompt,
            config=config
        )
    
    return run_with_timeout(api_call, timeout_seconds)

if __name__ == "__main__":
    print("\n=== Testing Timeout Functionality ===\n")
    
    # Test 1: Function that completes within timeout
    def quick_function():
        time.sleep(1)
        return "Quick function completed"
        
    print("1. Testing function that completes within timeout (2 seconds):")
    try:
        result = run_with_timeout(quick_function, 2)
        print(f"✓ Success: {result}")
    except TimeoutError as e:
        print(f"✗ Failed: {str(e)}")
        
    # Test 2: Function that exceeds timeout
    def slow_function():
        time.sleep(3)
        return "Slow function completed"
        
    print("\n2. Testing function that exceeds timeout (1 second):")
    try:
        result = run_with_timeout(slow_function, 1)
        print(f"✗ Failed: Function should have timed out")
    except TimeoutError as e:
        print(f"✓ Success: {str(e)}")
        
    # Test 3: Function that raises an exception
    def error_function():
        raise ValueError("Test error")
        
    print("\n3. Testing function that raises an exception:")
    try:
        result = run_with_timeout(error_function, 1)
        print(f"✗ Failed: Function should have raised an error")
    except ValueError as e:
        print(f"✓ Success: Original error raised: {str(e)}")
        
    # Test 4: Using timeout decorator
    @timeout_decorator(1)
    def decorated_slow_function():
        time.sleep(10)
        return "Decorated function completed"
        
    print("\n4. Testing timeout decorator:")
    try:
        result = decorated_slow_function()
        print(f"✗ Failed: Function should have timed out")
    except TimeoutError as e:
        print(f"✓ Success: {str(e)}")
        
    # Test 5: Function with arguments
    def function_with_args(x, y, sleep_time=1):
        time.sleep(sleep_time)
        return x + y
        
    print("\n5. Testing function with arguments:")
    try:
        # Should complete
        result = run_with_timeout(function_with_args, 5, 1, 2, sleep_time=0.5)
        print(f"✓ Success: Result = {result}")
        
        # Should timeout
        result = run_with_timeout(function_with_args, 1, 3, 4, sleep_time=2)
        print(f"✗ Failed: Function should have timed out")
    except TimeoutError as e:
        print(f"✓ Success: {str(e)}")
    
    print("\n=== Test Complete ===") 
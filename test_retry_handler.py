"""Test script for retry handler functionality."""

import time
from src.retry_handler import (
    retry_on_error, 
    RetryConfig, 
    CircuitBreaker,
    OPENAI_RETRY_CONFIG,
    SLACK_RETRY_CONFIG
)
from src.utils import setup_logging

logger = setup_logging()


def test_basic_retry():
    """Test basic retry functionality."""
    print("\n" + "="*60)
    print("TEST 1: Basic Retry with Success on Third Attempt")
    print("="*60)
    
    attempt_count = [0]  # Use list to modify in nested function
    
    @retry_on_error(
        config=RetryConfig(max_retries=3, initial_delay=0.5, exponential_base=2.0),
        exceptions=(ValueError,),
        on_retry=lambda e, attempt: print(f"  Retry {attempt + 1}: {e}")
    )
    def flaky_function():
        attempt_count[0] += 1
        if attempt_count[0] < 3:
            raise ValueError(f"Attempt {attempt_count[0]} failed")
        return "Success!"
    
    try:
        result = flaky_function()
        print(f"✅ Result: {result}")
        print(f"   Total attempts: {attempt_count[0]}")
    except Exception as e:
        print(f"❌ Failed: {e}")


def test_max_retries_exceeded():
    """Test behavior when max retries are exceeded."""
    print("\n" + "="*60)
    print("TEST 2: Max Retries Exceeded")
    print("="*60)
    
    attempt_count = [0]
    
    @retry_on_error(
        config=RetryConfig(max_retries=3, initial_delay=0.3),
        exceptions=(RuntimeError,)
    )
    def always_fails():
        attempt_count[0] += 1
        print(f"  Attempt {attempt_count[0]}: Failing...")
        raise RuntimeError("This always fails")
    
    try:
        result = always_fails()
        print(f"✅ Result: {result}")
    except RuntimeError as e:
        print(f"❌ Failed after {attempt_count[0]} attempts: {e}")


def test_circuit_breaker():
    """Test circuit breaker functionality."""
    print("\n" + "="*60)
    print("TEST 3: Circuit Breaker")
    print("="*60)
    
    breaker = CircuitBreaker(
        failure_threshold=3,
        recovery_timeout=2.0,
        expected_exception=ConnectionError
    )
    
    def unreliable_service(should_fail=True):
        if should_fail:
            raise ConnectionError("Service unavailable")
        return "Success!"
    
    # Fail until circuit opens
    for i in range(5):
        try:
            result = breaker.call(unreliable_service, should_fail=True)
            print(f"  Attempt {i+1}: {result}")
        except Exception as e:
            print(f"  Attempt {i+1}: {type(e).__name__}: {e}")
        
        time.sleep(0.1)
    
    # Try after recovery timeout
    print("\n  Waiting for recovery timeout...")
    time.sleep(2.5)
    
    try:
        result = breaker.call(unreliable_service, should_fail=False)
        print(f"  After recovery: ✅ {result}")
    except Exception as e:
        print(f"  After recovery: ❌ {e}")


def test_exponential_backoff():
    """Test exponential backoff timing."""
    print("\n" + "="*60)
    print("TEST 4: Exponential Backoff Timing")
    print("="*60)
    
    from src.retry_handler import calculate_delay
    
    config = RetryConfig(
        initial_delay=1.0,
        max_delay=10.0,
        exponential_base=2.0,
        jitter=False  # Disable for predictable testing
    )
    
    print("  Delay progression:")
    for attempt in range(5):
        delay = calculate_delay(attempt, config)
        print(f"    Attempt {attempt + 1}: {delay:.2f}s")


def test_different_exceptions():
    """Test handling of different exception types."""
    print("\n" + "="*60)
    print("TEST 5: Exception Type Filtering")
    print("="*60)
    
    @retry_on_error(
        config=RetryConfig(max_retries=2, initial_delay=0.2),
        exceptions=(ValueError, KeyError)
    )
    def selective_retry(error_type):
        if error_type == "value":
            raise ValueError("This will be retried")
        elif error_type == "key":
            raise KeyError("This will be retried")
        else:
            raise RuntimeError("This will NOT be retried")
    
    # Test retryable exception
    print("  Testing ValueError (retryable):")
    try:
        selective_retry("value")
    except ValueError as e:
        print(f"    ✅ Caught after retries: {e}")
    
    # Test non-retryable exception
    print("\n  Testing RuntimeError (not retryable):")
    try:
        selective_retry("runtime")
    except RuntimeError as e:
        print(f"    ✅ Immediately raised (no retry): {e}")


def test_config_comparison():
    """Compare different retry configurations."""
    print("\n" + "="*60)
    print("TEST 6: Configuration Comparison")
    print("="*60)
    
    configs = {
        "OpenAI": OPENAI_RETRY_CONFIG,
        "Slack": SLACK_RETRY_CONFIG,
    }
    
    for name, config in configs.items():
        print(f"\n  {name} Config:")
        print(f"    Max Retries: {config.max_retries}")
        print(f"    Initial Delay: {config.initial_delay}s")
        print(f"    Max Delay: {config.max_delay}s")
        print(f"    Exponential Base: {config.exponential_base}x")
        print(f"    Jitter: {config.jitter}")


def test_nested_retries():
    """Test nested retry scenarios."""
    print("\n" + "="*60)
    print("TEST 7: Nested Retries")
    print("="*60)
    
    outer_attempts = [0]
    inner_attempts = [0]
    
    @retry_on_error(
        config=RetryConfig(max_retries=2, initial_delay=0.2),
        exceptions=(RuntimeError,)
    )
    def outer_function():
        outer_attempts[0] += 1
        print(f"  Outer attempt {outer_attempts[0]}")
        
        @retry_on_error(
            config=RetryConfig(max_retries=2, initial_delay=0.1),
            exceptions=(ValueError,)
        )
        def inner_function():
            inner_attempts[0] += 1
            print(f"    Inner attempt {inner_attempts[0]}")
            if inner_attempts[0] < 2:
                raise ValueError("Inner failure")
            return "Inner success"
        
        result = inner_function()
        if outer_attempts[0] < 2:
            raise RuntimeError("Outer failure")
        return f"Outer success with {result}"
    
    try:
        result = outer_function()
        print(f"✅ Final result: {result}")
        print(f"   Outer attempts: {outer_attempts[0]}, Inner attempts: {inner_attempts[0]}")
    except Exception as e:
        print(f"❌ Failed: {e}")


def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("🧪 RETRY HANDLER TEST SUITE")
    print("="*60)
    print("Testing error handling and retry mechanisms...\n")
    
    tests = [
        test_basic_retry,
        test_max_retries_exceeded,
        test_exponential_backoff,
        test_different_exceptions,
        test_config_comparison,
        test_nested_retries,
        test_circuit_breaker,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            failed += 1
            print(f"\n❌ Test failed with error: {e}")
            logger.error(f"Test {test.__name__} failed", exc_info=True)
    
    print("\n" + "="*60)
    print("📊 TEST RESULTS")
    print("="*60)
    print(f"✅ Passed: {passed}/{len(tests)}")
    print(f"❌ Failed: {failed}/{len(tests)}")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()

"""Backoff calculation utilities for retry logic.

Provides exponential backoff calculation for task retries.
"""


def calculate_backoff_delay(retry_count: int, base_delay: int = 60) -> int:
    """Calculate exponential backoff delay.
    
    Args:
        retry_count: Current retry attempt (0-indexed)
        base_delay: Base delay in seconds
        
    Returns:
        Delay in seconds with exponential backoff
        
    The formula is: base_delay * 2^retry_count
    
    Examples:
        - retry_count=0, base_delay=60 -> 60 seconds
        - retry_count=1, base_delay=60 -> 120 seconds
        - retry_count=2, base_delay=60 -> 240 seconds
        - retry_count=3, base_delay=60 -> 480 seconds
    """
    return base_delay * (2 ** retry_count)

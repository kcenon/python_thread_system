"""
Cancellation token for cooperative task cancellation
"""

import threading
from typing import Callable, Optional


class CancellationToken:
    """
    A token that allows cooperative cancellation of operations.

    Thread-safe cancellation mechanism using threading.Event.

    Example:
        >>> token = CancellationToken()
        >>> def work(token):
        ...     while not token.is_cancelled():
        ...         # Do work
        ...         pass
        >>> token.cancel()
    """

    def __init__(self) -> None:
        """Initialize a new cancellation token."""
        self._event = threading.Event()
        self._callbacks: list[Callable[[], None]] = []
        self._lock = threading.Lock()

    def cancel(self) -> None:
        """
        Request cancellation.

        Sets the internal event and executes all registered callbacks.
        This method is thread-safe and can be called multiple times.
        """
        if not self._event.is_set():
            self._event.set()

            # Execute callbacks
            with self._lock:
                for callback in self._callbacks:
                    try:
                        callback()
                    except Exception:
                        # Ignore callback exceptions to ensure all callbacks execute
                        pass

    def is_cancelled(self) -> bool:
        """
        Check if cancellation has been requested.

        Returns:
            True if cancel() has been called, False otherwise
        """
        return self._event.is_set()

    def wait(self, timeout: Optional[float] = None) -> bool:
        """
        Wait for cancellation to be requested.

        Args:
            timeout: Maximum time to wait in seconds. None means wait forever.

        Returns:
            True if cancellation was requested, False if timeout occurred
        """
        return self._event.wait(timeout)

    def register_callback(self, callback: Callable[[], None]) -> None:
        """
        Register a callback to be called when cancellation is requested.

        If cancellation has already been requested, the callback is executed immediately.

        Args:
            callback: Function to call on cancellation (takes no arguments)
        """
        with self._lock:
            if self._event.is_set():
                # Already cancelled, execute immediately
                try:
                    callback()
                except Exception:
                    pass
            else:
                self._callbacks.append(callback)

    def __bool__(self) -> bool:
        """Allow using token in boolean context: if token: ..."""
        return self.is_cancelled()

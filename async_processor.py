import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class TaskStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class AsyncTask:
    """Represents an asynchronous task"""
    id: str
    status: TaskStatus = TaskStatus.PENDING
    result: Any = None
    error: str = None
    created_at: float = field(default_factory=time.time)
    started_at: float = None
    completed_at: float = None
    progress: float = 0.0  # 0.0 to 1.0


class AsyncProcessor:
    """Handles asynchronous processing of citation fact-checking"""

    def __init__(self, default_timeout: float = 30.0):
        self.tasks: dict[str, AsyncTask] = {}
        self.callbacks: dict[str, Callable] = {}
        self._lock = threading.Lock()
        self.default_timeout = default_timeout

    def create_task(self, task_id: str, func: Callable, *args, timeout: float = None, **kwargs) -> AsyncTask:
        """Create a new asynchronous task with timeout"""
        if timeout is None:
            timeout = self.default_timeout

        with self._lock:
            task = AsyncTask(id=task_id)
            self.tasks[task_id] = task

        # Run task in background thread with timeout
        def run_task():
            try:
                with self._lock:
                    task.status = TaskStatus.PROCESSING
                    task.started_at = time.time()

                # Execute the function with timeout
                result = self._run_with_timeout(func, timeout, *args, **kwargs)

                with self._lock:
                    task.result = result
                    task.status = TaskStatus.COMPLETED
                    task.completed_at = time.time()
                    task.progress = 1.0

                # Trigger callback if registered
                if task_id in self.callbacks:
                    try:
                        self.callbacks[task_id](task_id, result)
                    except Exception as e:
                        print(f"Callback error for task {task_id}: {e}")

            except TimeoutError:
                with self._lock:
                    task.error = f"Timeout after {timeout} seconds"
                    task.status = TaskStatus.ERROR
                    task.completed_at = time.time()

                # Trigger error callback if registered
                if task_id in self.callbacks:
                    try:
                        self.callbacks[task_id](task_id, None, error=task.error)
                    except Exception as callback_e:
                        print(f"Error callback error for task {task_id}: {callback_e}")

            except Exception as e:
                with self._lock:
                    task.error = str(e)
                    task.status = TaskStatus.ERROR
                    task.completed_at = time.time()

                # Trigger error callback if registered
                if task_id in self.callbacks:
                    try:
                        self.callbacks[task_id](task_id, None, error=str(e))
                    except Exception as callback_e:
                        print(f"Error callback error for task {task_id}: {callback_e}")

        # Start background thread
        thread = threading.Thread(target=run_task, daemon=True)
        thread.start()

        return task

    def _run_with_timeout(self, func, timeout, *args, **kwargs):
        """Run a function with timeout using threading"""
        import queue
        import threading

        # Create a queue to get the result from the thread
        result_queue = queue.Queue()
        exception_queue = queue.Queue()

        def worker():
            try:
                result = func(*args, **kwargs)
                result_queue.put(result)
            except Exception as e:
                exception_queue.put(e)

        # Start the worker thread
        worker_thread = threading.Thread(target=worker)
        worker_thread.daemon = True
        worker_thread.start()

        # Wait for the result with timeout
        worker_thread.join(timeout=timeout)

        if worker_thread.is_alive():
            # Thread is still running, timeout occurred
            raise TimeoutError(f"Function timed out after {timeout} seconds")

        # Check for exceptions
        if not exception_queue.empty():
            raise exception_queue.get()

        # Return the result
        if not result_queue.empty():
            return result_queue.get()

        return None

    def register_callback(self, task_id: str, callback: Callable):
        """Register a callback to be called when task completes"""
        self.callbacks[task_id] = callback

    def get_task(self, task_id: str) -> AsyncTask:
        """Get task status and result"""
        return self.tasks.get(task_id)

    def get_all_tasks(self) -> dict[str, AsyncTask]:
        """Get all tasks"""
        return self.tasks.copy()

    def cleanup_old_tasks(self, max_age: float = 3600):
        """Clean up tasks older than max_age seconds"""
        current_time = time.time()
        with self._lock:
            old_tasks = [
                task_id for task_id, task in self.tasks.items()
                if current_time - task.created_at > max_age
            ]
            for task_id in old_tasks:
                del self.tasks[task_id]
                if task_id in self.callbacks:
                    del self.callbacks[task_id]


# Global async processor instance
async_processor = AsyncProcessor()


def create_async_task_id() -> str:
    """Create a unique task ID"""
    return f"task_{int(time.time() * 1000)}_{hash(str(time.time()))}"

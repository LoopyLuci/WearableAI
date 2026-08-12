"""
kernel_sim.py — Host-side FreeRTOS task scheduler simulator
Runs tasks as Python threads with priority-based preemption simulation.
"""
import threading
import time
import heapq
from dataclasses import dataclass, field
from typing import Callable, Optional, List
from enum import Enum

class TaskState(Enum):
    READY = 0
    RUNNING = 1
    BLOCKED = 2
    SUSPENDED = 3


@dataclass(order=True)
class ScheduledTask:
    priority: int
    task_id: int
    entry: Callable = field(compare=False)
    param: object = field(compare=False)
    stack_size: int = field(compare=False, default=8192)
    state: TaskState = field(compare=False, default=TaskState.READY)
    _thread: Optional[threading.Thread] = field(compare=False, default=None)
    _event: Optional[threading.Event] = field(compare=False, default=None)
    _notify_bits: int = field(compare=False, default=0)
    _notify_event: Optional[threading.Event] = field(compare=False, default=None)
    _restart_count: int = field(compare=False, default=0)


class KernelSimulator:
    """
    Simulates FreeRTOS task scheduling on the host.
    Uses Python threading with priority-based behavior simulation.
    """

    def __init__(self):
        self._tasks: List[ScheduledTask] = []
        self._lock = threading.Lock()
        self._task_counter = 0
        self._running = False
        self._ticks = 0
        self._tick_thread: Optional[threading.Thread] = None
        self._fault_handlers = {
            'stack_overflow': [],
            'malloc_failed': [],
            'idle': []
        }

    def task_create(self, entry: Callable, param: object, name: str,
                    stack_size: int, priority: int, core: int = 0) -> int:
        with self._lock:
            task_id = self._task_counter
            self._task_counter += 1

        event = threading.Event()
        notify_event = threading.Event()

        task = ScheduledTask(
            priority=-priority,  # Negate for min-heap (higher priority = lower number)
            task_id=task_id,
            entry=entry,
            param=param,
            stack_size=stack_size,
            _event=event,
            _notify_event=notify_event
        )
        task._thread = threading.Thread(
            target=self._task_wrapper,
            args=(task,),
            name=name,
            daemon=True
        )
        with self._lock:
            self._tasks.append(task)
        task._thread.start()
        return task_id

    def _task_wrapper(self, task: ScheduledTask):
        """Wrapper that simulates FreeRTOS task behavior."""
        while True:
            # Wait for task to be ready
            if task._event:
                task._event.wait(timeout=0.1)
                task._event.clear()

            if task.state == TaskState.SUSPENDED:
                time.sleep(0.01)
                continue

            if task.state == TaskState.BLOCKED:
                time.sleep(0.01)
                continue

            # Run the entry point
            try:
                task.entry(task.param)
            except Exception as e:
                print(f"[KernelSim] Task {task._thread.name if task._thread else '?'} raised: {e}")
                for handler in self._fault_handlers.get('stack_overflow', []):
                    handler(task.task_id)

            # Task completed — suspend
            task.state = TaskState.SUSPENDED

    def task_suspend(self, task_id: int):
        with self._lock:
            for t in self._tasks:
                if t.task_id == task_id:
                    t.state = TaskState.SUSPENDED
                    if t._event:
                        t._event.set()
                    break

    def task_resume(self, task_id: int):
        with self._lock:
            for t in self._tasks:
                if t.task_id == task_id:
                    t.state = TaskState.READY
                    if t._event:
                        t._event.set()
                    break

    def task_delete(self, task_id: int):
        with self._lock:
            self._tasks = [t for t in self._tasks if t.task_id != task_id]

    def task_notify(self, task_id: int, bits: int):
        with self._lock:
            for t in self._tasks:
                if t.task_id == task_id:
                    t._notify_bits |= bits
                    if t._notify_event:
                        t._notify_event.set()
                    break

    def task_wait_notification(self, task_id: int, bits: int, timeout_s: float) -> bool:
        with self._lock:
            for t in self._tasks:
                if t.task_id == task_id:
                    event = t._notify_event
                    break
            else:
                return False

        result = event.wait(timeout=timeout_s)
        if result:
            with self._lock:
                t._notify_event.clear()
        return result

    def on_fault(self, fault_type: str, handler: Callable):
        self._fault_handlers.setdefault(fault_type, []).append(handler)

    def start_scheduler(self):
        self._running = True
        print("[KernelSim] Scheduler started")

    def tick(self):
        """Simulate one system tick."""
        self._ticks += 1

    def stop(self):
        self._running = False
        print(f"[KernelSim] Scheduler stopped, total ticks: {self._ticks}")

"""
test_kernel.py — Host-side kernel simulator tests
"""
import sys
import os
import time
import threading

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "host-tools", "kernel-sim"))

from kernel_sim import KernelSimulator, TaskState

results = []
errors = []


def task_entry_a(param):
    """Task that completes quickly."""
    results.append(('A_start', param))
    time.sleep(0.01)
    results.append(('A_end',))


def task_entry_b(param):
    """Task that loops until suspended."""
    results.append(('B_start', param))
    while True:
        time.sleep(0.01)


def task_faulty(param):
    """Task that raises an exception."""
    raise RuntimeError("intentional fault")


def test_task_creation():
    sim = KernelSimulator()
    tid = sim.task_create(task_entry_a, 42, "TaskA", 4096, 5, 0)
    assert tid >= 0, "Task creation failed"
    sim.task_suspend(tid)
    sim.task_delete(tid)
    print("✓ Task create/suspend/delete")


def test_multiple_tasks():
    sim = KernelSimulator()
    tid_a = sim.task_create(task_entry_a, "A", "TaskA", 4096, 5, 0)
    tid_b = sim.task_create(task_entry_b, "B", "TaskB", 8192, 3, 0)

    sim.task_suspend(tid_b)
    sim.task_delete(tid_a)
    sim.task_delete(tid_b)
    print("✓ Multiple tasks created and cleaned up")


def test_fault_handler():
    sim = KernelSimulator()
    fault_caught = []

    def on_fault(task_id):
        fault_caught.append(task_id)

    sim.on_fault('stack_overflow', on_fault)
    tid = sim.task_create(task_faulty, None, "Faulty", 2048, 1, 0)

    # Wait for task to execute and raise (with longer timeout)
    import time
    deadline = time.time() + 2.0
    while time.time() < deadline and len(fault_caught) == 0:
        time.sleep(0.1)

    assert len(fault_caught) > 0, "Fault handler not called"
    sim.task_delete(tid)
    print("✓ Fault handler invoked on task exception")


def test_task_notify():
    sim = KernelSimulator()
    notified = []

    def task_with_notify(param):
        notified.append('waiting')
        sim.task_wait_notification(0, 0x01, 5.0)
        notified.append('notified')

    tid = sim.task_create(task_with_notify, None, "NotifyTask", 2048, 3, 0)
    time.sleep(0.05)
    sim.task_notify(tid, 0x01)
    time.sleep(0.1)
    assert 'notified' in notified, "Task was not notified"
    sim.task_delete(tid)
    print("✓ Task notification works")


def test_scheduler_lifecycle():
    sim = KernelSimulator()
    sim.start_scheduler()
    assert sim._running is True
    sim.stop()
    assert sim._running is False
    print("✓ Scheduler start/stop lifecycle")


if __name__ == '__main__':
    test_task_creation()
    test_multiple_tasks()
    test_fault_handler()
    test_task_notify()
    test_scheduler_lifecycle()
    print("\nAll kernel simulator tests passed.")

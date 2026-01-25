import asyncio
import pytest
from blunder_tutor.events.event_bus import EventBus
from blunder_tutor.events.event_types import EventType, JobEvent


@pytest.mark.asyncio
async def test_subscribe_and_publish():
    bus = EventBus()
    queue = await bus.subscribe(EventType.JOB_STATUS_CHANGED)

    event = JobEvent.create_status_changed("job-123", "import", "pending")
    await bus.publish(event)

    received = await asyncio.wait_for(queue.get(), timeout=1.0)
    assert received.type == EventType.JOB_STATUS_CHANGED
    assert received.data["job_id"] == "job-123"


@pytest.mark.asyncio
async def test_multiple_subscribers():
    bus = EventBus()
    queue1 = await bus.subscribe(EventType.JOB_STATUS_CHANGED)
    queue2 = await bus.subscribe(EventType.JOB_STATUS_CHANGED)

    event = JobEvent.create_status_changed("job-123", "import", "pending")
    await bus.publish(event)

    received1 = await queue1.get()
    received2 = await queue2.get()

    assert received1.data["job_id"] == received2.data["job_id"]


@pytest.mark.asyncio
async def test_subscribe_to_all_events():
    bus = EventBus()
    queue = await bus.subscribe(event_type=None)  # Subscribe to all events

    event1 = JobEvent.create_status_changed("job-123", "import", "pending")
    event2 = JobEvent.create_progress_updated("job-123", "import", 50, 100)

    await bus.publish(event1)
    await bus.publish(event2)

    received1 = await asyncio.wait_for(queue.get(), timeout=1.0)
    received2 = await asyncio.wait_for(queue.get(), timeout=1.0)

    assert received1.type == EventType.JOB_STATUS_CHANGED
    assert received2.type == EventType.JOB_PROGRESS_UPDATED


@pytest.mark.asyncio
async def test_unsubscribe():
    bus = EventBus()
    queue = await bus.subscribe(EventType.JOB_STATUS_CHANGED)

    # Unsubscribe before publishing
    await bus.unsubscribe(queue, EventType.JOB_STATUS_CHANGED)

    event = JobEvent.create_status_changed("job-123", "import", "pending")
    await bus.publish(event)

    # Queue should be empty since we unsubscribed
    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(queue.get(), timeout=0.1)


@pytest.mark.asyncio
async def test_event_to_dict():
    event = JobEvent.create_status_changed("job-123", "import", "pending")
    event_dict = event.to_dict()

    assert event_dict["type"] == EventType.JOB_STATUS_CHANGED
    assert event_dict["data"]["job_id"] == "job-123"
    assert event_dict["data"]["job_type"] == "import"
    assert event_dict["data"]["status"] == "pending"
    assert "timestamp" in event_dict


@pytest.mark.asyncio
async def test_progress_event_calculation():
    event = JobEvent.create_progress_updated("job-123", "import", 50, 100)

    assert event.data["current"] == 50
    assert event.data["total"] == 100
    assert event.data["percent"] == 50

    # Test edge case: 0 total
    event_zero = JobEvent.create_progress_updated("job-123", "import", 0, 0)
    assert event_zero.data["percent"] == 0

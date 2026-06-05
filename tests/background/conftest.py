from __future__ import annotations

import pytest

from blunder_tutor.events.event_bus import EventBus


@pytest.fixture
async def event_bus() -> EventBus:
    return EventBus()

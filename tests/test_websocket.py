def test_websocket_connection(app):
    with app.websocket_connect("/ws") as websocket:
        # Subscribe to job events
        websocket.send_json({"action": "subscribe", "events": ["job.created"]})

        # Should receive subscription confirmation
        response = websocket.receive_json()
        assert response["type"] == "subscribed"
        assert "job.created" in response["events"]


def test_websocket_ping_pong(app):
    with app.websocket_connect("/ws") as websocket:
        # Send ping
        websocket.send_json({"action": "ping"})

        # Should receive pong
        response = websocket.receive_json()
        assert response["type"] == "pong"


def test_websocket_multiple_subscriptions(app):
    with app.websocket_connect("/ws") as websocket:
        # Subscribe to multiple events
        websocket.send_json(
            {
                "action": "subscribe",
                "events": ["job.created", "job.status_changed", "stats.updated"],
            }
        )

        # Should receive confirmation with all events
        response = websocket.receive_json()
        assert response["type"] == "subscribed"
        assert "job.created" in response["events"]
        assert "job.status_changed" in response["events"]
        assert "stats.updated" in response["events"]


def test_websocket_invalid_event_type(app):
    with app.websocket_connect("/ws") as websocket:
        # Subscribe with some invalid event types
        websocket.send_json(
            {
                "action": "subscribe",
                "events": ["job.created", "invalid.event.type", "job.completed"],
            }
        )

        # Should still receive confirmation (invalid types are skipped)
        response = websocket.receive_json()
        assert response["type"] == "subscribed"

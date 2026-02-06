/**
 * WebSocket client for real-time updates.
 *
 * Usage:
 *   const client = new WebSocketClient();
 *   client.connect();
 *   client.subscribe(['job.progress_updated', 'job.completed']);
 *   client.on('job.progress_updated', (data) => {
 *     console.log('Progress:', data);
 *   });
 */
class WebSocketClient {
    constructor(url = '/ws') {
        this.url = `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}${url}`;
        this.ws = null;
        this.reconnectInterval = 3000;
        this.handlers = {};
        this.subscriptions = [];
        this.connected = false;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 10;
    }

    connect() {
        if (this.ws && this.connected) {
            console.log('WebSocket already connected');
            return;
        }

        console.log('Connecting to WebSocket:', this.url);
        this.ws = new WebSocket(this.url);

        this.ws.onopen = () => {
            console.log('WebSocket connected');
            this.connected = true;
            this.reconnectAttempts = 0;

            // Resubscribe to events after reconnection
            if (this.subscriptions.length > 0) {
                this.subscribe(this.subscriptions);
            }

            // Start heartbeat
            this.startHeartbeat();
        };

        this.ws.onmessage = (event) => {
            const message = JSON.parse(event.data);
            this.handleMessage(message);
        };

        this.ws.onclose = () => {
            console.log('WebSocket disconnected');
            this.connected = false;

            if (this.heartbeatInterval) {
                clearInterval(this.heartbeatInterval);
            }

            // Attempt reconnection with exponential backoff
            if (this.reconnectAttempts < this.maxReconnectAttempts) {
                this.reconnectAttempts++;
                const delay = Math.min(30000, this.reconnectInterval * Math.pow(2, this.reconnectAttempts - 1));
                console.log(`Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
                setTimeout(() => this.connect(), delay);
            } else {
                console.error('Max reconnection attempts reached');
            }
        };

        this.ws.onerror = (error) => {
            console.error('WebSocket error:', error);
        };
    }

    subscribe(eventTypes) {
        if (!Array.isArray(eventTypes)) {
            eventTypes = [eventTypes];
        }

        // Store subscriptions for reconnection
        this.subscriptions = [...new Set([...this.subscriptions, ...eventTypes])];

        if (this.connected) {
            this.ws.send(JSON.stringify({
                action: 'subscribe',
                events: eventTypes
            }));
        }
    }

    on(eventType, handler) {
        if (!this.handlers[eventType]) {
            this.handlers[eventType] = [];
        }
        this.handlers[eventType].push(handler);
    }

    off(eventType, handler) {
        if (this.handlers[eventType]) {
            if (handler) {
                this.handlers[eventType] = this.handlers[eventType].filter(h => h !== handler);
            } else {
                delete this.handlers[eventType];
            }
        }
    }

    handleMessage(message) {
        const handlers = this.handlers[message.type] || [];
        handlers.forEach(handler => {
            try {
                handler(message.data, message);
            } catch (error) {
                console.error('Error in message handler:', error);
            }
        });
    }

    startHeartbeat() {
        this.heartbeatInterval = setInterval(() => {
            if (this.connected) {
                this.ws.send(JSON.stringify({ action: 'ping' }));
            }
        }, 30000); // Every 30 seconds
    }

    disconnect() {
        if (this.heartbeatInterval) {
            clearInterval(this.heartbeatInterval);
        }
        if (this.ws) {
            this.reconnectAttempts = this.maxReconnectAttempts; // Prevent reconnection
            this.ws.close();
        }
    }
}

export { WebSocketClient };

const WebSocket = require('ws');
const EventEmitter = require('events');

class PythonTelemetryClient extends EventEmitter {
    constructor() {
        super();
        this.ws = null;
        this.isConnected = false;
        this.sessionInfo = null;
        this.telemetry = null;
        this.reconnectInterval = 5000;
        this.reconnectTimer = null;
    }
    
    connect() {
        try {
            this.ws = new WebSocket('ws://localhost:8082');
            
            this.ws.on('open', () => {
                console.log('[GT3] Connected to Python telemetry server');
                this.isConnected = true;
                if (this.reconnectTimer) {
                    clearTimeout(this.reconnectTimer);
                    this.reconnectTimer = null;
                }
            });
            
            this.ws.on('message', (data) => {
                try {
                    const message = JSON.parse(data.toString());
                    this.handleMessage(message);
                } catch (error) {
                    console.error('[GT3] Error parsing telemetry message:', error);
                }
            });
            
            this.ws.on('close', () => {
                console.log('[GT3] Disconnected from Python telemetry server');
                this.isConnected = false;
                this.scheduleReconnect();
            });
            
            this.ws.on('error', (error) => {
                console.error('[GT3] WebSocket error:', error);
            });
            
        } catch (error) {
            console.error('[GT3] Connection error:', error);
            this.scheduleReconnect();
        }
    }
    
    handleMessage(message) {
        switch (message.type) {
            case 'Connected':
                console.log('[GT3] iRacing connection status:', message.message);
                this.emit('Connected');
                break;
                
            case 'Disconnected':
                console.log('[GT3] iRacing disconnected');
                this.emit('Disconnected');
                break;
                
            case 'SessionInfo':
                this.sessionInfo = message.data;
                this.emit('SessionInfo', message.data);
                break;
                
            case 'Telemetry':
                this.telemetry = message.data;
                this.emit('Telemetry', message.data);
                break;
        }
    }
    
    scheduleReconnect() {
        if (this.reconnectTimer) return;
        
        console.log('[GT3] Reconnecting to Python server in 5 seconds...');
        this.reconnectTimer = setTimeout(() => {
            this.reconnectTimer = null;
            this.connect();
        }, this.reconnectInterval);
    }
    
    disconnect() {
        if (this.reconnectTimer) {
            clearTimeout(this.reconnectTimer);
            this.reconnectTimer = null;
        }
        if (this.ws) {
            this.ws.close();
            this.ws = null;
        }
    }
}

module.exports = PythonTelemetryClient;
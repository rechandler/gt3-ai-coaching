// src/telemetry-server.js
// COMPLETE REPLACEMENT - GT3 AI Coaching Telemetry Server using Python backend

const CoachingAgentClient = require('./coaching-agent-client');
const EventEmitter = require('events');

class EnhancedIRacingTelemetryServer extends EventEmitter {
    constructor() {
        super();
        
        // Replace node-irsdk with Python client
        this.pythonClient = new CoachingAgentClient();
        
        // State management
        this.isConnectedToIRacing = false;
        this.currentSessionInfo = null;
        this.currentTelemetry = null;
        
        // GT3 specific data
        this.currentCar = null;
        this.currentTrack = null;
        this.lastLapTime = null;
        this.bestLapTime = null;
        
        // Setup event handlers
        this.setupEventHandlers();
        
        // Start connection
        this.connectToIRacing();
        
        console.log('[GT3 Telemetry] Enhanced iRacing Telemetry Server initialized with Python backend');
    }
    
    setupEventHandlers() {
        this.pythonClient.on('Connected', () => {
            console.log('[GT3 Telemetry] Connected to iRacing via Coaching Agent server');
            this.isConnectedToIRacing = true;
            this.emit('Connected');
        });
        
        this.pythonClient.on('Disconnected', () => {
            console.log('[GT3 Telemetry] Disconnected from iRacing');
            this.isConnectedToIRacing = false;
            this.emit('Disconnected');
        });
        
        this.pythonClient.on('SessionInfo', (sessionInfo) => {
            console.log('[GT3 Telemetry] Session info received');
            this.currentSessionInfo = sessionInfo;
            this.processSessionInfo(sessionInfo);
            this.emit('SessionInfo', sessionInfo);
        });
        
        this.pythonClient.on('Telemetry', (telemetry) => {
            this.currentTelemetry = telemetry;
            this.processTelemetry(telemetry);
            this.emit('Telemetry', telemetry);
        });
        
        this.pythonClient.on('Error', (error) => {
            console.error('[GT3 Telemetry] Error:', error);
            this.emit('Error', error);
        });
    }
    
    connectToIRacing() {
        console.log('[GT3 Telemetry] Connecting to Coaching Agent server...');
        this.pythonClient.connect();
    }
    
    processSessionInfo(sessionInfo) {
        try {
            // Extract car information
            if (sessionInfo.DriverInfo && sessionInfo.DriverInfo.Drivers) {
                const playerDriver = sessionInfo.DriverInfo.Drivers.find(driver => 
                    driver.CarIdx === sessionInfo.DriverInfo.DriverCarIdx
                );
                if (playerDriver) {
                    this.currentCar = {
                        name: playerDriver.CarScreenName,
                        path: playerDriver.CarPath,
                        id: playerDriver.CarID
                    };
                    console.log(`[Telemetry] Current car: ${this.currentCar.name}`);
                }
            }
            // Extract track and category information
            if (sessionInfo.WeekendInfo) {
                this.currentTrack = {
                    name: sessionInfo.WeekendInfo.TrackDisplayName,
                    config: sessionInfo.WeekendInfo.TrackConfigName,
                    id: sessionInfo.WeekendInfo.TrackID,
                    length: sessionInfo.WeekendInfo.TrackLength,
                    category: sessionInfo.WeekendInfo.Category || 'Unknown'
                };
                console.log(`[Telemetry] Current track: ${this.currentTrack.name} (${this.currentTrack.config}), Category: ${this.currentTrack.category}`);
            }
            // Category-specific session processing
            this.processCategorySessionInfo(sessionInfo);
        } catch (error) {
            console.error('[Telemetry] Error processing session info:', error);
        }
    }
    
    processCategorySessionInfo(sessionInfo) {
        // Category-specific car validation (example: can be extended for other categories)
        if (this.currentCar && this.currentTrack && this.currentTrack.category) {
            // Example: emit event for detected car/category
            this.emit(`${this.currentTrack.category}CarDetected`, this.currentCar);
        }
    }
    
    processTelemetry(telemetry) {
        try {
            // Category-specific telemetry processing
            this.processCategoryTelemetry(telemetry);
            
            // Shared telemetry processing
            this.processLapTimes(telemetry);
            
            // Analyze telemetry data for coaching insights
            this.analyzePerformance(telemetry);
            
        } catch (error) {
            console.error('[Telemetry] Error processing telemetry:', error);
        }
    }
    
    processCategoryTelemetry(telemetry) {
        if (!this.currentTrack) return;
        
        const category = this.currentTrack.category.toLowerCase();
        
        // Example: GT3 specific processing
        if (category.includes('gt3')) {
            if (telemetry.TireTemp) {
                this.analyzeTireTemperatures(telemetry.TireTemp);
            }
            if (telemetry.BrakeTemp) {
                this.analyzeBrakeTemperatures(telemetry.BrakeTemp);
            }
            if (telemetry.FuelLevel) {
                this.analyzeFuelStrategy(telemetry);
            }
        }
        
        // Pass telemetry to category-specific analysis
        this.emit('CategoryTelemetry', { category, telemetry });
    }
    
    processPaceFlags(paceFlags) {
        const flagMap = {
            1: 'checkered',
            2: 'white',
            4: 'green',
            8: 'yellow',
            16: 'red',
            32: 'blue',
            64: 'debris',
            128: 'crossed',
            256: 'furled'
        };
        
        const activeFlags = [];
        for (const flag in flagMap) {
            if (paceFlags & flag) {
                activeFlags.push(flagMap[flag]);
            }
        }
        
        if (activeFlags.length > 0) {
            this.emit('PaceFlags', activeFlags);
        }
    }
    
    processLapTimes(telemetry) {
        if (telemetry.LapLastLapTime && telemetry.LapLastLapTime !== this.lastLapTime) {
            this.lastLapTime = telemetry.LapLastLapTime;
            this.emit('LapCompleted', this.lastLapTime);
            
            if (!this.bestLapTime || this.lastLapTime < this.bestLapTime) {
                this.bestLapTime = this.lastLapTime;
                this.emit('BestLap', this.bestLapTime);
            }
        }
    }
    
    analyzeTireTemperatures(tireTemps) {
        const warnings = [];
        const thresholds = {
            cold: 70,  // C
            hot: 110 // C
        };
        
        const tirePositions = ['LF', 'RF', 'LR', 'RR'];
        for (const pos of tirePositions) {
            const temp = tireTemps[pos];
            if (temp < thresholds.cold) {
                warnings.push(`${pos} tires are cold (${temp.toFixed(1)}°C)`);
            } else if (temp > thresholds.hot) {
                warnings.push(`${pos} tires are overheating (${temp.toFixed(1)}°C)`);
            }
        }
        
        if (warnings.length > 0) {
            this.emit('TireWarning', { type: 'temperature', warnings });
        }
    }
    
    analyzeBrakeTemperatures(brakePressures) {
        const warnings = [];
        const pressureThreshold = 0.9; // 90% brake pressure
        
        // Assuming brake pressures are an array [LF, RF, LR, RR]
        const [lf, rf, lr, rr] = brakePressures;
        
        if (lf > pressureThreshold || rf > pressureThreshold) {
            warnings.push('High brake pressure detected, risk of lock-up');
        }
        
        if (warnings.length > 0) {
            this.emit('BrakeWarning', { type: 'pressure', warnings });
        }
    }
    
    analyzeFuelStrategy(telemetry) {
        const fuelLevel = telemetry.FuelLevel;
        const fuelRemaining = telemetry.FuelLapsRemaining;
        const sessionLaps = telemetry.SessionLaps;
        const sessionTime = telemetry.SessionTime;
        
        const warnings = [];
        
        if (fuelRemaining < 2) {
            warnings.push(`Low fuel: ${fuelRemaining.toFixed(1)} laps remaining`);
        }
        
        // Example: check if fuel will last the session
        if (sessionLaps > 0 && fuelRemaining < sessionLaps) {
            warnings.push('Fuel will not last the session');
        }
        
        if (warnings.length > 0) {
            this.emit('FuelWarning', { type: 'level', warnings });
        }
    }
    
    analyzePerformance(telemetry) {
        // Example: analyze speed and gear usage
        const speed = telemetry.Speed;
        const gear = telemetry.Gear;
        const rpm = telemetry.RPM;
        
        const analysis = {
            speed: speed,
            gear: gear,
            rpm: rpm
        };
        
        this.emit('PerformanceUpdate', analysis);
    }
    
    getCategoryAnalysis(telemetry) {
        // This function would contain more detailed, category-specific analysis
        // For example, IndyCar vs. GT3 specific logic
        return {};
    }
    
    formatTime(seconds) {
        const minutes = Math.floor(seconds / 60);
        const secs = (seconds % 60).toFixed(3);
        return `${minutes}:${secs.padStart(6, '0')}`;
    }
    
    get sessionInfo() {
        return this.currentSessionInfo;
    }
    
    get telemetry() {
        return this.currentTelemetry;
    }
    
    get isConnected() {
        return this.isConnectedToIRacing;
    }
    
    // Additional getters for easy access
    getCurrentCar() {
        return this.currentCar;
    }
    
    getCurrentTrack() {
        return this.currentTrack;
    }
    
    disconnect() {
        if (this.pythonClient) {
            this.pythonClient.disconnect();
        }
    }
}

module.exports = EnhancedIRacingTelemetryServer;

// If running directly (for testing)
if (require.main === module) {
    const server = new EnhancedIRacingTelemetryServer();
    
    // Test event handlers
    server.on('Connected', () => {
        console.log('✅ GT3 Telemetry Server Connected');
    });
    
    server.on('GT3CarDetected', (car) => {
        console.log(`🏎️  GT3 Car: ${car.name}`);
    });
    
    server.on('LapCompleted', (lapTime) => {
        console.log(`🏁 Lap completed: ${server.formatTime(lapTime)}`);
    });
    
    server.on('TireWarning', (warning) => {
        console.log('🔥 Tire Warning:', warning.warnings.join(', '));
    });
    
    server.on('FuelWarning', (warning) => {
        console.log('⛽ Fuel Warning:', warning.message);
    });
    
    // Graceful shutdown
    process.on('SIGINT', () => {
        console.log('\n[GT3 Telemetry] Shutting down...');
        server.disconnect();
        process.exit(0);
    });
    
    console.log('[GT3 Telemetry] Server started. Waiting for iRacing...');
}
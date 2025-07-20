// src/telemetry-server.js
// COMPLETE REPLACEMENT - GT3 AI Coaching Telemetry Server using Python backend

const PythonTelemetryClient = require('./python-telemetry-client');
const EventEmitter = require('events');

class EnhancedIRacingTelemetryServer extends EventEmitter {
    constructor() {
        super();
        
        // Replace node-irsdk with Python client
        this.pythonClient = new PythonTelemetryClient();
        
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
            console.log('[GT3 Telemetry] Connected to iRacing via Python server');
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
        console.log('[GT3 Telemetry] Connecting to Python telemetry server...');
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
            if (telemetry.PaceFlags !== undefined) {
                this.processPaceFlags(telemetry.PaceFlags);
            }
            if (telemetry.LapCurrentLapTime !== undefined) {
                this.processLapTimes(telemetry);
            }
            // Category-specific telemetry processing
            this.processCategoryTelemetry(telemetry);
        } catch (error) {
            console.error('[Telemetry] Error processing telemetry:', error);
        }
    }
    processCategoryTelemetry(telemetry) {
        // Category-specific telemetry processing (type-agnostic)
        // Example: tire/brake/fuel/performance analysis can be made generic or extended per category
        if (telemetry.TireTemps) {
            this.analyzeTireTemperatures(telemetry.TireTemps);
        }
        if (telemetry.BrakePressures) {
            this.analyzeBrakeTemperatures(telemetry.BrakePressures);
        }
        if (telemetry.FuelLevel !== undefined && telemetry.FuelUsePerHour !== undefined) {
            this.analyzeFuelStrategy(telemetry);
        }
        if (telemetry.Speed !== undefined && telemetry.RPM !== undefined) {
            this.analyzePerformance(telemetry);
        }
        // Emit processed category data
        const category = this.currentTrack?.category || 'Unknown';
        this.emit(`${category}Telemetry`, {
            car: this.currentCar,
            track: this.currentTrack,
            telemetry: telemetry,
            analysis: this.getCategoryAnalysis(telemetry)
        });
    }
    processPaceFlags(paceFlags) {
        // Handle pace flags - no converter issues with Python backend!
        if (paceFlags & 0x00000001) { // EndOfLine
            this.emit('PaceFlag', 'EndOfLine');
        }
        if (paceFlags & 0x00000002) { // FreePass
            this.emit('PaceFlag', 'FreePass');
        }
        if (paceFlags & 0x00000004) { // WavedAround
            this.emit('PaceFlag', 'WavedAround');
        }
        if (paceFlags & 0x00000200) { // Caution
            this.emit('PaceFlag', 'Caution');
        }
        if (paceFlags & 0x00002000) { // Green
            this.emit('PaceFlag', 'Green');
        }
        if (paceFlags & 0x00004000) { // Yellow
            this.emit('PaceFlag', 'Yellow');
        }
        if (paceFlags & 0x00008000) { // Red
            this.emit('PaceFlag', 'Red');
        }
    }
    
    processLapTimes(telemetry) {
        // Track lap time improvements
        if (telemetry.LapLastLapTime && telemetry.LapLastLapTime > 0) {
            if (!this.lastLapTime || telemetry.LapLastLapTime !== this.lastLapTime) {
                this.lastLapTime = telemetry.LapLastLapTime;
                console.log(`[GT3 Telemetry] Lap completed: ${this.formatTime(this.lastLapTime)}`);
                this.emit('LapCompleted', this.lastLapTime);
            }
        }
        
        if (telemetry.LapBestLapTime && telemetry.LapBestLapTime > 0) {
            if (!this.bestLapTime || telemetry.LapBestLapTime !== this.bestLapTime) {
                this.bestLapTime = telemetry.LapBestLapTime;
                console.log(`[GT3 Telemetry] New best lap: ${this.formatTime(this.bestLapTime)}`);
                this.emit('BestLap', this.bestLapTime);
            }
        }
    }
    
    analyzeTireTemperatures(tireTemps) {
        // GT3 tire temperature analysis
        const analysis = {
            optimal: true,
            warnings: []
        };
        
        // Check for overheating (GT3 optimal range: 80-100°C)
        Object.entries(tireTemps).forEach(([tire, temp]) => {
            if (temp > 100) {
                analysis.optimal = false;
                analysis.warnings.push(`${tire} overheating: ${temp.toFixed(1)}°C`);
            } else if (temp < 80) {
                analysis.optimal = false;
                analysis.warnings.push(`${tire} too cold: ${temp.toFixed(1)}°C`);
            }
        });
        
        if (analysis.warnings.length > 0) {
            this.emit('TireWarning', analysis);
        }
    }
    
    analyzeBrakeTemperatures(brakePressures) {
        // GT3 brake analysis
        const maxPressure = Math.max(...Object.values(brakePressures));
        const minPressure = Math.min(...Object.values(brakePressures));
        
        if (maxPressure > 800) { // High brake pressure threshold
            this.emit('BrakeWarning', {
                type: 'HighPressure',
                maxPressure: maxPressure,
                message: 'High brake pressure detected'
            });
        }
        
        // Check for brake balance issues
        const frontAvg = (brakePressures.LFbrakeLinePress + brakePressures.RFbrakeLinePress) / 2;
        const rearAvg = (brakePressures.LRbrakeLinePress + brakePressures.RRbrakeLinePress) / 2;
        
        if (frontAvg > 0 && rearAvg > 0) {
            const balance = frontAvg / (frontAvg + rearAvg);
            if (balance < 0.55 || balance > 0.75) {
                this.emit('BrakeWarning', {
                    type: 'Balance',
                    balance: balance,
                    message: `Brake balance: ${(balance * 100).toFixed(1)}% front`
                });
            }
        }
    }
    
    analyzeFuelStrategy(telemetry) {
        // GT3 fuel strategy analysis
        const fuelLevel = telemetry.FuelLevel;
        const fuelUseRate = telemetry.FuelUsePerHour;
        
        if (fuelLevel < 10) { // Low fuel warning
            this.emit('FuelWarning', {
                type: 'LowFuel',
                level: fuelLevel,
                message: `Low fuel: ${fuelLevel.toFixed(1)}L remaining`
            });
        }
        
        // Calculate laps remaining
        if (fuelUseRate > 0 && telemetry.LapLastLapTime > 0) {
            const lapsPerHour = 3600 / telemetry.LapLastLapTime;
            const fuelPerLap = fuelUseRate / lapsPerHour;
            const lapsRemaining = Math.floor(fuelLevel / fuelPerLap);
            
            this.emit('FuelStrategy', {
                fuelLevel: fuelLevel,
                fuelPerLap: fuelPerLap,
                lapsRemaining: lapsRemaining
            });
        }
    }
    
    analyzePerformance(telemetry) {
        // GT3 performance analysis
        const performance = {
            speed: telemetry.Speed,
            rpm: telemetry.RPM,
            gear: telemetry.Gear,
            throttle: telemetry.Throttle,
            brake: telemetry.Brake,
            steering: telemetry.Steering
        };
        
        // Analyze driving style
        if (telemetry.Throttle > 0.95 && telemetry.Brake > 0.1) {
            this.emit('DrivingWarning', {
                type: 'ThrottleBrake',
                message: 'Throttle and brake applied simultaneously'
            });
        }
        
        this.emit('PerformanceData', performance);
    }
    
    getCategoryAnalysis(telemetry) {
        // Generic analysis (can be extended per category)
        return {
            timestamp: Date.now(),
            car: this.currentCar?.name,
            track: this.currentTrack?.name,
            lapTime: telemetry.LapCurrentLapTime,
            speed: telemetry.Speed,
            rpm: telemetry.RPM,
            gear: telemetry.Gear,
            fuelLevel: telemetry.FuelLevel,
            tireTemps: telemetry.TireTemps,
            brakes: telemetry.BrakePressures,
            flags: {
                session: telemetry.SessionFlags,
                pace: telemetry.PaceFlags
            }
        };
    }
    
    formatTime(seconds) {
        const mins = Math.floor(seconds / 60);
        const secs = (seconds % 60).toFixed(3);
        return `${mins}:${secs.padStart(6, '0')}`;
    }
    
    // Compatibility methods for existing code
    get sessionInfo() {
        return this.currentSessionInfo;
    }
    
    get telemetry() {
        return this.currentTelemetry;
    }
    
    get isConnected() {
        return this.isConnectedToIRacing;
    }
    
    // Method to get current car info
    getCurrentCar() {
        return this.currentCar;
    }
    
    // Method to get current track info
    getCurrentTrack() {
        return this.currentTrack;
    }
    
    // Method to disconnect
    disconnect() {
        console.log('[GT3 Telemetry] Disconnecting...');
        this.pythonClient.disconnect();
    }
}

// Export the enhanced telemetry server
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
// Enhanced GT3 Telemetry Server with Rule-Based AI Integration
const irsdk = require('node-irsdk');
const WebSocket = require('ws');

class GT3RuleBasedCoach {
  constructor() {
    this.sessionData = [];
    this.personalBests = {};
    this.drivingPatterns = {};
    this.trackKnowledge = this.initializeTrackKnowledge();
    this.carKnowledge = this.initializeCarKnowledge();
    this.userProfile = this.initializeUserProfile();
  }

  initializeTrackKnowledge() {
    return {
      'Road Atlanta': {
        optimalTireTemp: { min: 200, max: 240 },
        criticalBrakingZones: [0.15, 0.35, 0.75],
        fuelConsumption: 2.8,
        keyTurns: {
          0.15: 'Turn 1: Brake at 200ft board, trail brake to apex',
          0.35: 'Turn 3: Late brake, quick rotation, early throttle',
          0.75: 'Turn 10A: Brake hard, set up for 10B exit'
        }
      },
      'Watkins Glen': {
        optimalTireTemp: { min: 190, max: 230 },
        criticalBrakingZones: [0.08, 0.25, 0.55],
        fuelConsumption: 2.5,
        keyTurns: {
          0.08: 'Turn 1: Brake at 300ft, carry speed through',
          0.25: 'Chicane: Brake straight, quick direction changes',
          0.55: 'Boot: Brake early, maximize exit speed'
        }
      },
      'Monza': {
        optimalTireTemp: { min: 210, max: 250 },
        criticalBrakingZones: [0.18, 0.45, 0.65],
        fuelConsumption: 3.2,
        keyTurns: {
          0.18: 'Turn 1: Brake at chicane, watch for dive bombs',
          0.45: 'Lesmo 1: Brake early, set up for Lesmo 2',
          0.65: 'Parabolica: Long corner, patience on throttle'
        }
      },
      'Silverstone': {
        optimalTireTemp: { min: 195, max: 235 },
        criticalBrakingZones: [0.12, 0.28, 0.52],
        fuelConsumption: 2.9,
        keyTurns: {
          0.12: 'Copse: Flat out, small lift if needed',
          0.28: 'Brooklands: Late apex, early throttle',
          0.52: 'Stowe: Brake hard, quick rotation'
        }
      }
    };
  }

  initializeCarKnowledge() {
    return {
      'Porsche 911 GT3 R': {
        optimalTireTemp: { min: 200, max: 240 },
        brakeTempLimit: 1200,
        fuelCapacity: 120,
        characteristics: {
          rearBias: true,
          earlyBraking: true,
          tireWarmup: 'fast'
        }
      },
      'Mercedes AMG GT3': {
        optimalTireTemp: { min: 190, max: 230 },
        brakeTempLimit: 1250,
        fuelCapacity: 125,
        characteristics: {
          rearBias: false,
          earlyBraking: false,
          tireWarmup: 'medium'
        }
      },
      'BMW M4 GT3': {
        optimalTireTemp: { min: 195, max: 235 },
        brakeTempLimit: 1180,
        fuelCapacity: 115,
        characteristics: {
          rearBias: false,
          earlyBraking: false,
          tireWarmup: 'slow'
        }
      },
      'Audi R8 LMS GT3': {
        optimalTireTemp: { min: 200, max: 240 },
        brakeTempLimit: 1220,
        fuelCapacity: 118,
        characteristics: {
          rearBias: true,
          earlyBraking: true,
          tireWarmup: 'medium'
        }
      },
      'Ferrari 488 GT3': {
        optimalTireTemp: { min: 205, max: 245 },
        brakeTempLimit: 1240,
        fuelCapacity: 120,
        characteristics: {
          rearBias: true,
          earlyBraking: false,
          tireWarmup: 'fast'
        }
      }
    };
  }

  initializeUserProfile() {
    return {
      experienceLevel: 'intermediate',
      weakAreas: [],
      consistency: 100,
      sessionsCompleted: 0
    };
  }

  analyzeAndCoach(telemetryData) {
    this.sessionData.push(telemetryData);
    
    const analyses = {
      tire: this.analyzeTireManagement(telemetryData),
      brake: this.analyzeBraking(telemetryData),
      fuel: this.analyzeFuelStrategy(telemetryData),
      driving: this.analyzeDrivingTechnique(telemetryData),
      race: this.analyzeRaceStrategy(telemetryData)
    };

    const prioritizedMessages = this.prioritizeCoaching(analyses);
    this.updateUserProfile(telemetryData, analyses);
    
    return {
      primaryMessage: prioritizedMessages[0],
      secondaryMessages: prioritizedMessages.slice(1, 3),
      analyses: analyses,
      confidence: this.calculateConfidence(telemetryData)
    };
  }

  analyzeTireManagement(data) {
    const trackInfo = this.trackKnowledge[data.trackName];
    const carInfo = this.carKnowledge[data.carName];
    
    if (!trackInfo || !carInfo) {
      return { priority: 0, messages: [] };
    }

    const messages = [];
    const avgTireTemp = (data.tireTempLF + data.tireTempRF + data.tireTempLR + data.tireTempRR) / 4;
    const tempDiff = Math.max(data.tireTempLF, data.tireTempRF, data.tireTempLR, data.tireTempRR) - 
                     Math.min(data.tireTempLF, data.tireTempRF, data.tireTempLR, data.tireTempRR);
    
    if (avgTireTemp > carInfo.optimalTireTemp.max + 20) {
      messages.push({
        priority: 9,
        message: `Critical tire overheating (${avgTireTemp.toFixed(0)}°F) - Reduce tire pressure by 1-2 PSI`,
        category: 'critical'
      });
    } else if (avgTireTemp > carInfo.optimalTireTemp.max + 10) {
      messages.push({
        priority: 7,
        message: `Tires running hot (${avgTireTemp.toFixed(0)}°F) - Ease off in fast corners`,
        category: 'warning'
      });
    } else if (avgTireTemp < carInfo.optimalTireTemp.min - 10) {
      const warmupAdvice = carInfo.characteristics.tireWarmup === 'fast' ? 
        'Push harder to warm up' : 'Use tire blankets or gentle weaving';
      messages.push({
        priority: 6,
        message: `Tires cold (${avgTireTemp.toFixed(0)}°F) - ${warmupAdvice}`,
        category: 'info'
      });
    }

    if (tempDiff > 30) {
      const hotCorner = this.identifyHotCorner(data);
      messages.push({
        priority: 8,
        message: `Uneven tire temps (${tempDiff.toFixed(0)}°F spread) - ${hotCorner} running hottest`,
        category: 'warning'
      });
    }

    return { priority: Math.max(...messages.map(m => m.priority), 0), messages };
  }

  analyzeBraking(data) {
    const trackInfo = this.trackKnowledge[data.trackName];
    const carInfo = this.carKnowledge[data.carName];
    
    if (!trackInfo || !carInfo) {
      return { priority: 0, messages: [] };
    }

    const messages = [];
    const maxBrakeTemp = Math.max(data.brakeTempLF, data.brakeTempRF);
    
    if (maxBrakeTemp > carInfo.brakeTempLimit + 100) {
      messages.push({
        priority: 10,
        message: `BRAKE FADE IMMINENT (${maxBrakeTemp.toFixed(0)}°F) - Brake 100ft earlier`,
        category: 'critical'
      });
    } else if (maxBrakeTemp > carInfo.brakeTempLimit + 50) {
      messages.push({
        priority: 8,
        message: `Brake temps high (${maxBrakeTemp.toFixed(0)}°F) - Brake earlier and lighter`,
        category: 'warning'
      });
    } else if (maxBrakeTemp > carInfo.brakeTempLimit) {
      messages.push({
        priority: 6,
        message: `Brake temps rising (${maxBrakeTemp.toFixed(0)}°F) - Monitor closely`,
        category: 'info'
      });
    }

    // Track-specific braking advice
    const lapDistance = data.lapDistPct;
    const nearBrakingZone = trackInfo.criticalBrakingZones.find(zone => 
      Math.abs(lapDistance - zone) < 0.03
    );
    
    if (nearBrakingZone && data.brake > 0.7) {
      const turnAdvice = trackInfo.keyTurns[nearBrakingZone];
      if (turnAdvice) {
        messages.push({
          priority: 7,
          message: turnAdvice,
          category: 'technique'
        });
      }
    }

    // Braking technique analysis
    if (data.brake > 0.95 && data.speed > 100) {
      const technique = carInfo.characteristics.earlyBraking ? 
        'Brake earlier with less pressure' : 'Brake later but harder';
      messages.push({
        priority: 5,
        message: `Braking too aggressive - ${technique}`,
        category: 'technique'
      });
    }

    return { priority: Math.max(...messages.map(m => m.priority), 0), messages };
  }

  analyzeFuelStrategy(data) {
    const trackInfo = this.trackKnowledge[data.trackName];
    
    if (!trackInfo) {
      return { priority: 0, messages: [] };
    }

    const messages = [];
    const estimatedConsumption = trackInfo.fuelConsumption;
    const lapsRemaining = data.fuelLevel / estimatedConsumption;
    
    if (lapsRemaining < 1.5) {
      messages.push({
        priority: 9,
        message: `CRITICAL FUEL - ${lapsRemaining.toFixed(1)} laps remaining, PIT NOW`,
        category: 'critical'
      });
    } else if (lapsRemaining < 3) {
      messages.push({
        priority: 7,
        message: `Low fuel - ${lapsRemaining.toFixed(1)} laps remaining, pit window open`,
        category: 'warning'
      });
    } else if (lapsRemaining < 5) {
      messages.push({
        priority: 5,
        message: `Plan pit stop - ${lapsRemaining.toFixed(1)} laps of fuel remaining`,
        category: 'info'
      });
    }

    // Fuel saving when needed
    if (lapsRemaining < 8 && data.sessionLapsRemain > lapsRemaining) {
      messages.push({
        priority: 6,
        message: 'Fuel save mode - lift and coast into braking zones',
        category: 'technique'
      });
    }

    return { priority: Math.max(...messages.map(m => m.priority), 0), messages };
  }

  analyzeDrivingTechnique(data) {
    const messages = [];
    
    // Throttle application analysis
    if (data.throttle > 0.95 && data.speed < 30) {
      messages.push({
        priority: 5,
        message: 'Wheelspin detected - smoother throttle application',
        category: 'technique'
      });
    }

    // Consistency analysis
    if (this.sessionData.length > 5) {
      const consistencyScore = this.calculateConsistencyScore();
      if (consistencyScore < 85) {
        messages.push({
          priority: 4,
          message: `Consistency at ${consistencyScore}% - Focus on smooth, repeatable inputs`,
          category: 'general'
        });
      }
    }

    return { priority: Math.max(...messages.map(m => m.priority), 0), messages };
  }

  analyzeRaceStrategy(data) {
    const messages = [];
    
    // Position-based strategy
    if (data.position) {
      if (data.position <= 3) {
        messages.push({
          priority: 3,
          message: 'Maintain position - avoid risks, focus on consistency',
          category: 'strategy'
        });
      } else if (data.position > 10) {
        messages.push({
          priority: 3,
          message: 'Attack mode - take calculated risks to gain positions',
          category: 'strategy'
        });
      }
    }

    return { priority: Math.max(...messages.map(m => m.priority), 0), messages };
  }

  identifyHotCorner(data) {
    const temps = [
      { corner: 'Front Left', temp: data.tireTempLF },
      { corner: 'Front Right', temp: data.tireTempRF },
      { corner: 'Rear Left', temp: data.tireTempLR },
      { corner: 'Rear Right', temp: data.tireTempRR }
    ];
    
    return temps.reduce((hottest, current) => 
      current.temp > hottest.temp ? current : hottest
    ).corner;
  }

  prioritizeCoaching(analyses) {
    const allMessages = [];
    
    Object.values(analyses).forEach(analysis => {
      if (analysis.messages) {
        allMessages.push(...analysis.messages);
      }
    });
    
    allMessages.sort((a, b) => b.priority - a.priority);
    
    const highPriorityExists = allMessages.some(msg => msg.priority >= 8);
    if (highPriorityExists) {
      return allMessages.filter(msg => msg.priority >= 6);
    }
    
    return allMessages.slice(0, 3);
  }

  calculateConsistencyScore() {
    if (this.sessionData.length < 3) return 100;
    
    const recentLaps = this.sessionData.slice(-5);
    const lapTimes = recentLaps
      .map(lap => lap.lapCurrentLapTime)
      .filter(time => time > 0);
    
    if (lapTimes.length < 2) return 100;
    
    const avgTime = lapTimes.reduce((a, b) => a + b) / lapTimes.length;
    const variance = lapTimes.reduce((acc, time) => acc + Math.pow(time - avgTime, 2), 0) / lapTimes.length;
    const stdDev = Math.sqrt(variance);
    
    return Math.max(0, 100 - (stdDev * 50));
  }

  calculateConfidence(data) {
    let confidence = 100;
    
    if (!this.trackKnowledge[data.trackName]) confidence -= 20;
    if (!this.carKnowledge[data.carName]) confidence -= 20;
    if (this.sessionData.length < 5) confidence -= 20;
    
    return Math.max(60, confidence);
  }

  updateUserProfile(telemetryData, analyses) {
    this.userProfile.sessionsCompleted++;
    
    if (analyses.brake.priority > 7) {
      this.addWeakArea('braking');
    }
    if (analyses.tire.priority > 7) {
      this.addWeakArea('tire_management');
    }
    if (analyses.fuel.priority > 7) {
      this.addWeakArea('fuel_strategy');
    }
  }

  addWeakArea(area) {
    if (!this.userProfile.weakAreas.includes(area)) {
      this.userProfile.weakAreas.push(area);
    }
  }
}

class EnhancedIRacingTelemetryServer {
  constructor() {
    this.irsdk = irsdk;
    this.coach = new GT3RuleBasedCoach();
    this.isConnected = false;
    this.telemetryData = {};
    this.websocketServer = null;
    this.clients = new Set();
    this.personalBestLap = null;
    
    this.setupWebSocketServer();
    this.connectToIRacing();
  }

  setupWebSocketServer() {
    this.websocketServer = new WebSocket.Server({ port: 8080 });
    console.log('🚀 Enhanced WebSocket server started on port 8080');
    
    this.websocketServer.on('connection', (ws) => {
      console.log('📱 Client connected to enhanced telemetry stream');
      this.clients.add(ws);
      
      if (this.telemetryData) {
        ws.send(JSON.stringify(this.telemetryData));
      }
      
      ws.on('close', () => {
        console.log('📱 Client disconnected from telemetry stream');
        this.clients.delete(ws);
      });
    });
  }

  connectToIRacing() {
    console.log('🏎️  Connecting to iRacing with enhanced AI coaching...');
    
    this.irsdk.init({
      telemetryUpdateInterval: 100,
      sessionInfoUpdateInterval: 1000
    });

    this.irsdk.on('Connected', () => {
      console.log('✅ Connected to iRacing with enhanced AI coaching!');
      this.isConnected = true;
      this.broadcastConnectionStatus();
    });

    this.irsdk.on('Disconnected', () => {
      console.log('❌ Disconnected from iRacing');
      this.isConnected = false;
      this.broadcastConnectionStatus();
      setTimeout(() => this.connectToIRacing(), 3000);
    });

    this.irsdk.on('Telemetry', (data) => {
      this.processTelemetryData(data);
    });
  }

  processTelemetryData(data) {
    const sessionInfo = this.irsdk.getSessionInfo();
    
    if (data.LapBestLapTime > 0) {
      this.personalBestLap = data.LapBestLapTime;
    }
    
    // Basic telemetry data
    this.telemetryData = {
      isConnected: this.isConnected,
      timestamp: Date.now(),
      
      // Car data
      speed: data.Speed * 2.237,
      gear: data.Gear,
      rpm: data.RPM,
      throttle: data.Throttle,
      brake: data.Brake,
      
      // Lap data
      lap: data.Lap,
      lapDistPct: data.LapDistPct,
      lapCurrentLapTime: data.LapCurrentLapTime,
      lapLastLapTime: data.LapLastLapTime,
      lapBestLapTime: data.LapBestLapTime,
      deltaTime: this.calculateDeltaTime(data),
      
      // Temperatures
      tireTempLF: this.celsiusToFahrenheit(data.LFtempCL),
      tireTempRF: this.celsiusToFahrenheit(data.RFtempCL),
      tireTempLR: this.celsiusToFahrenheit(data.LRtempCL),
      tireTempRR: this.celsiusToFahrenheit(data.RRtempCL),
      
      brakeTempLF: this.celsiusToFahrenheit(data.LFbrakeLineTemp),
      brakeTempRF: this.celsiusToFahrenheit(data.RFbrakeLineTemp),
      
      // Fuel
      fuelLevel: data.FuelLevel,
      fuelLevelPct: data.FuelLevelPct,
      fuelUsePerHour: data.FuelUsePerHour,
      
      // Session info
      sessionTime: data.SessionTime,
      sessionTimeRemain: data.SessionTimeRemain,
      sessionLapsRemain: data.SessionLapsRemain,
      
      // Car and track
      carName: this.getCarName(sessionInfo),
      trackName: this.getTrackName(sessionInfo),
      position: data.Position || data.ClassPosition
    };
    
    // Enhanced AI coaching analysis
    const coachingAnalysis = this.coach.analyzeAndCoach(this.telemetryData);
    
    // Add enhanced coaching to telemetry data
    this.telemetryData = {
      ...this.telemetryData,
      coachingMessage: coachingAnalysis.primaryMessage?.message || 'Maintain focus and consistency',
      coachingPriority: coachingAnalysis.primaryMessage?.priority || 0,
      coachingCategory: coachingAnalysis.primaryMessage?.category || 'general',
      secondaryMessages: coachingAnalysis.secondaryMessages || [],
      coachingConfidence: coachingAnalysis.confidence || 100,
      userProfile: this.coach.userProfile
    };
    
    this.broadcastTelemetry();
  }

  calculateDeltaTime(data) {
    if (this.personalBestLap && data.LapCurrentLapTime > 0 && data.LapDistPct > 0) {
      const estimatedLapTime = data.LapCurrentLapTime / data.LapDistPct;
      return estimatedLapTime - this.personalBestLap;
    }
    return 0;
  }

  celsiusToFahrenheit(celsius) {
    return (celsius * 9/5) + 32;
  }

  getCarName(sessionInfo) {
    try {
      return sessionInfo?.DriverInfo?.Drivers?.[0]?.CarScreenName || 'Unknown Car';
    } catch (e) {
      return 'Unknown Car';
    }
  }

  getTrackName(sessionInfo) {
    try {
      return sessionInfo?.WeekendInfo?.TrackName || 'Unknown Track';
    } catch (e) {
      return 'Unknown Track';
    }
  }

  broadcastTelemetry() {
    const message = JSON.stringify(this.telemetryData);
    
    this.clients.forEach(client => {
      if (client.readyState === WebSocket.OPEN) {
        client.send(message);
      }
    });
  }

  broadcastConnectionStatus() {
    const statusMessage = JSON.stringify({
      isConnected: this.isConnected,
      timestamp: Date.now(),
      coachingMessage: this.isConnected ? 'Enhanced AI coaching active' : 'Waiting for iRacing connection...'
    });
    
    this.clients.forEach(client => {
      if (client.readyState === WebSocket.OPEN) {
        client.send(statusMessage);
      }
    });
  }
}

// Start the enhanced server
const server = new EnhancedIRacingTelemetryServer();

process.on('SIGINT', () => {
  console.log('🛑 Shutting down enhanced telemetry server...');
  if (server.websocketServer) {
    server.websocketServer.close();
  }
  process.exit(0);
});

console.log('🧠 Enhanced GT3 AI Coaching System loaded');
console.log('🎯 Features: Track knowledge, car profiles, intelligent coaching');
console.log('💰 Cost: $0 - runs entirely locally');
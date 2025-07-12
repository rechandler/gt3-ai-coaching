#!/usr/bin/env python3
"""
Test script to check available vehicle dynamics data from iRacing SDK
for oversteer/understeer detection
"""

import irsdk
import time
import json

def test_vehicle_dynamics():
    """Test what vehicle dynamics data is available from iRacing"""
    
    try:
        # Initialize iRacing SDK
        ir = irsdk.IRSDK()
        ir.startup()
        
        if not ir.is_connected:
            print("❌ iRacing not connected - start iRacing and enter a session")
            return
            
        print("✅ Connected to iRacing!")
        print("🔍 Checking available vehicle dynamics telemetry...\n")
        
        # Vehicle dynamics fields to check for oversteer/understeer detection
        dynamics_fields = {
            # Steering and rotation
            'SteeringWheelAngle': 'Steering wheel angle (radians)',
            'SteeringWheelAngleMax': 'Maximum steering wheel angle',
            'SteeringWheelTorque': 'Steering wheel torque/force feedback',
            'YawNorth': 'Car yaw angle relative to north',
            'Yaw': 'Car yaw angle',
            'YawRate': 'Yaw rate (rotation speed)',
            'Roll': 'Car roll angle', 
            'RollRate': 'Roll rate',
            'Pitch': 'Car pitch angle',
            'PitchRate': 'Pitch rate',
            
            # Acceleration and G-forces
            'LatAccel': 'Lateral acceleration (G-force sideways)',
            'LongAccel': 'Longitudinal acceleration (G-force forward/back)',
            'VertAccel': 'Vertical acceleration (G-force up/down)',
            
            # Velocity components
            'VelocityX': 'Velocity in X direction',
            'VelocityY': 'Velocity in Y direction', 
            'VelocityZ': 'Velocity in Z direction',
            
            # Slip angles and ratios (key for oversteer/understeer)
            'LFslipAngle': 'Left front tire slip angle',
            'RFslipAngle': 'Right front tire slip angle',
            'LRslipAngle': 'Left rear tire slip angle', 
            'RRslipAngle': 'Right rear tire slip angle',
            'LFslipRatio': 'Left front tire slip ratio',
            'RFslipRatio': 'Right front tire slip ratio',
            'LRslipRatio': 'Left rear tire slip ratio',
            'RRslipRatio': 'Right rear tire slip ratio',
            
            # Tire forces
            'LFshockForce': 'Left front shock force',
            'RFshockForce': 'Right front shock force',
            'LRshockForce': 'Left rear shock force',
            'RRshockForce': 'Right rear shock force',
            
            # Track and position
            'TrackSurface': 'Track surface type',
            'PlayerTrackSurface': 'Player track surface',
            'LapDistPct': 'Lap distance percentage',
            
            # Basic controls (for correlation)
            'Throttle': 'Throttle position',
            'Brake': 'Brake position',
            'Speed': 'Vehicle speed',
            'RPM': 'Engine RPM'
        }
        
        # Test each field
        available_fields = []
        unavailable_fields = []
        
        for field_name, description in dynamics_fields.items():
            try:
                value = ir[field_name]
                if value is not None:
                    available_fields.append((field_name, description, value))
                    print(f"✅ {field_name}: {value} - {description}")
                else:
                    unavailable_fields.append((field_name, description))
                    print(f"❌ {field_name}: None - {description}")
            except Exception as e:
                unavailable_fields.append((field_name, description))
                print(f"❌ {field_name}: Error ({e}) - {description}")
        
        print(f"\n📊 Summary:")
        print(f"✅ Available fields: {len(available_fields)}")
        print(f"❌ Unavailable fields: {len(unavailable_fields)}")
        
        # Show what we can use for oversteer/understeer detection
        print(f"\n🎯 Key fields for oversteer/understeer detection:")
        key_fields = ['LatAccel', 'YawRate', 'SteeringWheelAngle', 'LFslipAngle', 'RFslipAngle', 'LRslipAngle', 'RRslipAngle']
        
        for field in key_fields:
            found = False
            for available_field, desc, value in available_fields:
                if available_field == field:
                    print(f"✅ {field}: {value} - AVAILABLE for analysis")
                    found = True
                    break
            if not found:
                print(f"❌ {field}: NOT AVAILABLE")
        
        # Sample real-time data for a few seconds if moving
        print(f"\n🔄 Sampling live data for 5 seconds...")
        
        sample_data = []
        for i in range(25):  # 5 seconds at ~5Hz
            try:
                data_point = {}
                for field_name, _, _ in available_fields[:10]:  # Sample first 10 available fields
                    data_point[field_name] = ir[field_name]
                sample_data.append(data_point)
                time.sleep(0.2)  # 5Hz sampling
            except Exception as e:
                print(f"Error sampling: {e}")
                break
        
        if sample_data:
            print(f"📈 Sample data collected ({len(sample_data)} points)")
            print(f"🎯 Speed range: {min(d.get('Speed', 0) for d in sample_data):.1f} - {max(d.get('Speed', 0) for d in sample_data):.1f}")
            
            # Check if car is moving for meaningful analysis
            max_speed = max(d.get('Speed', 0) for d in sample_data)
            if max_speed > 10:
                print(f"🏁 Car is moving! Vehicle dynamics analysis possible")
                
                # Show lateral acceleration range (key for handling analysis)
                if any('LatAccel' in d for d in sample_data):
                    lat_accels = [d.get('LatAccel', 0) for d in sample_data if 'LatAccel' in d]
                    print(f"🌊 Lateral G-force range: {min(lat_accels):.2f} to {max(lat_accels):.2f}g")
            else:
                print(f"🅿️ Car stationary - enter a session and drive for meaningful analysis")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        try:
            ir.shutdown()
        except:
            pass

if __name__ == "__main__":
    test_vehicle_dynamics()

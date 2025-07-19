#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Session API - Persistent Mistake Analysis Endpoints
==================================================

Provides API endpoints for session summaries and persistent mistake analysis.
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

logger = logging.getLogger(__name__)

# Pydantic models for API responses
class MistakePatternResponse(BaseModel):
    corner_name: str
    mistake_type: str
    frequency: int
    total_time_loss: float
    avg_time_loss: float
    priority: str
    severity_trend: str
    description: str

class SessionSummaryResponse(BaseModel):
    session_id: str
    session_duration: float
    total_mistakes: int
    total_time_lost: float
    session_score: float
    most_common_mistakes: List[MistakePatternResponse]
    most_costly_mistakes: List[MistakePatternResponse]
    improvement_areas: List[str]
    recommendations: List[str]

class CornerAnalysisResponse(BaseModel):
    corner_id: str
    corner_name: str
    total_mistakes: int
    total_time_lost: float
    mistake_types: Dict[str, Dict[str, Any]]
    recent_trend: str

class RecentMistakesResponse(BaseModel):
    corner_name: str
    mistake_type: str
    time_loss: float
    severity: float
    description: str
    timestamp: float

class SessionAPI:
    """API server for session analysis and persistent mistake tracking"""
    
    def __init__(self, coaching_agent=None):
        self.coaching_agent = coaching_agent
        self.app = FastAPI(title="GT3 Coaching Session API", version="1.0.0")
        
        # Add CORS middleware
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # Register routes
        self._register_routes()
        
        logger.info("🚀 Session API initialized")
    
    def _register_routes(self):
        """Register API routes"""
        
        @self.app.get("/")
        async def root():
            return {"message": "GT3 Coaching Session API", "version": "1.0.0"}
        
        @self.app.get("/health")
        async def health_check():
            return {"status": "healthy", "coaching_agent_active": self.coaching_agent is not None}
        
        @self.app.get("/advice/session_summary", response_model=SessionSummaryResponse)
        async def get_session_summary():
            """Get comprehensive session summary with persistent mistakes"""
            if not self.coaching_agent:
                raise HTTPException(status_code=503, detail="Coaching agent not available")
            
            try:
                summary_data = self.coaching_agent.get_session_summary()
                
                # Convert to response model
                summary = SessionSummaryResponse(
                    session_id=summary_data['session_id'],
                    session_duration=summary_data['session_duration'],
                    total_mistakes=summary_data['total_mistakes'],
                    total_time_lost=summary_data['total_time_lost'],
                    session_score=summary_data['session_score'],
                    most_common_mistakes=[
                        MistakePatternResponse(**mistake)
                        for mistake in summary_data['most_common_mistakes']
                    ],
                    most_costly_mistakes=[
                        MistakePatternResponse(**mistake)
                        for mistake in summary_data['most_costly_mistakes']
                    ],
                    improvement_areas=summary_data['improvement_areas'],
                    recommendations=summary_data['recommendations']
                )
                
                return summary
                
            except Exception as e:
                logger.error(f"Error getting session summary: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/advice/persistent_mistakes", response_model=List[MistakePatternResponse])
        async def get_persistent_mistakes():
            """Get persistent mistakes that need focus"""
            if not self.coaching_agent:
                raise HTTPException(status_code=503, detail="Coaching agent not available")
            
            try:
                persistent_mistakes = self.coaching_agent.get_persistent_mistakes()
                
                return [
                    MistakePatternResponse(**mistake)
                    for mistake in persistent_mistakes
                ]
                
            except Exception as e:
                logger.error(f"Error getting persistent mistakes: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/advice/corner/{corner_id}", response_model=CornerAnalysisResponse)
        async def get_corner_analysis(corner_id: str):
            """Get detailed analysis for a specific corner"""
            if not self.coaching_agent:
                raise HTTPException(status_code=503, detail="Coaching agent not available")
            
            try:
                analysis = self.coaching_agent.get_corner_analysis(corner_id)
                
                if not analysis:
                    raise HTTPException(status_code=404, detail=f"No data found for corner {corner_id}")
                
                return CornerAnalysisResponse(**analysis)
                
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error getting corner analysis: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/advice/recent_mistakes", response_model=List[RecentMistakesResponse])
        async def get_recent_mistakes(window_minutes: int = 10):
            """Get recent mistakes from time window"""
            if not self.coaching_agent:
                raise HTTPException(status_code=503, detail="Coaching agent not available")
            
            try:
                recent_mistakes = self.coaching_agent.get_recent_mistakes(window_minutes)
                
                return [
                    RecentMistakesResponse(**mistake)
                    for mistake in recent_mistakes
                ]
                
            except Exception as e:
                logger.error(f"Error getting recent mistakes: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/advice/focus_areas")
        async def get_focus_areas():
            """Get recommended focus areas based on persistent mistakes"""
            if not self.coaching_agent:
                raise HTTPException(status_code=503, detail="Coaching agent not available")
            
            try:
                persistent_mistakes = self.coaching_agent.get_persistent_mistakes()
                session_summary = self.coaching_agent.get_session_summary()
                
                # Identify critical focus areas
                critical_areas = []
                high_priority_areas = []
                
                for mistake in persistent_mistakes:
                    if mistake['priority'] == 'critical':
                        critical_areas.append({
                            'corner_name': mistake['corner_name'],
                            'mistake_type': mistake['mistake_type'],
                            'frequency': mistake['frequency'],
                            'total_time_loss': mistake['total_time_loss'],
                            'description': mistake['description']
                        })
                    elif mistake['priority'] == 'high':
                        high_priority_areas.append({
                            'corner_name': mistake['corner_name'],
                            'mistake_type': mistake['mistake_type'],
                            'frequency': mistake['frequency'],
                            'total_time_loss': mistake['total_time_loss'],
                            'description': mistake['description']
                        })
                
                return {
                    'critical_focus_areas': critical_areas,
                    'high_priority_areas': high_priority_areas,
                    'session_score': session_summary['session_score'],
                    'total_time_lost': session_summary['total_time_lost'],
                    'recommendations': session_summary['recommendations']
                }
                
            except Exception as e:
                logger.error(f"Error getting focus areas: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/advice/trends")
        async def get_improvement_trends():
            """Get improvement trends and patterns"""
            if not self.coaching_agent:
                raise HTTPException(status_code=503, detail="Coaching agent not available")
            
            try:
                persistent_mistakes = self.coaching_agent.get_persistent_mistakes()
                
                # Analyze trends
                improving_areas = []
                declining_areas = []
                stable_areas = []
                
                for mistake in persistent_mistakes:
                    trend_data = {
                        'corner_name': mistake['corner_name'],
                        'mistake_type': mistake['mistake_type'],
                        'frequency': mistake['frequency'],
                        'total_time_loss': mistake['total_time_loss'],
                        'description': mistake['description']
                    }
                    
                    if mistake['severity_trend'] == 'improving':
                        improving_areas.append(trend_data)
                    elif mistake['severity_trend'] == 'declining':
                        declining_areas.append(trend_data)
                    else:
                        stable_areas.append(trend_data)
                
                return {
                    'improving_areas': improving_areas,
                    'declining_areas': declining_areas,
                    'stable_areas': stable_areas,
                    'total_patterns': len(persistent_mistakes)
                }
                
            except Exception as e:
                logger.error(f"Error getting improvement trends: {e}")
                raise HTTPException(status_code=500, detail=str(e))
    
    def set_coaching_agent(self, coaching_agent):
        """Set the coaching agent for the API"""
        self.coaching_agent = coaching_agent
        logger.info("🤖 Coaching agent connected to Session API")
    
    async def start_server(self, host: str = "0.0.0.0", port: int = 8001):
        """Start the API server"""
        config = uvicorn.Config(
            self.app,
            host=host,
            port=port,
            log_level="info"
        )
        server = uvicorn.Server(config)
        await server.serve()
    
    def get_app(self):
        """Get the FastAPI app instance"""
        return self.app

# Example usage
async def test_session_api():
    """Test the session API"""
    from hybrid_coach import HybridCoachingAgent
    from config import get_development_config
    
    # Initialize coaching agent
    config = get_development_config()
    coaching_agent = HybridCoachingAgent(config)
    
    # Initialize API
    api = SessionAPI(coaching_agent)
    
    # Start server
    await api.start_server(port=8001)

if __name__ == "__main__":
    asyncio.run(test_session_api()) 
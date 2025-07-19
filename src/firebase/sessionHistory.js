import { useState, useEffect } from 'react';
import { 
  collection, 
  addDoc, 
  query, 
  orderBy, 
  limit, 
  onSnapshot, 
  where,
  serverTimestamp,
  doc,
  updateDoc
} from 'firebase/firestore';
import { db } from './config';
import { useAuth } from './auth';

export const useSessionHistory = () => {
  const { user, isAuthenticated } = useAuth();
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [currentSessionId, setCurrentSessionId] = useState(null);

  // Listen to session history when user is authenticated
  useEffect(() => {
    if (!isAuthenticated || !user) {
      setSessions([]);
      return;
    }

    setLoading(true);
    setError(null);

    try {
      // Create query for user's sessions
      const sessionsRef = collection(db, 'sessions');
      const q = query(
        sessionsRef,
        where('userId', '==', user.uid),
        orderBy('startTime', 'desc'),
        limit(50) // Get last 50 sessions
      );

      // Real-time listener
      const unsubscribe = onSnapshot(q, 
        (snapshot) => {
          const sessionData = snapshot.docs.map(doc => ({
            id: doc.id,
            ...doc.data(),
            // Convert Firestore timestamps to Date objects
            startTime: doc.data().startTime?.toDate(),
            endTime: doc.data().endTime?.toDate()
          }));

          setSessions(sessionData);
          setLoading(false);
          console.log(`Loaded ${sessionData.length} sessions for user ${user.uid}`);
        },
        (error) => {
          console.error('Error loading sessions:', error);
          setError(error.message);
          setLoading(false);
        }
      );

      return () => unsubscribe();
    } catch (error) {
      console.error('Error setting up session listener:', error);
      setError(error.message);
      setLoading(false);
    }
  }, [isAuthenticated, user]);

  // Start a new session
  const startSession = async (sessionInfo, telemetryData) => {
    if (!isAuthenticated || !user) {
      console.warn('Cannot start session: user not authenticated');
      return null;
    }

    try {
      setError(null);

      const sessionData = {
        userId: user.uid,
        startTime: serverTimestamp(),
        track_name: sessionInfo?.track_name || 'Unknown Track',
        car_name: sessionInfo?.car_name || 'Unknown Car',
        session_type: sessionInfo?.session_type || 'Practice',
        session_active: true,
        coaching_messages: [],
        lap_times: [],
        best_lap_time: null,
        total_laps: 0,
        fuel_used: 0,
        created_at: serverTimestamp()
      };

      const docRef = await addDoc(collection(db, 'sessions'), sessionData);
      setCurrentSessionId(docRef.id);
      
      console.log('New session started:', docRef.id);
      return docRef.id;
    } catch (error) {
      console.error('Error starting session:', error);
      setError(error.message);
      throw error;
    }
  };

  // End current session
  const endSession = async (sessionStats = {}) => {
    if (!currentSessionId || !isAuthenticated) {
      console.warn('Cannot end session: no active session or user not authenticated');
      return;
    }

    try {
      setError(null);

      const sessionRef = doc(db, 'sessions', currentSessionId);
      await updateDoc(sessionRef, {
        endTime: serverTimestamp(),
        session_active: false,
        ...sessionStats // Include any final stats like total laps, best time, etc.
      });

      console.log('Session ended:', currentSessionId);
      setCurrentSessionId(null);
    } catch (error) {
      console.error('Error ending session:', error);
      setError(error.message);
      throw error;
    }
  };

  // Add coaching message to current session
  const addCoachingMessage = async (message) => {
    if (!currentSessionId || !isAuthenticated) {
      console.warn('Cannot add coaching message: no active session');
      return;
    }

    try {
      setError(null);

      const messageData = {
        id: message.id,
        message: message.message,
        category: message.category,
        priority: message.priority,
        confidence: message.confidence,
        timestamp: new Date(message.timestamp),
        improvement_potential: message.improvementPotential
      };

      const sessionRef = doc(db, 'sessions', currentSessionId);
      
      // Add message to the coaching_messages array
      // Note: This is a simple approach. For high-frequency updates, 
      // consider using a subcollection instead
      const currentSession = sessions.find(s => s.id === currentSessionId);
      const updatedMessages = [...(currentSession?.coaching_messages || []), messageData];
      
      await updateDoc(sessionRef, {
        coaching_messages: updatedMessages
      });

      console.log('Coaching message added to session:', currentSessionId);
    } catch (error) {
      console.error('Error adding coaching message:', error);
      setError(error.message);
    }
  };

  // Update session with lap time
  const addLapTime = async (lapTime, lapNumber) => {
    if (!currentSessionId || !isAuthenticated) {
      console.warn('Cannot add lap time: no active session');
      return;
    }

    try {
      setError(null);

      const sessionRef = doc(db, 'sessions', currentSessionId);
      const currentSession = sessions.find(s => s.id === currentSessionId);
      
      const newLapData = {
        lap_number: lapNumber,
        lap_time: lapTime,
        timestamp: new Date()
      };

      const updatedLapTimes = [...(currentSession?.lap_times || []), newLapData];
      const newBestTime = Math.min(
        currentSession?.best_lap_time || Infinity,
        lapTime
      );

      await updateDoc(sessionRef, {
        lap_times: updatedLapTimes,
        best_lap_time: newBestTime === Infinity ? lapTime : newBestTime,
        total_laps: lapNumber
      });

      console.log(`Lap ${lapNumber} added: ${lapTime.toFixed(3)}s`);
    } catch (error) {
      console.error('Error adding lap time:', error);
      setError(error.message);
    }
  };

  return {
    sessions,
    loading,
    error,
    currentSessionId,
    hasActiveSession: !!currentSessionId,
    startSession,
    endSession,
    addCoachingMessage,
    addLapTime
  };
};

import { initializeApp } from 'firebase/app';
import { getFirestore, enableNetwork, disableNetwork } from 'firebase/firestore';
import { getAuth, signInAnonymously } from 'firebase/auth';

// Firebase configuration - you'll need to replace this with your actual config
const firebaseConfig = {
  // Replace with your Firebase config
  apiKey: "your-api-key",
  authDomain: "your-project.firebaseapp.com",
  projectId: "your-project-id",
  storageBucket: "your-project.appspot.com",
  messagingSenderId: "123456789",
  appId: "your-app-id"
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);

// Initialize Firestore with offline persistence
export const db = getFirestore(app);

// Initialize Auth
export const auth = getAuth(app);

// Enable offline persistence (works automatically in v9+)
// Firestore will cache data locally and sync when online

// Auto sign-in anonymously for session tracking
let authInitialized = false;

export const initializeAuth = async () => {
  if (authInitialized) return;
  
  try {
    if (!auth.currentUser) {
      await signInAnonymously(auth);
      console.log('Signed in anonymously for session tracking');
    }
    authInitialized = true;
  } catch (error) {
    console.warn('Firebase auth failed, will work offline:', error);
    authInitialized = true;
  }
};

// Helper to handle online/offline states
export const setFirebaseOnline = async (online) => {
  try {
    if (online) {
      await enableNetwork(db);
    } else {
      await disableNetwork(db);
    }
  } catch (error) {
    console.warn('Failed to change Firebase network state:', error);
  }
};

export default app;

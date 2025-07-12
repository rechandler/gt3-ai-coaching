import { initializeApp } from 'firebase/app';
import { getFirestore, connectFirestoreEmulator } from 'firebase/firestore';
import { getAuth, connectAuthEmulator } from 'firebase/auth';

// Firebase configuration - you'll need to replace this with your actual config
const firebaseConfig = {
  // You'll get these values from Firebase Console when you create a project
  apiKey: process.env.REACT_APP_FIREBASE_API_KEY || "demo-api-key",
  authDomain: process.env.REACT_APP_FIREBASE_AUTH_DOMAIN || "gt3-ai-coaching.firebaseapp.com",
  projectId: process.env.REACT_APP_FIREBASE_PROJECT_ID || "gt3-ai-coaching-demo",
  storageBucket: process.env.REACT_APP_FIREBASE_STORAGE_BUCKET || "gt3-ai-coaching.appspot.com",
  messagingSenderId: process.env.REACT_APP_FIREBASE_MESSAGING_SENDER_ID || "123456789",
  appId: process.env.REACT_APP_FIREBASE_APP_ID || "1:123456789:web:abcdef"
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);

// Initialize Firebase services
export const db = getFirestore(app);
export const auth = getAuth(app);

// Development mode - connect to emulators if running locally
if (process.env.NODE_ENV === 'development') {
  try {
    // Only connect to emulators if they haven't been connected already
    if (!auth._delegate._config.emulator) {
      connectAuthEmulator(auth, "http://localhost:9099");
    }
    if (!db._delegate._databaseId.projectId.includes('localhost')) {
      connectFirestoreEmulator(db, 'localhost', 8080);
    }
  } catch (error) {
    console.log("Firebase emulators not available, using production:", error.message);
  }
}

export default app;

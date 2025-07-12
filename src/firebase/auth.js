import { useState, useEffect } from 'react';
import { 
  signInAnonymously, 
  signInWithEmailAndPassword,
  createUserWithEmailAndPassword,
  signOut,
  onAuthStateChanged,
  linkWithCredential,
  EmailAuthProvider
} from 'firebase/auth';
import { auth } from './config';

export const useAuth = () => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, (user) => {
      setUser(user);
      setLoading(false);
      console.log('Auth state changed:', user ? 'User logged in' : 'User logged out');
    });

    return () => unsubscribe();
  }, []);

  // Sign in anonymously - perfect for getting started quickly
  const signInAnonymous = async () => {
    try {
      setError(null);
      setLoading(true);
      const result = await signInAnonymously(auth);
      console.log('Anonymous sign in successful:', result.user.uid);
      return result.user;
    } catch (error) {
      console.error('Anonymous sign in failed:', error);
      setError(error.message);
      throw error;
    } finally {
      setLoading(false);
    }
  };

  // Sign in with email/password
  const signInWithEmail = async (email, password) => {
    try {
      setError(null);
      setLoading(true);
      const result = await signInWithEmailAndPassword(auth, email, password);
      console.log('Email sign in successful:', result.user.email);
      return result.user;
    } catch (error) {
      console.error('Email sign in failed:', error);
      setError(error.message);
      throw error;
    } finally {
      setLoading(false);
    }
  };

  // Create account with email/password
  const signUpWithEmail = async (email, password) => {
    try {
      setError(null);
      setLoading(true);
      const result = await createUserWithEmailAndPassword(auth, email, password);
      console.log('Email sign up successful:', result.user.email);
      return result.user;
    } catch (error) {
      console.error('Email sign up failed:', error);
      setError(error.message);
      throw error;
    } finally {
      setLoading(false);
    }
  };

  // Upgrade anonymous account to permanent account
  const upgradeAnonymousAccount = async (email, password) => {
    try {
      if (!user || !user.isAnonymous) {
        throw new Error('User is not anonymous or not logged in');
      }

      setError(null);
      setLoading(true);
      
      const credential = EmailAuthProvider.credential(email, password);
      const result = await linkWithCredential(user, credential);
      
      console.log('Anonymous account upgraded successfully:', result.user.email);
      return result.user;
    } catch (error) {
      console.error('Account upgrade failed:', error);
      setError(error.message);
      throw error;
    } finally {
      setLoading(false);
    }
  };

  // Sign out
  const logout = async () => {
    try {
      setError(null);
      await signOut(auth);
      console.log('User signed out successfully');
    } catch (error) {
      console.error('Sign out failed:', error);
      setError(error.message);
      throw error;
    }
  };

  return {
    user,
    loading,
    error,
    isAnonymous: user?.isAnonymous || false,
    isAuthenticated: !!user,
    signInAnonymous,
    signInWithEmail,
    signUpWithEmail,
    upgradeAnonymousAccount,
    logout
  };
};

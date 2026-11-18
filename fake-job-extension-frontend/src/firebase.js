
import { initializeApp } from "firebase/app";
import {
  initializeAuth,
  indexedDBLocalPersistence,
  browserLocalPersistence
} from "firebase/auth";  

// Your web app's Firebase configuration
const firebaseConfig = {
  apiKey: "AIzaSyDzjYthnjL8mczpv2e_RO-VG0GpMY77QFc",
  authDomain: "hirely-b7650.firebaseapp.com",
  projectId: "hirely-b7650",
  storageBucket: "hirely-b7650.firebasestorage.app",
  messagingSenderId: "766000017389",
  appId: "1:766000017389:web:6e7b930b58d6902add81e4"
};

const app = initializeApp(firebaseConfig);

// Initialize Firebase Auth with persistent storage
export const auth = initializeAuth(app, {
  persistence: [
    indexedDBLocalPersistence,
    browserLocalPersistence
  ]
});
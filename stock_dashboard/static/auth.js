import { initializeApp } from "https://www.gstatic.com/firebasejs/10.8.0/firebase-app.js";
import { getAuth, signInWithPopup, GoogleAuthProvider, signOut, onAuthStateChanged } from "https://www.gstatic.com/firebasejs/10.8.0/firebase-auth.js";

const firebaseConfig = {
  apiKey: "AIzaSyCn9gbe1KpADL8SK4HSkRTDlA_WwlXvL0s",
  authDomain: "stockml-9a81e.firebaseapp.com",
  projectId: "stockml-9a81e",
  storageBucket: "stockml-9a81e.firebasestorage.app",
  messagingSenderId: "671631880928",
  appId: "1:671631880928:web:75a13d85ecc2e03193d685",
  measurementId: "G-G62H0QB9ZQ"
};

const app = initializeApp(firebaseConfig);
const auth = getAuth(app);
const provider = new GoogleAuthProvider();

provider.setCustomParameters({
  prompt: 'select_account'
});


export { auth, provider, signInWithPopup, signOut, onAuthStateChanged };

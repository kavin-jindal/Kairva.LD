
// Import the functions you need from the SDKs you need
import { initializeApp } from "https://www.gstatic.com/firebasejs/10.7.1/firebase-app.js";
import { getAuth, GoogleAuthProvider, signInWithPopup, signInWithEmailAndPassword, createUserWithEmailAndPassword, onAuthStateChanged, signOut } from "https://www.gstatic.com/firebasejs/10.7.1/firebase-auth.js";

// Expose logout to window
window.logout = async () => {
    try {
        await signOut(auth);
        window.location.href = "/logout";
    } catch (error) {
        console.error("Error signing out:", error);
        // Fallback to backend logout anyway
        window.location.href = "/logout";
    }
};

// Firebase configuration is injected by the backend into window.firebaseConfig
const firebaseConfig = window.firebaseConfig;

// Initialize Firebase
const app = initializeApp(firebaseConfig);
const auth = getAuth(app);
const googleProvider = new GoogleAuthProvider();


// Helper to show/hide errors onscreen
function showErrorMessage(message) {
    const errorDiv = document.getElementById('auth-error');
    if (errorDiv) {
        errorDiv.textContent = message;
        errorDiv.style.display = 'block';
    } else {
        alert(message);
    }
}

function clearError() {
    const errorDiv = document.getElementById('auth-error');
    if (errorDiv) errorDiv.style.display = 'none';
}

// Google Sign-In Function
window.signInWithGoogle = async () => {
    try {
        clearError();
        const role = document.getElementById('roleSelect')?.value || document.querySelector('select')?.value || 'student';
        const result = await signInWithPopup(auth, googleProvider);
        const user = result.user;
        const idToken = await user.getIdToken();

        // Send token and role to backend
        await sendTokenToBackend(idToken, role);
    } catch (error) {
        console.error("Error signing in with Google:", error);
        showErrorMessage("An error occurred. Please try again.");
    }
};

// Email/Password Sign-Up
window.signUpWithEmail = async (email, password) => {
    try {
        clearError();
        const role = document.getElementById('roleSelect')?.value || document.querySelector('select')?.value || 'student';
        const userCredential = await createUserWithEmailAndPassword(auth, email, password);
        const user = userCredential.user;
        const idToken = await user.getIdToken();
        await sendTokenToBackend(idToken, role);
    } catch (error) {
        console.error("Error signing up:", error);
        showErrorMessage("An error occurred. Please try again.");
    }
};

// Email/Password Login
window.loginWithEmail = async (email, password) => {
    try {
        clearError();
        const role = document.getElementById('roleSelect')?.value || document.querySelector('select')?.value || null;
        const userCredential = await signInWithEmailAndPassword(auth, email, password);
        const user = userCredential.user;
        const idToken = await user.getIdToken();
        await sendTokenToBackend(idToken, role);
    } catch (error) {
        console.error("Error logging in:", error);
        showErrorMessage("An error occurred. Please try again.");
    }
};

async function sendTokenToBackend(idToken, role = null) {
    try {
        console.log("Sending token to backend... Role:", role);
        const nameInput = document.getElementById('fullname');
        const name = nameInput ? nameInput.value : null;

        const body = { token: idToken };
        if (role) body.role = role;
        if (name) body.name = name;

        const response = await fetch('/verify-token', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(body),
        });

        console.log("Backend response status:", response.status);
        const data = await response.json();
        if (data.success) {
            window.location.href = data.redirect_url;
        } else {
            console.error("Backend verification failed:", data.error);
            showErrorMessage("An error occurred. Please try again.");
        }
    } catch (error) {
        console.error("Error sending token to backend:", error);
        showErrorMessage("An error occurred. Please try again.");
    }
}

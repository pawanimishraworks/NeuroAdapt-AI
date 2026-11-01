// NeuroAdapt AI authentication - connects login.html to FastAPI.
const API_BASE = "http://127.0.0.1:8000";

let currentMode = "login";

function showLogin() {
    currentMode = "login";
    document.getElementById("nameGroup").hidden = true;
    document.getElementById("formTitle").textContent = "Welcome Back!";
    document.getElementById("formSubtitle").textContent =
        "Sign in to continue your learning journey.";
    document.getElementById("submitBtn").textContent = "Login";
    document.getElementById("loginTab").classList.add("active");
    document.getElementById("signupTab").classList.remove("active");
    document.getElementById("name").required = false;
    document.getElementById("password").minLength = 1;
    document.getElementById("authMessage").textContent = "";
}

function showSignup() {
    currentMode = "signup";
    document.getElementById("nameGroup").hidden = false;
    document.getElementById("formTitle").textContent = "Create Account";
    document.getElementById("formSubtitle").textContent =
        "Join NeuroAdapt AI and start learning smarter.";
    document.getElementById("submitBtn").textContent = "Create Account";
    document.getElementById("signupTab").classList.add("active");
    document.getElementById("loginTab").classList.remove("active");
    document.getElementById("name").required = true;
    document.getElementById("password").minLength = 8;
    document.getElementById("authMessage").textContent =
        "Use a password with at least 8 characters.";
}

function togglePassword() {
    const password = document.getElementById("password");
    const button = document.querySelector(".show-password");
    const showing = password.type === "password";
    password.type = showing ? "text" : "password";
    button.textContent = showing ? "Hide" : "Show";
}

document.getElementById("authForm").addEventListener("submit", async (event) => {
    event.preventDefault();

    const message = document.getElementById("authMessage");
    const submit = document.getElementById("submitBtn");
    const email = document.getElementById("email").value.trim().toLowerCase();
    const password = document.getElementById("password").value;
    const name = document.getElementById("name").value.trim();

    if (currentMode === "signup" && password.length < 8) {
        message.textContent = "Password must contain at least 8 characters.";
        return;
    }

    const endpoint = currentMode === "signup"
        ? "/api/auth/register"
        : "/api/auth/login";

    const payload = currentMode === "signup"
        ? { name, email, password }
        : { email, password };

    submit.disabled = true;
    submit.textContent = currentMode === "signup" ? "Creating account..." : "Signing in...";
    message.textContent = "Connecting to NeuroAdapt AI...";

    try {
        const response = await fetch(`${API_BASE}${endpoint}`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || "Authentication failed. Please try again.");
        }

        sessionStorage.setItem("neuroadapt_token", data.token);
        sessionStorage.setItem("neuroadapt_user", JSON.stringify(data.user));

        message.textContent = currentMode === "signup"
            ? "Account created successfully! Redirecting..."
            : "Login successful! Redirecting...";

        window.location.href = "dashboard.html";
    } catch (error) {
        message.textContent = error.message.includes("Failed to fetch")
            ? "Cannot connect to the backend. Make sure FastAPI is running at http://127.0.0.1:8000."
            : error.message;
    } finally {
        submit.disabled = false;
        submit.textContent = currentMode === "signup" ? "Create Account" : "Login";
    }
});

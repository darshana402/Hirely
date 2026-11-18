
import { useState, useEffect } from "react";

import {
  signInWithEmailAndPassword,
  createUserWithEmailAndPassword,
  updateProfile,
  signOut,
  onAuthStateChanged
} from "firebase/auth";

import { auth } from "./firebase";
import "./App.css";

import logofinal from ".././public/logofinal.jpeg";

// Online Hirely Backend URL
const API_BASE_URL = "https://hirely-api-darshana402.onrender.com";


function App() {

  const [page, setPage] = useState("login");

  const [analyzing, setAnalyzing] = useState(false);

  const [jobContent, setJobContent] = useState(null);

  const [analysisResult, setAnalysisResult] = useState(null);

  // ---------------- AUTH STATE ----------------

  const [loading, setLoading] = useState(true);

  // ---------------- SIGNUP ----------------

  const [signupData, setSignupData] = useState({
    name: "",
    email: "",
    password: ""
  });

  // ---------------- LOGIN ----------------

  const [loginData, setLoginData] = useState({
    email: "",
    password: ""
  });

  // ---------------- ERROR ----------------

  const [error, setError] = useState("");

  // =========================================================
  // CHECK FIREBASE AUTH STATE
  // =========================================================

  useEffect(() => {

    const unsubscribe = onAuthStateChanged(
      auth,
      (currentUser) => {

        if (currentUser) {
          setPage("dashboard");
        } else {
          setPage("login");
        }

        setLoading(false);

      }
    );

    return () => unsubscribe();

  }, []);

  // =========================================================
  // SIGNUP
  // =========================================================

  const handleSignup = async (e) => {

    e.preventDefault();

    setError("");

    try {

      // 1. Create Firebase account

      const userCredential =
        await createUserWithEmailAndPassword(
          auth,
          signupData.email,
          signupData.password
        );

      const firebaseUser = userCredential.user;

      // 2. Save user's name in Firebase profile

      await updateProfile(firebaseUser, {
        displayName: signupData.name
      });

      // 3. SAVE USER IN FASTAPI + SQLITE

      try {

        const response = await fetch(
          `${API_BASE_URL}/users`,
          {
            method: "POST",

            headers: {
              "Content-Type": "application/json"
            },

            body: JSON.stringify({

              firebase_uid: firebaseUser.uid,

              name: signupData.name,

              email: firebaseUser.email

            })
          }
        );

        if (!response.ok) {

          const errorData =
            await response.json();

          throw new Error(
            errorData.detail ||
            "Unable to save user in database."
          );

        }

        const databaseUser =
          await response.json();

        console.log(
          "User saved in SQLite:",
          databaseUser
        );

      } catch (databaseError) {

        console.error(
          "Database storage error:",
          databaseError
        );

        setError(
          "Account created, but user could not be saved in database."
        );

        return;

      }

      // 4. Account created successfully

      alert("Account created successfully!");

      await signOut(auth);

      // 5. Clear signup form

      setSignupData({
        name: "",
        email: "",
        password: ""
      });

      // 6. Go back to login

      setPage("login");

    } catch (error) {

      console.error(
        "Signup error:",
        error
      );

      if (
        error.code ===
        "auth/email-already-in-use"
      ) {

        setError(
          "An account with this email already exists."
        );

      } else if (
        error.code ===
        "auth/weak-password"
      ) {

        setError(
          "Password should be at least 6 characters."
        );

      } else if (
        error.code ===
        "auth/invalid-email"
      ) {

        setError(
          "Please enter a valid email address."
        );

      } else {

        setError(
          "Unable to create account. Please try again."
        );

      }

    }

  };

  // =========================================================
  // LOGIN
  // =========================================================

  const handleLogin = async (e) => {

    e.preventDefault();

    setError("");

    try {

      await signInWithEmailAndPassword(
        auth,
        loginData.email,
        loginData.password
      );

      setLoginData({
        email: "",
        password: ""
      });

    } catch (error) {

      console.error(
        "Login error:",
        error
      );

      if (
        error.code === "auth/invalid-credential" ||
        error.code === "auth/wrong-password" ||
        error.code === "auth/user-not-found"
      ) {

        setError(
          "Invalid email or password."
        );

      } else if (
        error.code === "auth/invalid-email"
      ) {

        setError(
          "Please enter a valid email address."
        );

      } else {

        setError(
          "Unable to login. Please try again."
        );

      }

    }

  };

  // =========================================================
  // ANALYZE JOB
  // =========================================================


const analyzeJob = async () => {
  try {
    setAnalyzing(true);
    setJobContent(null);
    setAnalysisResult(null);

    // Check whether the user is using the Chrome extension
    if (typeof chrome !== "undefined" && chrome.tabs?.query) {
      const tabs = await chrome.tabs.query({
        active: true,
        currentWindow: true
      });

      const currentTab = tabs[0];

      if (!currentTab?.id) {
        throw new Error("Unable to access the current tab.");
      }

      chrome.tabs.sendMessage(
        currentTab.id,
        { type: "GET_JOB_CONTENT" },
        async (response) => {
          if (chrome.runtime.lastError) {
            console.error(chrome.runtime.lastError);
            alert("Unable to read this webpage. Try refreshing the job page.");
            setAnalyzing(false);
            return;
          }

          if (!response?.success) {
            alert("Could not extract job information.");
            setAnalyzing(false);
            return;
          }

          await sendJobForAnalysis(response.data);
        }
      );

      return;
    }

    // Normal deployed website: ask user to paste job details
    const jobText = prompt(
      "Paste the complete job description here:"
    );

    if (!jobText || !jobText.trim()) {
      setAnalyzing(false);
      return;
    }

    await sendJobForAnalysis({
      title: "Job Posting",
      url: "",
      text: jobText.trim()
    });

  } catch (error) {
    console.error("Analysis error:", error);
    alert(error.message || "Something went wrong.");
    setAnalyzing(false);
  }
};

// Send job information to the online backend
const sendJobForAnalysis = async (jobData) => {
  try {
    setJobContent(jobData);

    const apiResponse = await fetch(
      `${API_BASE_URL}/analyze`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          title: jobData.title || "Job Posting",
          url: jobData.url || "",
          text: jobData.text || ""
        })
      }
    );

    if (!apiResponse.ok) {
      const errorData = await apiResponse.text();
      throw new Error(errorData || "Backend analysis failed.");
    }

    const result = await apiResponse.json();

    console.log("FastAPI Result:", result);
    setAnalysisResult(result);

  } catch (error) {
    console.error("Backend analysis error:", error);
    alert(error.message || "Unable to analyze this job.");
  } finally {
    setAnalyzing(false);
  }
};


  // =========================================================
  // LOGOUT
  // =========================================================

  const handleLogout = async () => {

    try {

      await signOut(auth);

      setJobContent(null);

      setAnalysisResult(null);

    } catch (error) {

      console.error(
        "Logout error:",
        error
      );

    }

  };

  // =========================================================
  // LOADING
  // =========================================================

  if (loading) {

    return (

      <div className="app-container">

        <div className="auth-card">

          <p>
            Loading...
          </p>

        </div>

      </div>

    );

  }

  if (analysisResult) {
    console.log(
      JSON.stringify(analysisResult.suspicious_factors)
    );
  }

  // =========================================================
  // LOGIN PAGE
  // =========================================================

  if (page === "login") {

    return (

      <div className="app-container">

        <div className="auth-card">

          <img
            src={logofinal}
            alt="Hirely Logo"
            className="auth-logo"
          />

          <h1>
            Welcome to Hirely
          </h1>

          <p className="subtitle">
            AI-powered fake job detection
          </p>

          {error && (

            <p className="error-message">
              {error}
            </p>

          )}

          <form onSubmit={handleLogin}>

            <input
              type="email"
              placeholder="Email address"
              value={loginData.email}
              onChange={(e) =>
                setLoginData({
                  ...loginData,
                  email: e.target.value
                })
              }
              required
            />

            <input
              type="password"
              placeholder="Password"
              value={loginData.password}
              onChange={(e) =>
                setLoginData({
                  ...loginData,
                  password: e.target.value
                })
              }
              required
            />

            <button
              type="submit"
              className="primary-btn"
            >
              Login
            </button>

          </form>

          <p className="switch-text">

            Don't have an account?

            <span
              onClick={() => {

                setError("");

                setPage("signup");

              }}
            >
              {" "}
              Create Account
            </span>

          </p>

        </div>

      </div>

    );

  }

  // =========================================================
  // SIGNUP PAGE
  // =========================================================

  if (page === "signup") {

    return (

      <div className="app-container">

        <div className="auth-card">

          <img
            src={logofinal}
            alt="Hirely Logo"
            className="auth-logo"
          />

          <h1>
            Create Account
          </h1>

          <p className="subtitle">
            Start detecting fake jobs
          </p>

          {error && (

            <p className="error-message">
              {error}
            </p>

          )}

          <form onSubmit={handleSignup}>

            <input
              type="text"
              placeholder="Full name"
              value={signupData.name}
              onChange={(e) =>
                setSignupData({
                  ...signupData,
                  name: e.target.value
                })
              }
              required
            />

            <input
              type="email"
              placeholder="Email address"
              value={signupData.email}
              onChange={(e) =>
                setSignupData({
                  ...signupData,
                  email: e.target.value
                })
              }
              required
            />

            <input
              type="password"
              placeholder="Create password"
              value={signupData.password}
              onChange={(e) =>
                setSignupData({
                  ...signupData,
                  password: e.target.value
                })
              }
              required
            />

            <button
              type="submit"
              className="primary-btn"
            >
              Create Account
            </button>

          </form>

          <p className="switch-text">

            Already have an account?

            <span
              onClick={() => {

                setError("");

                setPage("login");

              }}
            >
              {" "}
              Login
            </span>

          </p>

        </div>

      </div>

    );

  }

  // =========================================================
  // DASHBOARD
  // =========================================================

  return (

    <div className="dashboard">

      {/* HEADER */}

      <header className="header">

        <div className="brand">

          <img
            src={logofinal}
            alt="Hirely"
            className="header-logo"
          />

        </div>

        <button
          className="logout-btn"
          onClick={handleLogout}
        >
          Logout
        </button>

      </header>

      {/* MAIN CONTENT */}

      <main className="main-content">

        <div className="welcome-section">

          <h1>
            Job Detection
          </h1>

          <p>
            Check whether a job posting is legitimate or potentially fraudulent.
          </p>

        </div>

        {/* JOB DETECTION CARD */}

        <div className="detection-card">

          <div className="detection-icon">
            🔍
          </div>

          <h2>
            Analyze Current Job
          </h2>

          <p>
            Open a job posting in your browser and click the button below.
          </p>

          <button
            className="analyze-btn"
            onClick={analyzeJob}
            disabled={analyzing}
          >

            {analyzing ? (

              <>
                <span className="button-spinner"></span>
                Analyzing...
              </>

            ) : (

              "Analyze Job"

            )}

          </button>

        </div>

        {/* AI RESULT */}

        <div className="result-card">

          <div className="result-header">

            <h2>
              AI Detection Result
            </h2>

            {analyzing ? (

              <span className="analyzing-status">
                Analyzing...
              </span>

            ) : analysisResult ? (

              <span className="completed-status">
                Analysis Complete
              </span>

            ) : (

              <span className="pending">
                Waiting for analysis
              </span>

            )}

          </div>

          {/* LOADING */}

          {analyzing ? (

            <div className="result-loading">

              <div className="loading-ring"></div>

              <h3>
                Analyzing Job...
              </h3>

              <p>
                Extracting job information and checking for potential fraud.
              </p>

            </div>

          ) : analysisResult ? (

            /* RESULT */

            <div className="result-content">

              <div className="result-main">

                <div className="shield">
                  🛡️
                </div>

                <h3>
                  {analysisResult.final_prediction || analysisResult.prediction}
                </h3>

                {(analysisResult.extracted_title || analysisResult.extracted_company) ? (

                  <p className="job-meta">

                    {analysisResult.extracted_title || "Unknown title"}

                    {analysisResult.extracted_title && analysisResult.extracted_company && " at "}

                    {analysisResult.extracted_company}

                  </p>

                ) : (

                  <p className="job-meta">
                    ⚠️ Job title/company not detected — please verify this matches the posting you intended to analyze.
                  </p>

                )}

              </div>

              {/* FINAL RISK ANALYSIS */}

              <div className="model-result">

                <div className="model-row">
                  <span>Final Risk Score</span>
                  <span>{analysisResult.risk_score}/100</span>
                </div>

                <div className="model-row">
                  <span>Risk Level</span>
                  <span>{analysisResult.risk_level}</span>
                </div>

                <div className="model-row">
                  <span>Final Verdict</span>
                  <span>{analysisResult.final_prediction || analysisResult.prediction}</span>
                </div>

              </div>

              {/* WHY THIS PREDICTION */}

              <div className="suspicious-section">

                <h4>
                  Why This Prediction
                </h4>

                {analysisResult.top_contributing_words &&
                analysisResult.top_contributing_words.length > 0 ? (

                  <div className="factor">

                    <strong>
                      Words the model itself weighted most heavily toward 'Fraudulent'
                    </strong>

                    {(() => {

                      const words = analysisResult.top_contributing_words;

                      const maxWeight = words[0].weight;

                      return words.map((item, index) => {

                        const strength = maxWeight
                          ? Math.round((item.weight / maxWeight) * 100)
                          : 0;

                        return (

                          <p key={index}>
                            "{item.word}" — {strength}% relative strength
                          </p>

                        );

                      });

                    })()}

                  </div>

                ) : (

                  <div className="factor">
                    <p>No notable risk indicators found in this posting.</p>
                  </div>

                )}

              </div>

            </div>

          ) : (

            /* NO RESULT */

            <div className="result-placeholder">

              <div className="shield">
                🛡️
              </div>

              <h3>
                No result yet
              </h3>

              <p>
                Analyze a job posting to see its fraud risk score and AI prediction.
              </p>

            </div>

          )}

        </div>

      </main>

    </div>

  );

}

export default App;

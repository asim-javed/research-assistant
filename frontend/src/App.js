
import React, { useEffect, useState } from "react";
import "./App.css";

function App() {
  const [user, setUser] = useState(null);
  const [currentView, setCurrentView] = useState("login");
  const [referenceSets, setReferenceSets] = useState([]);
  const [inquiries, setInquiries] = useState([]);
  const [message, setMessage] = useState("");

  useEffect(() => {
    // Check if user is logged in
    const savedUser = localStorage.getItem("user");
    if (savedUser) {
      setUser(JSON.parse(savedUser));
      setCurrentView("dashboard");
      loadUserData();
    }
    
    // Test API connection
    fetch("/api/hello")
      .then(res => res.json())
      .then(data => console.log("API connected:", data.message))
      .catch(err => console.error("API connection failed:", err));
  }, []);

  const loadUserData = async () => {
    try {
      const [refSetsRes, inquiriesRes] = await Promise.all([
        fetch("/api/reference-sets"),
        fetch("/api/inquiries")
      ]);
      
      const refSets = await refSetsRes.json();
      const inquiriesData = await inquiriesRes.json();
      
      setReferenceSets(refSets.reference_sets);
      setInquiries(inquiriesData.inquiries);
    } catch (error) {
      console.error("Error loading user data:", error);
    }
  };

  const handleLogin = async (email, password) => {
    try {
      const response = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password })
      });
      
      const data = await response.json();
      if (data.success) {
        setUser(data.user);
        localStorage.setItem("user", JSON.stringify(data.user));
        setCurrentView("dashboard");
        loadUserData();
      } else {
        setMessage("Login failed: " + data.error);
      }
    } catch (error) {
      setMessage("Login error: " + error.message);
    }
  };

  const handleSignup = async (email, password) => {
    try {
      const response = await fetch("/api/auth/signup", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password })
      });
      
      const data = await response.json();
      if (data.success) {
        setMessage("Account created! Please log in.");
        setCurrentView("login");
      } else {
        setMessage("Signup failed: " + data.error);
      }
    } catch (error) {
      setMessage("Signup error: " + error.message);
    }
  };

  const logout = () => {
    setUser(null);
    localStorage.removeItem("user");
    setCurrentView("login");
    setReferenceSets([]);
    setInquiries([]);
  };

  if (currentView === "login") {
    return <LoginForm onLogin={handleLogin} onSignup={handleSignup} message={message} />;
  }

  return (
    <div className="app">
      <header className="app-header">
        <h1>Research Assistant</h1>
        <div className="user-info">
          <span>Welcome, {user?.email}</span>
          <button onClick={logout} className="logout-btn">Logout</button>
        </div>
      </header>
      
      <nav className="nav-tabs">
        <button 
          className={currentView === "dashboard" ? "active" : ""}
          onClick={() => setCurrentView("dashboard")}
        >
          Dashboard
        </button>
        <button 
          className={currentView === "reference-sets" ? "active" : ""}
          onClick={() => setCurrentView("reference-sets")}
        >
          Reference Sets
        </button>
        <button 
          className={currentView === "inquiries" ? "active" : ""}
          onClick={() => setCurrentView("inquiries")}
        >
          Lines of Inquiry
        </button>
      </nav>

      <main className="main-content">
        {currentView === "dashboard" && <Dashboard referenceSets={referenceSets} inquiries={inquiries} />}
        {currentView === "reference-sets" && <ReferenceSets referenceSets={referenceSets} />}
        {currentView === "inquiries" && <Inquiries inquiries={inquiries} referenceSets={referenceSets} />}
      </main>
    </div>
  );
}

function LoginForm({ onLogin, onSignup, message }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isSignup, setIsSignup] = useState(false);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (isSignup) {
      onSignup(email, password);
    } else {
      onLogin(email, password);
    }
  };

  return (
    <div className="login-container">
      <h1>Research Assistant</h1>
      <form onSubmit={handleSubmit} className="login-form">
        <input
          type="email"
          placeholder="Email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
        />
        <input
          type="password"
          placeholder="Password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
        />
        <button type="submit">
          {isSignup ? "Sign Up" : "Log In"}
        </button>
        <button
          type="button"
          onClick={() => setIsSignup(!isSignup)}
          className="toggle-btn"
        >
          {isSignup ? "Already have an account? Log In" : "Need an account? Sign Up"}
        </button>
      </form>
      {message && <div className="message">{message}</div>}
    </div>
  );
}

function Dashboard({ referenceSets, inquiries }) {
  return (
    <div className="dashboard">
      <h2>Dashboard</h2>
      <div className="stats">
        <div className="stat-card">
          <h3>Reference Sets</h3>
          <p>{referenceSets.length}</p>
        </div>
        <div className="stat-card">
          <h3>Lines of Inquiry</h3>
          <p>{inquiries.length}</p>
        </div>
      </div>
      <div className="quick-actions">
        <h3>Quick Actions</h3>
        <button>Create New Reference Set</button>
        <button>Start New Inquiry</button>
      </div>
    </div>
  );
}

function ReferenceSets({ referenceSets }) {
  return (
    <div className="reference-sets">
      <h2>Reference Sets</h2>
      <button className="create-btn">Create New Reference Set</button>
      {referenceSets.length === 0 ? (
        <p>No reference sets yet. Create one to get started!</p>
      ) : (
        <div className="reference-sets-list">
          {referenceSets.map((set, index) => (
            <div key={index} className="reference-set-card">
              <h3>{set.name}</h3>
              <p>{set.description}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function Inquiries({ inquiries, referenceSets }) {
  return (
    <div className="inquiries">
      <h2>Lines of Inquiry</h2>
      <button className="create-btn">Start New Inquiry</button>
      {inquiries.length === 0 ? (
        <p>No inquiries yet. Start your first line of inquiry!</p>
      ) : (
        <div className="inquiries-list">
          {inquiries.map((inquiry, index) => (
            <div key={index} className="inquiry-card">
              <h3>{inquiry.title}</h3>
              <p>{inquiry.description}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default App;

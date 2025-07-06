import React, { useEffect, useState } from "react";
import "./App.css";

function App() {
  const [user, setUser] = useState(null);
  const [currentView, setCurrentView] = useState("login");
  const [referenceSets, setReferenceSets] = useState([]);
  const [inquiries, setInquiries] = useState([]);
  const [message, setMessage] = useState("");
  const [showCreateRefSetModal, setShowCreateRefSetModal] = useState(false);
  const [showCreateInquiryModal, setShowCreateInquiryModal] = useState(false);
  const [activeInquiry, setActiveInquiry] = useState(null);

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

  const createReferenceSet = () => {
    setShowCreateRefSetModal(true);
  };

  const startInquiry = () => {
    setShowCreateInquiryModal(true);
  };

  const handleCreateReferenceSet = async (domain, description) => {
    try {
      const response = await fetch("/api/reference-sets", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ domain, description })
      });

      const data = await response.json();
      if (data.success) {
        // Reload data to get the new reference set
        loadUserData();
        setShowCreateRefSetModal(false);
        setCurrentView("reference-sets");
      } else {
        setMessage("Failed to create reference set: " + data.error);
      }
    } catch (error) {
      setMessage("Error creating reference set: " + error.message);
    }
  };

  const handleCreateInquiry = async (title, description, selectedReferenceSets) => {
    try {
      const response = await fetch("/api/inquiries", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ 
          title, 
          description, 
          reference_sets: selectedReferenceSets 
        })
      });

      const data = await response.json();
      if (data.success) {
        // Open the new inquiry directly
        const newInquiry = {
          id: data.inquiry_id,
          title,
          description,
          reference_sets: selectedReferenceSets,
          messages: []
        };
        setActiveInquiry(newInquiry);
        setShowCreateInquiryModal(false);
        setCurrentView("chat");
        loadUserData();
      } else {
        setMessage("Failed to create inquiry: " + data.error);
      }
    } catch (error) {
      setMessage("Error creating inquiry: " + error.message);
    }
  };

  const openInquiry = (inquiry) => {
    setActiveInquiry(inquiry);
    setCurrentView("chat");
  };

  const closeInquiry = () => {
    setActiveInquiry(null);
    setCurrentView("inquiries");
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
        {currentView === "dashboard" && <Dashboard referenceSets={referenceSets} inquiries={inquiries} onCreateReferenceSet={createReferenceSet} onStartInquiry={startInquiry} />}
        {currentView === "reference-sets" && <ReferenceSets referenceSets={referenceSets} onCreateReferenceSet={createReferenceSet} />}
        {currentView === "inquiries" && <Inquiries inquiries={inquiries} referenceSets={referenceSets} onStartInquiry={startInquiry} onOpenInquiry={openInquiry} />}
        {currentView === "chat" && activeInquiry && <InquiryChat inquiry={activeInquiry} onClose={closeInquiry} />}
      </main>

      {showCreateRefSetModal && (
        <CreateReferenceSetModal 
          onClose={() => setShowCreateRefSetModal(false)}
          onSubmit={handleCreateReferenceSet}
        />
      )}

      {showCreateInquiryModal && (
        <CreateInquiryModal 
          onClose={() => setShowCreateInquiryModal(false)}
          onSubmit={handleCreateInquiry}
          referenceSets={referenceSets}
        />
      )}
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

function Dashboard({ referenceSets, inquiries, onCreateReferenceSet, onStartInquiry }) {
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
        <button onClick={onCreateReferenceSet}>Create New Reference Set</button>
        <button onClick={onStartInquiry}>Start New Inquiry</button>
      </div>
    </div>
  );
}

function ReferenceSets({ referenceSets, onCreateReferenceSet }) {
  const [selectedRefSet, setSelectedRefSet] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [uploadMessage, setUploadMessage] = useState("");

  const handleFileUpload = async (event, refSet) => {
    const file = event.target.files[0];
    if (!file) return;

    setUploading(true);
    setUploadMessage("");

    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('domain', refSet.domain);

      const response = await fetch(`/api/reference-sets/${refSet.id}/upload`, {
        method: 'POST',
        body: formData
      });

      const data = await response.json();

      if (data.success) {
        setUploadMessage(`Successfully processed ${data.stats.filename}: ${data.stats.chunks} chunks across ${data.stats.pages} pages`);
      } else {
        setUploadMessage(`Upload failed: ${data.error}`);
      }
    } catch (error) {
      setUploadMessage(`Upload error: ${error.message}`);
    } finally {
      setUploading(false);
      // Clear the file input
      event.target.value = '';
    }
  };

  return (
    <div className="reference-sets">
      <h2>Reference Sets (Knowledge Domains)</h2>
      <button className="create-btn" onClick={onCreateReferenceSet}>Create New Reference Set</button>

      {uploadMessage && (
        <div className={`upload-message ${uploadMessage.includes('Successfully') ? 'success' : 'error'}`}>
          {uploadMessage}
        </div>
      )}

      {referenceSets.length === 0 ? (
        <p>No reference sets yet. Create one to get started!</p>
      ) : (
        <div className="reference-sets-list">
          {referenceSets.map((set, index) => (
            <div key={index} className="reference-set-card">
              <h3>{set.domain}</h3>
              <p>{set.description}</p>
              <div className="reference-set-stats">
                <span>Files: {set.file_count || 0}</span>
              </div>
              <div className="reference-set-actions">
                <input
                  type="file"
                  id={`file-upload-${set.id}`}
                  style={{ display: 'none' }}
                  onChange={(e) => handleFileUpload(e, set)}
                  accept=".pdf,.docx,.doc,.txt,.md,.pptx,.ppt,.xlsx,.xls,.json,.jsonl"
                  disabled={uploading}
                />
                <button 
                  onClick={() => document.getElementById(`file-upload-${set.id}`).click()}
                  disabled={uploading}
                  className="upload-btn"
                >
                  {uploading ? 'Processing...' : 'Upload Document'}
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function Inquiries({ inquiries, referenceSets, onStartInquiry, onOpenInquiry }) {
  return (
    <div className="inquiries">
      <h2>Lines of Inquiry</h2>
      <button className="create-btn" onClick={onStartInquiry}>Start New Inquiry</button>
      {inquiries.length === 0 ? (
        <p>No inquiries yet. Start your first line of inquiry!</p>
      ) : (
        <div className="inquiries-list">
          {inquiries.map((inquiry, index) => (
            <div key={index} className="inquiry-card" onClick={() => onOpenInquiry(inquiry)}>
              <h3>{inquiry.title}</h3>
              <p>{inquiry.description}</p>
              <div className="inquiry-actions">
                <button onClick={(e) => { e.stopPropagation(); onOpenInquiry(inquiry); }}>
                  Open Chat
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function CreateReferenceSetModal({ onClose, onSubmit }) {
  const [domain, setDomain] = useState("");
  const [description, setDescription] = useState("");

  const handleSubmit = (e) => {
    e.preventDefault();
    if (domain.trim()) {
      onSubmit(domain.trim(), description.trim());
    }
  };

  return (
    <div className="modal-overlay">
      <div className="modal">
        <h3>Create New Reference Set</h3>
        <form onSubmit={handleSubmit}>
          <input
            type="text"
            placeholder="Knowledge Domain (e.g., Machine Learning, Medicine, History)"
            value={domain}
            onChange={(e) => setDomain(e.target.value)}
            required
          />
          <textarea
            placeholder="Description (optional)"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows="3"
          />
          <div className="modal-buttons">
            <button type="button" onClick={onClose}>Cancel</button>
            <button type="submit">Create</button>
          </div>
        </form>
      </div>
    </div>
  );
}

function CreateInquiryModal({ onClose, onSubmit, referenceSets }) {
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [selectedReferenceSets, setSelectedReferenceSets] = useState([]);

  const handleSubmit = (e) => {
    e.preventDefault();
    console.log("Form submitted with:", { title, selectedReferenceSets });
    if (title.trim() && selectedReferenceSets.length > 0) {
      onSubmit(title.trim(), description.trim(), selectedReferenceSets);
    }
  };

  const toggleReferenceSet = (refSetId) => {
    console.log("Toggling reference set:", refSetId);
    setSelectedReferenceSets(prev => {
      const newSelection = prev.includes(refSetId) 
        ? prev.filter(id => id !== refSetId)
        : [...prev, refSetId];
      console.log("New selection:", newSelection);
      return newSelection;
    });
  };

  return (
    <div className="modal-overlay">
      <div className="modal">
        <h3>Start New Inquiry</h3>
        <form onSubmit={handleSubmit}>
          <input
            type="text"
            placeholder="Inquiry Title"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            required
          />
          <textarea
            placeholder="Description (optional)"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows="3"
          />

          <div className="reference-sets-selection">
            <h4>Select Reference Sets to Query:</h4>
            {referenceSets.length === 0 ? (
              <p>No reference sets available. Create one first!</p>
            ) : (
              <div className="reference-sets-checkboxes">
                {referenceSets.map((refSet) => (
                  <label key={refSet.id} className="checkbox-label">
                    <input
                      type="checkbox"
                      checked={selectedReferenceSets.includes(refSet.id)}
                      onChange={() => toggleReferenceSet(refSet.id)}
                    />
                    {refSet.domain}
                  </label>
                ))}
              </div>
            )}
          </div>

          <div className="modal-buttons">
            <button type="button" onClick={onClose}>Cancel</button>
            <button 
              type="submit" 
              disabled={!title.trim() || selectedReferenceSets.length === 0}
            >
              Start Inquiry
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function InquiryChat({ inquiry, onClose }) {
  const [messages, setMessages] = useState(inquiry.messages || []);
  const [inputMessage, setInputMessage] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const sendMessage = async (e) => {
    e.preventDefault();
    if (!inputMessage.trim() || isLoading) return;

    const userMessage = {
      role: "user",
      content: inputMessage.trim(),
      timestamp: new Date().toISOString()
    };

    setMessages(prev => [...prev, userMessage]);
    setInputMessage("");
    setIsLoading(true);

    try {
      const response = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          inquiry_id: inquiry.id,
          query: userMessage.content,
          reference_sets: inquiry.reference_sets
        })
      });

      const data = await response.json();

      const assistantMessage = {
        role: "assistant",
        content: data.response,
        citations: data.citations || [],
        sources: data.sources || [],
        timestamp: new Date().toISOString()
      };

      setMessages(prev => [...prev, assistantMessage]);
    } catch (error) {
      const errorMessage = {
        role: "assistant",
        content: "Sorry, I encountered an error while processing your query. Please try again.",
        timestamp: new Date().toISOString()
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="inquiry-chat">
      <div className="chat-header">
        <h2>{inquiry.title}</h2>
        <div className="chat-controls">
          <span>Reference Sets: {inquiry.reference_sets?.join(", ") || "None"}</span>
          <button onClick={onClose} className="close-chat-btn">Close</button>
        </div>
      </div>

      <div className="chat-container">
        <div className="chat-messages">
          {messages.length === 0 && (
            <div className="welcome-message">
              <p>Welcome to your inquiry: <strong>{inquiry.title}</strong></p>
              <p>Ask questions about your selected reference sets and I'll help you find relevant information.</p>
            </div>
          )}

          {messages.map((message, index) => (
            <div key={index} className={`message ${message.role}`}>
              <div className="message-content">
                {message.content}
              </div>
              {message.citations && message.citations.length > 0 && (
                <div className="message-citations">
                  <h4>Sources:</h4>
                  <ul>
                    {message.citations.map((citation, i) => (
                      <li key={i}>{citation}</li>
                    ))}
                  </ul>
                </div>
              )}
              <div className="message-timestamp">
                {new Date(message.timestamp).toLocaleTimeString()}
              </div>
            </div>
          ))}

          {isLoading && (
            <div className="message assistant loading">
              <div className="message-content">Thinking...</div>
            </div>
          )}
        </div>

        <form onSubmit={sendMessage} className="chat-input">
          <input
            type="text"
            placeholder="Ask a question about your reference sets..."
            value={inputMessage}
            onChange={(e) => setInputMessage(e.target.value)}
            disabled={isLoading}
          />
          <button type="submit" disabled={isLoading || !inputMessage.trim()}>
            Send
          </button>
        </form>
      </div>
    </div>
  );
}

export default App;
import React, { useEffect, useState } from "react";

function App() {
  const [message, setMessage] = useState("Loading...");

  useEffect(() => {
    fetch(
      "https://56376295-779e-467a-8916-b1d03059a196-00-17banyxbocmbx.riker.replit.dev/api/hello",
    )
      .then((res) => res.json())
      .then((data) => setMessage(data.message))
      .catch((err) => setMessage("Could not connect to Flask backend"));
  }, []);

  return (
    <div style={{ padding: "2rem", fontFamily: "Arial" }}>
      <h1>Research Assistant</h1>
      <p>{message}</p>
    </div>
  );
}

export default App;

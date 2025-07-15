import React, { useState, useEffect } from "react";
import axios from "axios";
import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import {
  Box,
  Button,
  Container,
  TextField,
  Typography,
  Paper,
  Alert,
  CircularProgress,
} from "@mui/material";
import GitHubIcon from "@mui/icons-material/GitHub";

function Home() {
  const BASE_URL = process.env.REACT_APP_BASE_URL;
  console.log("[INIT] React BASE_URL =", BASE_URL); 

  const buildEndpoint = (endpoint) => `${BASE_URL}${endpoint}`;

  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [repoPath, setRepoPath] = useState("");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    console.log("[EFFECT] URL Search Params:", window.location.search);
    if (window.location.search.includes("auth=success")) {
      setIsAuthenticated(true);
      const cleanUrl = window.location.origin;
      console.log("[AUTH] Success - cleaning up URL");
      window.history.replaceState({}, document.title, cleanUrl);
    }
  }, []);

  const handleLogin = () => {
    localStorage.clear();
    sessionStorage.clear();
    console.log("[INIT] React BASE_URL =", BASE_URL); 
    const loginUrl = buildEndpoint("/dissertation/login");
    console.log("[LOGIN] Redirecting to:", loginUrl);
    window.location.href = loginUrl;
  };

  const handleRepoSubmit = async () => {
    setMessage("");
    if (!repoPath) {
      setMessage("Please enter a repository path.");
      console.warn("[FORM] Empty repoPath submitted.");
      return;
    }
    setLoading(true);
    try {
      console.log("[REQUEST] Submitting repoPath:", repoPath);
      const res = await axios.post(
        buildEndpoint("/dissertation/set_repo"),
        { repo_path: repoPath },
        { withCredentials: true }
      );
      console.log("[RESPONSE] set_repo success:", res.data);
      const { github_token, repo_path: repoId, message } = res.data;
      setMessage(message || "Repository path submitted successfully.");

      if (github_token && repoId) {
        console.log("[REQUEST] Sending configuration to backend...");
        const configRes = await axios.post(
          buildEndpoint("/dissertation/repo/configuration"),
          { id: github_token, repoId },
          { withCredentials: true }
        );
        console.log("[RESPONSE] configuration result:", configRes.data);
        if (configRes.data?.message) {
          setMessage(configRes.data.message);
        }
      }
    } catch (err) {
      const errMsg =
        err?.response?.data?.message ||
        err?.response?.data?.detail ||
        "Error submitting repository path.";
      console.error("[ERROR] During submission:", err);
      setMessage(errMsg);
    }
    setLoading(false);
  };

  return (
    <Container maxWidth="sm" sx={{ mt: 10 }}>
      <Paper elevation={6} sx={{ p: 4, borderRadius: 4 }}>
        <Box sx={{ textAlign: "center", mb: 2 }}>
          <GitHubIcon color="primary" sx={{ fontSize: 50, mb: 1 }} />
          <Typography variant="h4" gutterBottom>
            GitHub Authorization
          </Typography>
        </Box>
        {!isAuthenticated ? (
          <Box sx={{ textAlign: "center", mt: 4 }}>
            <Button
              variant="contained"
              size="large"
              startIcon={<GitHubIcon />}
              onClick={handleLogin}
              sx={{ px: 4, py: 1.5, fontSize: 18, borderRadius: 3 }}
              disabled={loading}
            >
              {loading ? (
                <CircularProgress size={24} color="inherit" sx={{ mr: 1 }} />
              ) : null}
              Login with GitHub
            </Button>
          </Box>
        ) : (
          <Box sx={{ mt: 2 }}>
            <Typography variant="h6" sx={{ mb: 2 }}>
              Enter Repository Path
            </Typography>
            <TextField
              fullWidth
              label="Repository (e.g. user/repo)"
              value={repoPath}
              onChange={(e) => {
                console.log("[INPUT] repoPath:", e.target.value);
                setRepoPath(e.target.value);
              }}
              variant="outlined"
              sx={{ mb: 2 }}
              disabled={loading}
            />
            <Button
              variant="contained"
              color="primary"
              onClick={handleRepoSubmit}
              sx={{ width: "100%", py: 1.2, fontWeight: "bold" }}
              disabled={loading}
              endIcon={
                loading ? <CircularProgress size={22} color="inherit" /> : null
              }
            >
              {loading ? "Processing..." : "Submit Repository Path"}
            </Button>
            {loading && (
              <Box sx={{ display: "flex", justifyContent: "center", mt: 2 }}>
                <CircularProgress size={32} color="primary" />
              </Box>
            )}
            {message && (
              <Alert severity="info" sx={{ mt: 3, fontWeight: 600 }}>
                {message}
              </Alert>
            )}
          </Box>
        )}
      </Paper>
    </Container>
  );
}

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route
          path="*"
          element={
            <Typography sx={{ mt: 10, textAlign: "center" }}>
              404 - Page Not Found
            </Typography>
          }
        />
      </Routes>
    </Router>
  );
}

const BASE_URL = process.env.REACT_APP_BASE_URL;
console.log("[INIT] React BASE_URL =", BASE_URL); // Log the base URL for debugging
export default App;

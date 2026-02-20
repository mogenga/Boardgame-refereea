import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/Layout';
import RulesPage from './pages/RulesPage';
import SessionsPage from './pages/SessionsPage';
import GamePage from './pages/GamePage';
import './App.css';

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Navigate to="/rules" replace />} />
          <Route path="rules" element={<RulesPage />} />
          <Route path="sessions" element={<SessionsPage />} />
          <Route path="game/:sessionId" element={<GamePage />} />
        </Route>
      </Routes>
    </Router>
  );
}

export default App;

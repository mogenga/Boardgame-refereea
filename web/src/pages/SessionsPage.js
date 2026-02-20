import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { rulesAPI, sessionsAPI } from '../services/api';
import { toast } from '../utils/toast';
import CreateSessionModal from '../components/CreateSessionModal';
import ConfirmDialog from '../components/ConfirmDialog';
import './SessionsPage.css';

function SessionsPage() {
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [confirmDialog, setConfirmDialog] = useState({ isOpen: false, sessionId: '', gameName: '' });
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    // 暂时使用本地存储模拟会话列表
    loadSessions();
  }, []);

  const loadSessions = () => {
    const stored = localStorage.getItem('sessions');
    if (stored) {
      setSessions(JSON.parse(stored));
    }
  };

  const handleDeleteClick = (session) => {
    setConfirmDialog({ 
      isOpen: true, 
      sessionId: session.session_id,
      gameName: session.game_name 
    });
  };

  const handleDeleteConfirm = async () => {
    const { sessionId } = confirmDialog;
    setConfirmDialog({ isOpen: false, sessionId: '', gameName: '' });

    try {
      await sessionsAPI.delete(sessionId);
      toast.success('删除成功');
      const updated = sessions.filter(s => s.session_id !== sessionId);
      setSessions(updated);
      localStorage.setItem('sessions', JSON.stringify(updated));
    } catch (error) {
      toast.error('删除失败');
      console.error(error);
    }
  };

  const handleDeleteCancel = () => {
    setConfirmDialog({ isOpen: false, sessionId: '', gameName: '' });
  };

  const handleCreateSuccess = (newSession) => {
    setShowCreateModal(false);
    const updated = [...sessions, newSession];
    setSessions(updated);
    localStorage.setItem('sessions', JSON.stringify(updated));
    navigate(`/game/${newSession.session_id}`);
  };

  const formatTime = (timestamp) => {
    const now = new Date();
    const created = new Date(timestamp);
    const diff = Math.floor((now - created) / 1000);
    
    if (diff < 60) return '刚刚';
    if (diff < 3600) return `${Math.floor(diff / 60)}分钟前`;
    if (diff < 86400) return `${Math.floor(diff / 3600)}小时前`;
    return `${Math.floor(diff / 86400)}天前`;
  };

  return (
    <div className="sessions-page">
      <div className="page-header">
        <h1 className="page-title">游戏大厅</h1>
        <button className="btn btn-primary" onClick={() => setShowCreateModal(true)}>
          + 创建新游戏
        </button>
      </div>

      {sessions.length === 0 ? (
        <div className="empty-state">
          <div className="empty-icon">🎯</div>
          <h3>还没有进行中的游戏</h3>
          <p>点击创建开始新的游戏会话</p>
          <button className="btn btn-primary" onClick={() => setShowCreateModal(true)}>
            创建第一个游戏
          </button>
        </div>
      ) : (
        <div className="sessions-list">
          <h2>进行中的游戏</h2>
          {sessions.map((session) => (
            <div key={session.session_id} className="session-card">
              <div className="session-info">
                <div className="session-title">
                  <span className="session-icon">🎮</span>
                  <span className="session-game">{session.game_name}</span>
                  <span className="session-round">· 第 {session.round} 回合</span>
                </div>
                <div className="session-players">
                  玩家：{session.players.join('、')}
                </div>
              </div>
              <div className="session-actions">
                <span className="session-time">{formatTime(session.created_at)}</span>
                <button
                  className="btn btn-primary btn-sm"
                  onClick={() => navigate(`/game/${session.session_id}`)}
                >
                  进入
                </button>
                <button
                  className="btn btn-danger btn-sm"
                  onClick={() => handleDeleteClick(session)}
                >
                  删除
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {showCreateModal && (
        <CreateSessionModal
          onClose={() => setShowCreateModal(false)}
          onSuccess={handleCreateSuccess}
          preselectedGame={location.state?.selectedGame}
        />
      )}

      <ConfirmDialog
        isOpen={confirmDialog.isOpen}
        title="确认删除"
        message={`确定删除《${confirmDialog.gameName}》的游戏会话？`}
        onConfirm={handleDeleteConfirm}
        onCancel={handleDeleteCancel}
        confirmText="删除"
        danger={true}
      />
    </div>
  );
}

export default SessionsPage;

import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { rulesAPI } from '../services/api';
import { toast } from '../utils/toast';
import UploadModal from '../components/UploadModal';
import ConfirmDialog from '../components/ConfirmDialog';
import './RulesPage.css';

function RulesPage() {
  const [games, setGames] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [confirmDialog, setConfirmDialog] = useState({ isOpen: false, gameName: '' });
  const navigate = useNavigate();

  useEffect(() => {
    loadGames();
  }, []);

  const loadGames = async () => {
    try {
      setLoading(true);
      const response = await rulesAPI.list();
      setGames(response.data.games || []);
    } catch (error) {
      toast.error('加载游戏列表失败');
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteClick = (gameName) => {
    setConfirmDialog({ isOpen: true, gameName });
  };

  const handleDeleteConfirm = async () => {
    const { gameName } = confirmDialog;
    setConfirmDialog({ isOpen: false, gameName: '' });

    try {
      await rulesAPI.delete(gameName);
      toast.success('删除成功');
      loadGames();
    } catch (error) {
      toast.error('删除失败');
      console.error(error);
    }
  };

  const handleDeleteCancel = () => {
    setConfirmDialog({ isOpen: false, gameName: '' });
  };

  const handleUploadSuccess = () => {
    setShowUploadModal(false);
    loadGames();
  };

  const handleGameClick = (gameName) => {
    navigate('/sessions', { state: { selectedGame: gameName } });
  };

  if (loading) {
    return (
      <div className="loading">
        <div className="spinner"></div>
      </div>
    );
  }

  return (
    <div className="rules-page">
      <div className="page-header">
        <h1 className="page-title">规则库管理</h1>
        <button className="btn btn-primary" onClick={() => setShowUploadModal(true)}>
          + 上传规则书
        </button>
      </div>

      {games.length === 0 ? (
        <div className="empty-state">
          <div className="empty-icon">📚</div>
          <h3>还没有规则书</h3>
          <p>点击上传开始添加游戏规则</p>
          <button className="btn btn-primary" onClick={() => setShowUploadModal(true)}>
            上传第一本规则书
          </button>
        </div>
      ) : (
        <div className="games-grid">
          {games.map((game) => (
            <div key={game} className="game-card" onClick={() => handleGameClick(game)}>
              <div className="game-icon">🎮</div>
              <h3 className="game-name">{game}</h3>
              <div className="game-status">已入库</div>
              <button
                className="btn btn-danger btn-sm"
                onClick={(e) => {
                  e.stopPropagation();
                  handleDeleteClick(game);
                }}
              >
                删除
              </button>
            </div>
          ))}
        </div>
      )}

      {showUploadModal && (
        <UploadModal
          onClose={() => setShowUploadModal(false)}
          onSuccess={handleUploadSuccess}
        />
      )}

      <ConfirmDialog
        isOpen={confirmDialog.isOpen}
        title="确认删除"
        message={`确定删除《${confirmDialog.gameName}》的规则数据？此操作不可恢复`}
        onConfirm={handleDeleteConfirm}
        onCancel={handleDeleteCancel}
        confirmText="删除"
        danger={true}
      />
    </div>
  );
}

export default RulesPage;

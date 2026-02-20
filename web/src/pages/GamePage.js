import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { sessionsAPI, stateAPI } from '../services/api';
import { toast } from '../utils/toast';
import ChatPanel from '../components/ChatPanel';
import ConfirmDialog from '../components/ConfirmDialog';
import './GamePage.css';

function GamePage() {
  const { sessionId } = useParams();
  const navigate = useNavigate();
  const [gameState, setGameState] = useState(null);
  const [loading, setLoading] = useState(true);
  const [selectedPlayer, setSelectedPlayer] = useState('');
  const [hpDelta, setHpDelta] = useState('');
  const [hpReason, setHpReason] = useState('');
  const [confirmDialog, setConfirmDialog] = useState({ isOpen: false, type: '' });

  useEffect(() => {
    loadGameState();
  }, [sessionId]);

  const loadGameState = async () => {
    try {
      setLoading(true);
      const response = await sessionsAPI.get(sessionId);
      setGameState(response.data.state);
      if (response.data.state.players) {
        const firstPlayer = Object.keys(response.data.state.players)[0];
        setSelectedPlayer(firstPlayer);
      }
    } catch (error) {
      toast.error('加载游戏状态失败');
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const handleManualHpAdjust = async () => {
    if (!selectedPlayer || !hpDelta) {
      toast.error('请填写完整信息');
      return;
    }

    try {
      await stateAPI.updateHp(sessionId, selectedPlayer, {
        delta: parseInt(hpDelta),
        reason: hpReason || '手动调整',
      });
      toast.success('血量已更新');
      setHpDelta('');
      setHpReason('');
      loadGameState();
    } catch (error) {
      toast.error('更新失败');
      console.error(error);
    }
  };

  const handleNextRound = async () => {
    try {
      await stateAPI.nextRound(sessionId);
      toast.success('回合已切换');
      loadGameState();
    } catch (error) {
      toast.error('切换失败');
      console.error(error);
    }
  };

  const handleRemoveEffect = async (playerName, effect) => {
    try {
      await stateAPI.updateEffects(sessionId, playerName, {
        action: 'remove',
        effect: effect,
      });
      toast.success('效果已移除');
      loadGameState();
    } catch (error) {
      toast.error('移除失败');
      console.error(error);
    }
  };

  const handleResetClick = () => {
    setConfirmDialog({ isOpen: true, type: 'reset' });
  };

  const handleEndGameClick = () => {
    setConfirmDialog({ isOpen: true, type: 'end' });
  };

  const handleConfirm = async () => {
    const { type } = confirmDialog;
    setConfirmDialog({ isOpen: false, type: '' });

    if (type === 'reset') {
      try {
        await sessionsAPI.reset(sessionId);
        toast.success('游戏已重置');
        loadGameState();
      } catch (error) {
        toast.error('重置失败');
        console.error(error);
      }
    } else if (type === 'end') {
      try {
        await sessionsAPI.delete(sessionId);
        toast.success('游戏已结束');
        navigate('/sessions');
      } catch (error) {
        toast.error('结束失败');
        console.error(error);
      }
    }
  };

  const handleCancel = () => {
    setConfirmDialog({ isOpen: false, type: '' });
  };

  const getHpPercentage = (hp, maxHp) => {
    return (hp / maxHp) * 100;
  };

  const getHpClass = (percentage) => {
    if (percentage > 60) return 'high';
    if (percentage > 30) return 'medium';
    return 'low';
  };

  if (loading) {
    return (
      <div className="loading">
        <div className="spinner"></div>
      </div>
    );
  }

  if (!gameState) {
    return <div>游戏不存在</div>;
  }

  return (
    <div className="game-page">
      <div className="game-header">
        <div className="game-header-left">
          <button className="back-btn" onClick={() => navigate('/sessions')}>
            ← 返回大厅
          </button>
          <div className="game-title">
            <span>🎮</span>
            <span>{gameState.game_name} · 第{gameState.round}回合</span>
          </div>
        </div>
        <div className="game-header-actions">
          <button className="btn btn-secondary btn-sm" onClick={handleResetClick}>
            重置
          </button>
          <button className="btn btn-danger btn-sm" onClick={handleEndGameClick}>
            结束游戏
          </button>
        </div>
      </div>

      <div className="game-content">
        {/* 左栏：游戏状态 */}
        <div className="game-state-panel">
          <div className="state-section">
            <h3>游戏状态</h3>
            <div className="game-info">
              <span>回合：{gameState.round}</span>
              <span>当前：{gameState.current_player}</span>
            </div>
          </div>

          <div className="state-section">
            <h3>玩家状态</h3>
            {Object.values(gameState.players).map((player) => {
              const hpPercent = getHpPercentage(player.hp, player.max_hp);
              const isDead = player.hp === 0;
              const isCurrent = player.name === gameState.current_player;

              return (
                <div
                  key={player.name}
                  className={`player-card ${isCurrent ? 'current' : ''} ${isDead ? 'dead' : ''}`}
                >
                  <div className="player-header">
                    <span>👤</span>
                    <span className="player-name">{player.name}</span>
                    {isCurrent && <span className="current-badge">当前回合</span>}
                    {isDead && <span>💀</span>}
                  </div>

                  <div className="hp-bar-container">
                    <div className="hp-text">
                      <span>❤️ 血量</span>
                      <span>{player.hp}/{player.max_hp}</span>
                    </div>
                    <div className="hp-bar">
                      <div
                        className={`hp-fill ${getHpClass(hpPercent)}`}
                        style={{ width: `${hpPercent}%` }}
                      ></div>
                    </div>
                  </div>

                  <div className="status-effects">
                    <span style={{ color: '#a0aec0', fontSize: '12px' }}>状态：</span>
                    {player.status_effects.length === 0 ? (
                      <span style={{ color: '#a0aec0', fontSize: '12px' }}>无</span>
                    ) : (
                      player.status_effects.map((effect, idx) => (
                        <span
                          key={idx}
                          className={`status-tag ${effect.includes('护盾') || effect.includes('增益') ? 'positive' : 'negative'}`}
                          onClick={() => handleRemoveEffect(player.name, effect)}
                          title="点击移除"
                        >
                          {effect}
                        </span>
                      ))
                    )}
                  </div>
                </div>
              );
            })}
          </div>

          <div className="state-section">
            <h3>手动调整</h3>
            <div className="manual-adjust">
              <label>玩家</label>
              <select value={selectedPlayer} onChange={(e) => setSelectedPlayer(e.target.value)}>
                {Object.keys(gameState.players).map(name => (
                  <option key={name} value={name}>{name}</option>
                ))}
              </select>

              <label>血量变化</label>
              <input
                type="number"
                placeholder="正数回血，负数扣血"
                value={hpDelta}
                onChange={(e) => setHpDelta(e.target.value)}
              />

              <label>原因</label>
              <input
                type="text"
                placeholder="例如：被火球术命中"
                value={hpReason}
                onChange={(e) => setHpReason(e.target.value)}
              />

              <button className="btn btn-primary btn-sm" onClick={handleManualHpAdjust} style={{ width: '100%' }}>
                应用
              </button>
            </div>
          </div>

          <button className="next-round-btn" onClick={handleNextRound}>
            结束回合 →
          </button>
        </div>

        {/* 右栏：裁判问答 */}
        <ChatPanel sessionId={sessionId} gameName={gameState.game_name} onStateChange={loadGameState} />
      </div>

      <ConfirmDialog
        isOpen={confirmDialog.isOpen}
        title={confirmDialog.type === 'reset' ? '确认重置' : '确认结束游戏'}
        message={
          confirmDialog.type === 'reset' 
            ? '确定重置游戏状态？所有玩家血量将恢复，回合数归1，对话历史将清空。' 
            : '确定结束游戏？游戏数据将被删除，此操作不可恢复。'
        }
        onConfirm={handleConfirm}
        onCancel={handleCancel}
        confirmText={confirmDialog.type === 'reset' ? '重置' : '结束游戏'}
        danger={true}
      />
    </div>
  );
}

export default GamePage;

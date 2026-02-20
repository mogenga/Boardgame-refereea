import React, { useState, useEffect } from 'react';
import { rulesAPI, sessionsAPI } from '../services/api';
import { toast } from '../utils/toast';
import './CreateSessionModal.css';

function CreateSessionModal({ onClose, onSuccess, preselectedGame }) {
  const [games, setGames] = useState([]);
  const [selectedGame, setSelectedGame] = useState(preselectedGame || '');
  const [players, setPlayers] = useState([{ name: '', hp: 100 }]);
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    loadGames();
  }, []);

  const loadGames = async () => {
    try {
      const response = await rulesAPI.list();
      setGames(response.data.games || []);
      if (response.data.games.length > 0 && !preselectedGame) {
        setSelectedGame(response.data.games[0]);
      }
    } catch (error) {
      toast.error('加载游戏列表失败');
    }
  };

  const addPlayer = () => {
    if (players.length >= 8) {
      toast.error('最多支持 8 名玩家');
      return;
    }
    setPlayers([...players, { name: '', hp: 100 }]);
  };

  const removePlayer = (index) => {
    if (players.length <= 1) {
      toast.error('至少需要 1 名玩家');
      return;
    }
    setPlayers(players.filter((_, i) => i !== index));
  };

  const updatePlayer = (index, field, value) => {
    const updated = [...players];
    updated[index][field] = value;
    setPlayers(updated);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!selectedGame) {
      toast.error('请选择游戏');
      return;
    }

    const validPlayers = players.filter(p => p.name.trim());
    if (validPlayers.length === 0) {
      toast.error('至少需要填写 1 名玩家');
      return;
    }

    const names = validPlayers.map(p => p.name.trim());
    if (new Set(names).size !== names.length) {
      toast.error('玩家名称不能重复');
      return;
    }

    try {
      setCreating(true);
      const response = await sessionsAPI.create({
        game_name: selectedGame,
        players: validPlayers.map(p => ({
          name: p.name.trim(),
          hp: parseInt(p.hp) || 100,
          max_hp: parseInt(p.hp) || 100,
        })),
      });

      const sessionData = {
        session_id: response.data.session_id,
        game_name: selectedGame,
        round: 1,
        players: names,
        created_at: new Date().toISOString(),
      };

      toast.success('游戏创建成功');
      onSuccess(sessionData);
    } catch (error) {
      toast.error(error.response?.data?.error || '创建失败');
      console.error(error);
    } finally {
      setCreating(false);
    }
  };

  if (games.length === 0) {
    return (
      <div className="modal-overlay" onClick={onClose}>
        <div className="modal-content" onClick={(e) => e.stopPropagation()}>
          <div className="modal-header">
            <h2>创建新游戏会话</h2>
            <button className="modal-close" onClick={onClose}>×</button>
          </div>
          <div style={{ padding: '24px', textAlign: 'center' }}>
            <p style={{ color: '#a0aec0' }}>请先前往规则库上传规则书</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content create-session-modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>创建新游戏会话</h2>
          <button className="modal-close" onClick={onClose}>×</button>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label>选择游戏规则书</label>
            <select
              className="form-input"
              value={selectedGame}
              onChange={(e) => setSelectedGame(e.target.value)}
              disabled={creating}
            >
              {games.map(game => (
                <option key={game} value={game}>{game}</option>
              ))}
            </select>
          </div>

          <div className="form-group">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
              <label style={{ margin: 0 }}>添加玩家</label>
              <button type="button" className="btn btn-sm btn-primary" onClick={addPlayer}>
                + 添加
              </button>
            </div>

            {players.map((player, index) => (
              <div key={index} className="player-input-group">
                <input
                  type="text"
                  className="form-input"
                  placeholder="玩家姓名"
                  value={player.name}
                  onChange={(e) => updatePlayer(index, 'name', e.target.value)}
                  disabled={creating}
                />
                <input
                  type="number"
                  className="form-input"
                  placeholder="初始血量"
                  value={player.hp}
                  onChange={(e) => updatePlayer(index, 'hp', e.target.value)}
                  disabled={creating}
                  min="1"
                />
                <button
                  type="button"
                  className="player-remove-btn"
                  onClick={() => removePlayer(index)}
                  disabled={creating}
                >
                  ×
                </button>
              </div>
            ))}
          </div>

          <div className="modal-footer">
            <button type="button" className="btn btn-secondary" onClick={onClose} disabled={creating}>
              取消
            </button>
            <button type="submit" className="btn btn-primary" disabled={creating}>
              {creating ? '创建中...' : '开始游戏'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default CreateSessionModal;

import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 规则书管理
export const rulesAPI = {
  // 获取已入库游戏列表
  list: () => api.get('/api/rules'),
  
  // 上传规则书
  upload: (file, gameName) => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('game_name', gameName);
    return api.post('/api/rules/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
  },
  
  // 删除规则书
  delete: (gameName) => api.delete(`/api/rules/${gameName}`),
};

// 游戏会话管理
export const sessionsAPI = {
  // 创建会话
  create: (data) => api.post('/api/sessions', data),
  
  // 获取会话状态
  get: (sessionId) => api.get(`/api/sessions/${sessionId}`),
  
  // 重置会话
  reset: (sessionId) => api.post(`/api/sessions/${sessionId}/reset`),
  
  // 删除会话
  delete: (sessionId) => api.delete(`/api/sessions/${sessionId}`),
  
  // 获取操作日志
  getLogs: (sessionId) => api.get(`/api/sessions/${sessionId}/logs`),
};

// 状态操作
export const stateAPI = {
  // 更新血量
  updateHp: (sessionId, playerName, data) => 
    api.patch(`/api/sessions/${sessionId}/players/${playerName}/hp`, data),
  
  // 更新状态效果
  updateEffects: (sessionId, playerName, data) => 
    api.patch(`/api/sessions/${sessionId}/players/${playerName}/effects`, data),
  
  // 更新资源
  updateResources: (sessionId, playerName, data) => 
    api.patch(`/api/sessions/${sessionId}/players/${playerName}/resources`, data),
  
  // 切换回合
  nextRound: (sessionId, data = {}) => 
    api.post(`/api/sessions/${sessionId}/next-round`, data),
};

// 规则问答
export const queryAPI = {
  // 普通问答
  query: (data) => api.post('/api/query', data),
  
  // 流式问答（返回 EventSource URL）
  getStreamUrl: (sessionId, question) => {
    return `${API_BASE_URL}/api/query/stream`;
  },
};

export default api;

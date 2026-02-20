import React, { useState, useRef, useEffect } from 'react';
import { queryAPI } from '../services/api';
import { toast } from '../utils/toast';
import './ChatPanel.css';

function ChatPanel({ sessionId, gameName, onStateChange }) {
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content: `你好！我是本局的规则裁判。有任何规则疑问随时提问，我会根据《${gameName}》规则书给出裁定。`,
    },
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!input.trim() || loading) return;

    const userMessage = input.trim();
    setInput('');
    setMessages(prev => [...prev, { role: 'user', content: userMessage }]);

    try {
      setLoading(true);
      
      // 使用普通问答接口
      const response = await queryAPI.query({
        session_id: sessionId,
        question: userMessage,
        stream: false,
      });

      const assistantMessage = {
        role: 'assistant',
        content: response.data.answer,
        rule_references: response.data.rule_references || [],
        state_changes: response.data.state_changes || [],
      };

      setMessages(prev => [...prev, assistantMessage]);

      // 如果有状态变更，刷新游戏状态
      if (response.data.state_changes && response.data.state_changes.length > 0) {
        onStateChange();
      }
    } catch (error) {
      toast.error('裁定失败，请重试');
      console.error(error);
      setMessages(prev => [
        ...prev,
        {
          role: 'assistant',
          content: '抱歉，裁定过程出现错误，请重试。',
          error: true,
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  return (
    <div className="chat-panel">
      <div className="chat-header">
        <h3>🎲 裁判助手</h3>
      </div>

      <div className="chat-messages">
        {messages.map((msg, idx) => (
          <div key={idx} className={`message ${msg.role}`}>
            <div className="message-bubble">
              <div className="message-content">{msg.content}</div>

              {msg.rule_references && msg.rule_references.length > 0 && (
                <details className="rule-references">
                  <summary>📖 规则出处 ({msg.rule_references.length})</summary>
                  {msg.rule_references.map((ref, i) => (
                    <div key={i} className="rule-ref-item">
                      <div className="rule-ref-content">{ref.content}</div>
                      {ref.page && <div className="rule-ref-page">第 {ref.page} 页</div>}
                    </div>
                  ))}
                </details>
              )}

              {msg.state_changes && msg.state_changes.length > 0 && (
                <div className="state-changes">
                  <div className="state-changes-title">🔄 状态变更</div>
                  {msg.state_changes.map((change, i) => (
                    <div key={i} className="state-change-item">
                      · {formatStateChange(change)}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}

        {loading && (
          <div className="message assistant">
            <div className="message-bubble">
              <div className="typing-indicator">
                <span></span>
                <span></span>
                <span></span>
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      <form className="chat-input-form" onSubmit={handleSubmit}>
        <textarea
          className="chat-input"
          placeholder="输入规则问题..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={loading}
          rows={3}
        />
        <button type="submit" className="chat-submit-btn" disabled={loading || !input.trim()}>
          裁定
        </button>
      </form>
    </div>
  );
}

function formatStateChange(change) {
  const { action, player, details, reason } = change;

  switch (action) {
    case 'update_player_hp':
      const delta = details.delta;
      return `${player} 血量 ${delta > 0 ? '+' : ''}${delta}${reason ? ` (${reason})` : ''}`;
    case 'apply_status_effect':
      return `${player} 获得状态效果: ${details.effect}`;
    case 'remove_status_effect':
      return `${player} 移除状态效果: ${details.effect}`;
    case 'update_player_resource':
      return `${player} ${details.resource_name} ${details.delta > 0 ? '+' : ''}${details.delta}`;
    case 'next_round':
      return `切换到下一回合`;
    default:
      return JSON.stringify(change);
  }
}

export default ChatPanel;

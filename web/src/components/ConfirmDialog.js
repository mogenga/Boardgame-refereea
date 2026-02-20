import React from 'react';
import './ConfirmDialog.css';

function ConfirmDialog({ isOpen, title, message, onConfirm, onCancel, confirmText = '确定', cancelText = '取消', danger = false }) {
  if (!isOpen) return null;

  return (
    <div className="confirm-overlay" onClick={onCancel}>
      <div className="confirm-dialog" onClick={(e) => e.stopPropagation()}>
        <div className="confirm-header">
          <h3>{title}</h3>
        </div>
        
        <div className="confirm-body">
          <p>{message}</p>
        </div>
        
        <div className="confirm-footer">
          <button className="btn btn-secondary" onClick={onCancel}>
            {cancelText}
          </button>
          <button 
            className={`btn ${danger ? 'btn-danger' : 'btn-primary'}`} 
            onClick={onConfirm}
          >
            {confirmText}
          </button>
        </div>
      </div>
    </div>
  );
}

export default ConfirmDialog;

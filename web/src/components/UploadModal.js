import React, { useState } from 'react';
import { rulesAPI } from '../services/api';
import { toast } from '../utils/toast';
import './UploadModal.css';

function UploadModal({ onClose, onSuccess }) {
  const [gameName, setGameName] = useState('');
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [dragActive, setDragActive] = useState(false);

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileSelect(e.dataTransfer.files[0]);
    }
  };

  const handleFileSelect = (selectedFile) => {
    const validExtensions = ['.pdf', '.txt'];
    const fileExt = selectedFile.name.substring(selectedFile.name.lastIndexOf('.')).toLowerCase();
    
    if (!validExtensions.includes(fileExt)) {
      toast.error('仅支持 PDF 和 TXT 格式');
      return;
    }
    
    if (selectedFile.size > 20 * 1024 * 1024) {
      toast.error('文件大小不能超过 20MB');
      return;
    }
    
    setFile(selectedFile);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!gameName.trim()) {
      toast.error('请输入游戏名称');
      return;
    }
    
    if (!file) {
      toast.error('请选择文件');
      return;
    }

    try {
      setUploading(true);
      const response = await rulesAPI.upload(file, gameName.trim());
      toast.success(response.data.message || '上传成功');
      onSuccess();
    } catch (error) {
      toast.error(error.response?.data?.error || '上传失败');
      console.error(error);
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>上传规则书</h2>
          <button className="modal-close" onClick={onClose}>×</button>
        </div>
        
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label>游戏名称</label>
            <input
              type="text"
              className="form-input"
              placeholder="请输入游戏名称"
              value={gameName}
              onChange={(e) => setGameName(e.target.value)}
              disabled={uploading}
            />
          </div>

          <div className="form-group">
            <label>规则书文件（PDF / TXT）</label>
            <div
              className={`file-drop-zone ${dragActive ? 'active' : ''}`}
              onDragEnter={handleDrag}
              onDragLeave={handleDrag}
              onDragOver={handleDrag}
              onDrop={handleDrop}
            >
              {file ? (
                <div className="file-selected">
                  <span className="file-icon">📄</span>
                  <span className="file-name">{file.name}</span>
                  <button
                    type="button"
                    className="file-remove"
                    onClick={() => setFile(null)}
                  >
                    ×
                  </button>
                </div>
              ) : (
                <>
                  <div className="file-icon">📄</div>
                  <p>拖拽文件到此处</p>
                  <p>或</p>
                  <label className="file-select-btn">
                    点击选择文件
                    <input
                      type="file"
                      accept=".pdf,.txt"
                      onChange={(e) => e.target.files[0] && handleFileSelect(e.target.files[0])}
                      style={{ display: 'none' }}
                    />
                  </label>
                </>
              )}
            </div>
          </div>

          <div className="modal-footer">
            <button type="button" className="btn btn-secondary" onClick={onClose} disabled={uploading}>
              取消
            </button>
            <button type="submit" className="btn btn-primary" disabled={uploading}>
              {uploading ? '上传中...' : '开始上传'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default UploadModal;

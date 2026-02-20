# 桌游规则裁判助手 | Boardgame Referee AI

一个基于 AI 的桌游裁判助手，支持上传规则书、自然语言提问、自动裁定并维护游戏状态。适用于桌游、DND、剧本杀等复杂规则游戏。

## ✨ 核心功能

- **智能规则查询**：上传 PDF/TXT 规则书，用自然语言提问即可获得裁定
- **规则溯源**：每次裁定都附带规则书原文出处，保证有据可依
- **游戏状态管理**：自动追踪玩家血量、状态效果、资源、回合顺序
- **AI 自动操作**：LLM 通过 Function Calling 自动更新游戏状态（扣血、加 buff、资源变化等）
- **多轮对话**：支持连续追问，AI 具备上下文感知能力
- **多游戏支持**：可同时管理多个游戏的规则书和会话

## 🚀 快速开始

### 环境要求

- Python >= 3.11
- Node.js >= 16（前端）
- OpenAI API Key

### 后端启动

```bash
cd Backend
pip install -r requirements.txt
cp .env.example .env
# 编辑 .env 文件，填入你的 OPENAI_API_KEY
python main.py
```

后端运行在 `http://localhost:8000`

### 前端启动

```bash
cd web
npm install
cp .env.example .env
# 如需修改后端地址，编辑 .env 文件
npm start
```

前端运行在 `http://localhost:3000`

## 📖 使用流程

1. **上传规则书**：进入规则管理页面，上传游戏的 PDF 规则书
2. **创建会话**：新建游戏会话，设置玩家名称和初始状态
3. **提问裁定**：游戏过程中用自然语言提问，AI 给出裁定和规则出处
4. **自动更新**：AI 根据裁定自动更新玩家血量、状态效果、资源等

## 🏗️ 技术架构

```
前端 (React) → FastAPI 后端 → LangChain RAG → OpenAI GPT-4o
                              ↓
                       ChromaDB (向量数据库)
                              ↓
                       Redis (会话状态存储)
```

### 技术栈

**后端：**
- FastAPI + Uvicorn
- LangChain（RAG 编排）
- OpenAI GPT-4o（LLM + Function Calling）
- ChromaDB（向量数据库）
- Redis（会话存储）
- PyMuPDF（PDF 解析）

**前端：**
- React
- Axios（API 调用）

## 📁 项目结构

```
├── Backend/
│   ├── api/          # REST API 接口
│   ├── core/         # RAG、LLM、状态管理核心逻辑
│   ├── models/       # Pydantic 数据模型
│   └── storage/      # ChromaDB 持久化目录
└── web/
    └── src/
        ├── components/  # React 组件
        ├── pages/       # 页面视图
        └── services/    # API 客户端
```

## 🔧 主要接口

- `POST /api/rules/upload` - 上传规则书
- `GET /api/rules` - 查询已入库游戏列表
- `POST /api/sessions` - 创建游戏会话
- `GET /api/sessions/{id}` - 查询会话状态
- `POST /api/query` - 规则问答（核心接口）
- `PATCH /api/sessions/{id}/players/{name}/hp` - 更新玩家血量

## 📝 开源协议

MIT License - 详见 [LICENSE](LICENSE) 文件

## 🤝 贡献指南

欢迎提交 Pull Request 或 Issue！

## 📮 联系方式

如有问题或建议，请在 GitHub 上提交 Issue。
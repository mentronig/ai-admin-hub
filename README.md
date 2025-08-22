# 🤖 AI Admin Hub

[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Build Status](https://img.shields.io/badge/Build-Passing-brightgreen.svg)]()

**AI-powered admin hub for n8n workflows with intelligent diagnostics and automation**

---

## 🎯 **Overview**

AI Admin Hub is a modern Python framework that transforms traditional n8n workflow management into an intelligent, AI-powered automation platform. Built from the ground up with cross-platform compatibility and smart diagnostics.

### **🚀 Key Features**

- **🤖 AI-Powered Diagnostics** - GPT-4 integration for intelligent error analysis and solutions
- **⚙️ Automated Backup Management** - Smart workflow versioning with GitHub integration  
- **📊 Real-time System Monitoring** - Comprehensive health checks and performance metrics
- **🎨 Modern Web Interface** - Beautiful React dashboard with real-time updates
- **🔧 Cross-Platform Support** - Works seamlessly on Windows, macOS, and Linux
- **📱 CLI & Web UI** - Choose your preferred interface

---

## 🛠️ **Tech Stack**

| Component | Technology | Purpose |
|-----------|------------|---------|
| **Backend** | Python 3.9+ | Core application logic |
| **CLI Framework** | Typer + Rich | Beautiful command-line interface |
| **Configuration** | Pydantic | Type-safe settings management |
| **API Integration** | httpx/requests | N8n and GitHub API clients |
| **AI Integration** | OpenAI API | Intelligent diagnostics and automation |
| **Web Backend** | FastAPI | REST API for web interface |
| **Frontend** | React + Tailwind | Modern, responsive web UI |
| **Database** | SQLite/PostgreSQL | Data persistence |
| **Deployment** | Docker | Containerized deployment |

---

## 📦 **Installation**

### **Prerequisites**
- Python 3.9 or higher
- Poetry (recommended) or pip
- Git
- N8n instance (local or remote)
- GitHub account (for backup functionality)

### **Quick Start**

```bash
# Clone the repository
git clone https://github.com/yourusername/ai-admin-hub.git
cd ai-admin-hub

# Install dependencies with Poetry
poetry install

# Or with pip
pip install -e .

# Initialize configuration
ai-admin config init

# Check system status
ai-admin status system
```

---

## ⚙️ **Configuration**

### **Environment Setup**

1. **Copy the environment template:**
   ```bash
   cp .env.template .env
   ```

2. **Edit `.env` with your settings:**
   ```bash
   # N8n Configuration
   N8N_API_KEY=your_n8n_api_key_here
   N8N_BASE_URL=http://localhost:5678
   N8N_WORKFLOW_ID=your_primary_workflow_id

   # GitHub Configuration  
   GITHUB_TOKEN=your_github_personal_access_token
   GITHUB_REPO_URL=https://github.com/username/repository

   # AI Configuration (Optional)
   OPENAI_API_KEY=your_openai_api_key
   ```

3. **Validate configuration:**
   ```bash
   ai-admin config validate
   ```

---

## 🚀 **Usage**

### **Command Line Interface**

```bash
# System status and health checks
ai-admin status system
ai-admin status workflows

# Backup operations
ai-admin backup now
ai-admin backup list
ai-admin backup restore v1.2.0

# Workflow management
ai-admin workflow export my-workflow
ai-admin workflow import backup.json
ai-admin workflow diff v1.0.0 v1.1.0

# AI-powered diagnostics
ai-admin ai diagnose
ai-admin ai optimize
ai-admin ai auto-fix
```

### **Web Interface**

```bash
# Start the web server
ai-admin web serve --port 8000

# Open browser to http://localhost:8000
```

---

## 🏗️ **Development**

### **Setting up Development Environment**

```bash
# Clone and enter directory
git clone https://github.com/yourusername/ai-admin-hub.git
cd ai-admin-hub

# Install development dependencies
poetry install --with dev

# Install pre-commit hooks
pre-commit install

# Run tests
pytest

# Code quality checks
black .
isort .
pylint src/
mypy src/
```

### **Project Structure**

```
ai-admin-hub/
├── src/ai_admin_hub/          # Main application package
│   ├── cli.py                 # CLI entry point
│   ├── config.py              # Configuration management
│   ├── clients/               # API clients (N8n, GitHub)
│   ├── commands/              # CLI command implementations
│   ├── core/                  # Business logic
│   └── models/                # Data models
├── tests/                     # Test suite
├── docs/                      # Documentation
├── scripts/                   # Utility scripts
└── pyproject.toml            # Project configuration
```

---

## 🤖 **AI Integration**

AI Admin Hub leverages OpenAI's GPT-4 for intelligent automation:

- **Smart Error Analysis** - Converts cryptic error messages into actionable solutions
- **Performance Optimization** - Analyzes workflow patterns and suggests improvements
- **Predictive Maintenance** - Identifies potential issues before they occur
- **Auto-Repair Functions** - Safely fixes common problems with confirmation prompts

### **Example AI Interactions**

```bash
# Instead of: "Error 401: Unauthorized"
# AI provides: "API Key format incorrect. N8n expects X-N8N-API-KEY header, 
#              not Bearer token. Fix: Update header in config."

ai-admin ai diagnose
ai-admin ai optimize --workflow my-workflow
ai-admin ai auto-fix --confirm
```

---

## 📊 **Monitoring & Metrics**

- **Real-time System Health** - API connectivity, Git status, workflow states
- **Performance Metrics** - Execution times, success rates, resource usage
- **Cost Tracking** - AI API usage and associated costs
- **Historical Trends** - Long-term performance and reliability analytics

---

## 🔒 **Security**

- **Secure Credential Management** - Environment-based configuration with .env files
- **API Key Protection** - Never commits sensitive data to Git
- **Rate Limiting** - Respects API limits for N8n, GitHub, and OpenAI
- **Audit Logging** - Comprehensive logs for all operations

---

## 🗺️ **Roadmap**

- [x] **Phase 1:** Core Python Framework & CLI
- [x] **Phase 2:** AI Integration & Smart Diagnostics
- [ ] **Phase 3:** Web Interface & Dashboard
- [ ] **Phase 4:** Advanced Analytics & Monitoring
- [ ] **Phase 5:** Multi-tenant & Enterprise Features

See our [detailed backlog](docs/backlog.md) for complete project roadmap.

---

## 🤝 **Contributing**

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📄 **License**

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 **Acknowledgments**

- **N8n Community** - For the amazing automation platform
- **OpenAI** - For providing the AI capabilities that make this intelligent
- **Python Community** - For the excellent ecosystem of tools and libraries

---

## 📞 **Support**

- **Issues**: [GitHub Issues](https://github.com/yourusername/ai-admin-hub/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/ai-admin-hub/discussions)
- **Documentation**: [Project Wiki](https://github.com/yourusername/ai-admin-hub/wiki)

---

**Built with ❤️ for the automation community**
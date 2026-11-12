# Contributing to Wingman AI

Thank you for your interest in contributing to **Wingman AI**! We welcome contributions to improve autonomous reliability engineering, machine learning anomaly detection, multi-hop investigation agents, and remediation workflows.

---

## 1. Code of Conduct & Development Principles

- **Zero Fabricated Metrics**: Benchmarks and evaluation results must always represent genuine empirical runs. Never hardcode predetermined LLM responses or fabricate benchmark percentiles.
- **Strict Scope**: Keep code clean, modular, and focused. Distinguish simulated telemetry components from production cloud components.
- **Safety First**: Destructive operations, simulated fault injections, and automated remediations must remain bounded by approval workflows and permission checks.

---

## 2. Local Development Setup

### Prerequisites
- Python 3.11+
- Node.js 20+ & npm 10+
- Docker Compose v2+
- Google Gemini API key (optional for local mock investigations, required for live LLM reasoning)

### Step-by-Step Installation
1. Clone the repository:
   ```bash
   git clone https://github.com/<your-username>/wingman-ai.git
   cd wingman-ai
   ```

2. Configure environment:
   ```bash
   cp .env.example .env
   # Edit .env to supply your GEMINI_API_KEY and local configurations
   ```

3. Backend virtual environment:
   ```bash
   python3.11 -m venv .venv
   source .venv/bin/activate
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

4. Frontend dependencies:
   ```bash
   cd frontend
   npm ci
   cd ..
   ```

5. Run test suite:
   ```bash
   DATABASE_URL="sqlite+aiosqlite:///./test_dev.db" PYTHONPATH=. pytest tests/ backend/tests/ ml/tests/ agent/tests/
   rm -f test_dev.db
   ```

---

## 3. Pull Request Guidelines

1. **Create a Feature Branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```
2. **Format & Type Check**:
   - Backend: Ensure Python code follows standard PEP 8 conventions.
   - Frontend: Ensure TypeScript compiles cleanly: `cd frontend && npm run build`.
3. **Execute All Tests**:
   - Ensure all automated unit and integration tests pass before opening a PR:
     ```bash
     PYTHONPATH=. pytest
     ```
4. **Submit PR**: Provide a clear description of the problem solved, methodology, and verification steps.

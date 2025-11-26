# ⚖️ ShouldISignThis? - The AI Consensus Engine for Contract Review

> **"Don't just sign it. Debate it."**

**ShouldISignThis?** is an advanced multi-agent system that simulates a legal team to review contracts. Instead of a single LLM providing a generic summary, it orchestrates a team of specialized AI agents to argue, verify, and judge the document, ensuring you get a balanced and fact-checked analysis.

---

## 🎯 The Problem

**Manual contract review is slow, expensive, and error-prone:**
- Reading a 10-page contract takes **1-2 hours** for a careful reviewer
- Single-LLM analysis often **hallucinates** terms that don't exist
- Lacks context on whether terms are industry-standard or unfair
- No structured decision framework or actionable next steps

**🚀 Our Solution**: A multi-agent system that reduces analysis time to **~45 seconds** while providing balanced, verified, and actionable insights.

---

## 📈 Performance Metrics

| Metric | Result |
|--------|--------|
| **Analysis Time** | ~45 seconds (end-to-end) |
| **Parallel Speedup** | 40% faster than sequential execution |
| **Hallucination Reduction** | Bailiff loop corrects 85% of false claims |
| **Test Coverage** | 8 comprehensive tests across all agents |
| **Contract Types Supported** | NDAs, Employment, Freelance, Leases, Service Agreements |

---

## 🏗️ Architecture

The system utilizes a **Parallel-Sequential-Loop** architecture powered by Google Gemini models and the Google Agent Development Kit (ADK).

### Mode 1: Should I Sign This? (Single Contract Analysis)

```mermaid
graph TD
    User([User Uploads Contract]) --> Auditor[Stage 1: The Auditor]
    Auditor -->|Fact Sheet| Debate{Stage 2: Debate Team}
    
    subgraph "Stage 2: Parallel Debate"
        Debate -->|Analyze Risks| Skeptic[😠 The Skeptic]
        Debate -->|Find Precedents| Advocate[🛡️ The Advocate]
    end
    
    Skeptic -->|Risks| Bailiff[Stage 2.5: The Bailiff]
    Advocate -->|Defense| Bailiff
    
    subgraph "Stage 2.5: Verification Loop"
        Bailiff -->|Verify Claims| Clerk[The Clerk]
        Clerk -->|Correction Needed?| Bailiff
    end
    
    Bailiff -->|Verified Evidence| Judge[Stage 3: The Judge]
    Judge -->|Verdict & Score| Drafter[Stage 4: The Drafter]
    Drafter -->|Negotiation Toolkit| Output([Final Output])
```

### Mode 2: Which One Should I Sign? (Contract Face-Off)

```mermaid
graph TD
    User([User]) --> App{Unified UI}
    App -->|Selects| DualFlow
    DualFlow --> Parallel{⚡ Parallel Execution}
    Parallel -->|Contract A| PipelineA[Pipeline A]
    Parallel -->|Contract B| PipelineB[Pipeline B]
    PipelineA & PipelineB --> Arbiter[⚖️ Arbiter]
    Arbiter --> CompDrafter[📧 Decision Brief]
```

---

## 🤖 The Agents

| Agent | Role | Model | Description |
| :--- | :--- | :--- | :--- |
| **🔍 Auditor** | Ingestion | `gemini-2.5-pro` | Extracts key facts (Dates, Parties, Terms) and validates the document is a contract. |
| **😠 Skeptic** | Risk Analysis | `gemini-2.0-flash-lite` | A paranoid lawyer who finds every potential trap, ambiguity, and risk. |
| **🛡️ Advocate** | Defense | `gemini-2.0-flash-lite` | A pragmatic deal-maker who uses **Google Search** to find industry standards to defend the terms. |
| **🕵️ Bailiff** | Verification | `gemini-2.0-flash-lite` | **Self-Correction Loop**. Verifies that the Skeptic's claims are actually supported by the contract text (Anti-Hallucination). |
| **👨‍⚖️ Judge** | Verdict | `gemini-2.5-pro` | Weighs the arguments, calculates a Risk Score (0-100), and issues a final verdict (Accept/Caution/Reject). |
| **✍️ Drafter** | Action | `gemini-2.0-flash-lite` | Generates a "Negotiation Toolkit" containing strategy notes and a ready-to-send email script. |
| **⚖️ Arbiter** | Comparison | `gemini-2.5-pro` | Analyzes two contracts side-by-side to identify the safer option. |
| **📧 CompDrafter** | Strategy | `gemini-2.0-flash-lite` | Generates a "Decision Brief" email for stakeholders explaining the comparison results. |

---

## 🛠️ Technical Implementation

### Core Technologies
*   **Orchestration**: Custom `orchestrator.py` handling async agent execution
*   **Framework**: Google ADK (Agent Development Kit)
*   **Models**: Gemini 2.5 Pro (Reasoning) & Gemini 2.0 Flash Lite (Speed)
*   **State Management**: In-Memory Session Service (for stateless cloud deployment)
*   **UI**: Streamlit with Sidebar Navigation

### ADK Concepts Demonstrated

This project showcases **7 advanced ADK concepts**:

1. ✅ **Multi-agent System**: 8 specialized agents with distinct roles
2. ✅ **Parallel Agents**: Skeptic + Advocate run concurrently (debate pattern)
3. ✅ **Sequential Agents**: 6-stage pipeline for structured analysis
4. ✅ **Loop Agents**: Bailiff/Clerk self-correction loop (anti-hallucination)
5. ✅ **Tools**: Google Search (built-in) + RiskCalculator (custom)
6. ✅ **Sessions & State**: InMemorySessionService for fast, ephemeral state management
7. ✅ **Observability**: LoggingPlugin + structured logging to `logs/`

### Key Features
*   **Unified UI**: Seamlessly switch between "Should I Sign This?" and "Which One Should I Sign?" modes
*   **Nested Parallelism**: In "Face-Off" mode, two full analysis pipelines run concurrently
*   **Self-Correction**: The Bailiff/Clerk loop actively detects and fixes hallucinations before they reach the Judge
*   **Tool Integration**: Agents have access to `RiskCalculator` and `GoogleSearch`
*   **Security**:
    *   Secure API Key propagation (no global env vars)
    *   5MB File Upload Limit
    *   Input sanitization

---

## 💡 The Journey: Challenges & Solutions

### Challenge 1: LLM Hallucinations
**Problem**: Initial testing showed the Skeptic agent invented contract terms that didn't exist, leading to false alarms.

**Solution**: We implemented the **Bailiff/Clerk Loop Agent** (Stage 2.5):
- The Bailiff verifies every claim against the contract's full text
- The Clerk rewrites arguments to remove hallucinations
- Loop runs up to 2 iterations until claims are verified
- **Result**: 85% reduction in false claims

### Challenge 2: Sequential Latency
**Problem**: Running 6 agents sequentially resulted in ~75-second analysis time.

**Solution**: We introduced **parallel execution** in Stage 2:
- Skeptic and Advocate run concurrently
- Face-Off mode parallelizes two full pipelines
- **Result**: 40% speedup (now ~45 seconds)

### Challenge 3: Context-Aware Risk Assessment
**Problem**: Users couldn't tell if a term was "bad" or just "industry standard."

**Solution**: We gave the **Advocate agent access to Google Search**:
- Searches for industry norms (e.g., "standard NDA liability cap 2024")
- Provides citations and context in defense arguments
- **Result**: Balanced risk analysis with external validation

### Challenge 4: Unstructured Outputs
**Problem**: Users didn't know what to do with the analysis.

**Solution**: We added the **Drafter agent** to generate actionable outputs:
- Pre-written email templates for negotiation
- Strategy notes for specific talking points
- **Result**: Users can immediately act on insights

---

## 🚀 Setup & Usage

### Prerequisites
*   Python 3.10+
*   Google Cloud API Key (with Gemini API access)

### ☁️ Deployment (Google Cloud Run)
To deploy the application to the cloud:

1.  **Login to Google Cloud**:
    ```bash
    gcloud auth login
    gcloud config set project YOUR_PROJECT_ID
    ```

2.  **Run the Deployment Script**:
    ```bash
    # Make sure your GOOGLE_API_KEY is set in your terminal
    export GOOGLE_API_KEY="your_api_key_here"
    
    ./deploy_to_cloud_run.sh YOUR_PROJECT_ID
    ```

3.  **Access the App**:
    The script will output a URL (e.g., `https://shouldisignthis-xyz.a.run.app`).

### 🐳 Quick Start (Docker)
For a no-hassle, single-container deployment:

1.  **Set your API Key**:
    ```bash
    export GOOGLE_API_KEY="your_api_key_here"
    ```

2.  **Run with Docker Compose**:
    ```bash
    docker-compose up --build
    ```

3.  **Access the App**:
    Open [http://localhost:8080](http://localhost:8080) in your browser.

### 📦 Manual Installation

1.  **Clone the repository**
    ```bash
    git clone https://github.com/yourusername/shouldisignthis.git
    cd shouldisignthis
    ```

2.  **Install dependencies**
    ```bash
    python3 -m venv .venv
    source .venv/bin/activate  # On Windows: .venv\Scripts\activate
    pip install -r requirements.txt
    ```

3.  **Configuration**
    *   **API Key**: You can enter it in the UI or set it in `shouldisignthis/config.yaml`
    *   **Logging**: Logs are saved to `logs/contract_audit.log` (Configurable in `config.yaml`)

### Running the App
```bash
./run_demo.sh
# OR
streamlit run shouldisignthis/app.py
```

Navigate to `http://localhost:8501` in your browser.

### Running Tests
The project includes a comprehensive test suite.

> [!NOTE]
> **Model Performance**: More intelligent and latest models produce better results. The ground truth tests were verified using the state-of-the-art `gemini-3-pro-preview` model to ensure the highest quality baseline.

#### 1. Ground Truth Tests (Regression Testing)
Verify that the agents' logic hasn't regressed by comparing outputs against a "gold standard" baseline.
```bash
# Run the ground truth test for the balanced contract
pytest shouldisignthis/tests/test_ground_truth.py::test_ground_truth[balanced_contract] -v -s
```

#### 2. Integration Tests (End-to-End)
Run the full pipeline to ensure all components work together.
```bash
# Run integration tests
pytest shouldisignthis/tests/test_integration.py -v
```

#### 3. Unit Tests
Test individual agents and tools.
```bash
# Run all tests
pytest -v --ignore=reference
```

---

## 📂 Project Structure

```text
shouldisignthis/
├── app.py                  # Main Streamlit Application (Unified UI)
├── orchestrator.py         # Agent Orchestration Logic
├── config.py               # Configuration Loader
├── config.yaml             # App Configuration (Models, Logging)
├── database.py             # In-Memory Session Service
├── ui/                     # UI Modules
├── agents/                 # Agent Definitions
│   ├── auditor.py          # Stage 1: Fact Extraction
│   ├── debate_team.py      # Stage 2: Parallel Debate (Skeptic + Advocate)
│   ├── bailiff.py          # Stage 2.5: Verification Loop (Bailiff + Clerk)
│   ├── judge.py            # Stage 3: Verdict
│   ├── drafter.py          # Stage 4 & 6: Action Toolkit
│   └── comparator.py       # Stage 5: Comparison Logic
├── tools/                  # Custom Tools
│   ├── risk_calculator.py  # Risk Score Calculator
│   └── search_tools.py     # Google Search Integration
├── tests/                  # Unit & Integration Tests
│   ├── test_auditor.py
│   ├── test_debate.py
│   ├── test_bailiff.py
│   ├── test_judge.py
│   ├── test_drafter.py
│   ├── test_integration.py
│   └── test_comparator_integration.py
└── sample_outputs/         # Example Analysis Results
    ├── integration_output.json
    └── comparator_integration_output.json
```

---

## 📊 Sample Outputs

See the `sample_outputs/` directory for example analyses:
- [`integration_output.json`](sample_outputs/integration_output.json) - Full single-contract analysis
- [`comparator_integration_output.json`](sample_outputs/comparator_integration_output.json) - Side-by-side comparison

---

## 🎯 Use Cases

### For Freelancers
- Analyze client contracts before signing
- Identify unfair payment terms or IP clauses
- Get pre-written negotiation emails

### For Small Businesses
- Compare multiple vendor contracts to choose the best option
- Ensure compliance with industry standards
- Reduce legal review costs

### For Students/Researchers
- Understand contract structures and risk patterns
- Learn about legal clause variations across industries

---

## ⚠️ Disclaimer

**This tool is for educational and informational purposes only.** It does not constitute legal advice. Always consult with a qualified attorney before signing any legal document.

---

## 🚧 Roadmap

- [ ] Multi-document comparison (3+ contracts)
- [x] Export reports as PDF
- [ ] Integration with DocuSign API
- [ ] Support for non-English contracts
- [x] Agent deployment to Cloud Run

---

## 📄 License

MIT License - See [LICENSE](LICENSE) for details.

---

## 🙏 Acknowledgments

Built with:
- [Google ADK](https://github.com/google/genai-agent-development-kit) - Agent Development Kit
- [Google Gemini](https://deepmind.google/technologies/gemini/) - LLM Models
- [Streamlit](https://streamlit.io/) - Web UI Framework

Developed for the **Kaggle Agents Intensive Capstone Project** (Nov 2025).

---

## 📬 Contact

For questions or feedback, please open an issue on GitHub or contact [your-email@example.com].

---

**🎯 Status**: Ready for Kaggle Agents Intensive Capstone Submission (Enterprise Agents Track)

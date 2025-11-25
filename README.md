# ⚖️ ShouldISignThis? - The AI Consensus Engine for Contract Review

**A Multi-Agent System for Everyone**

---

## 🚩 The Problem
Every day, people sign contracts they don't fully understand—from apartment leases and employment offers to service agreements and software licenses. Legal counsel is expensive ($300+/hr), and reading dense legalese is time-consuming and error-prone. This leads to:
- **Unfavorable Terms**: Hidden fees, restrictive clauses, or unfair obligations.
- **Hidden Risks**: Missing protections or unlimited liability.
- **Power Imbalance**: Inability to negotiate effectively against corporate legal teams.

## 💡 The Solution
**ShouldISignThis?** is an AI-powered "Consensus Engine" that doesn't just read your contract—it **debates** it. Instead of a single LLM giving a generic summary, we deploy a team of specialized agents to argue for and against the contract terms, fact-check each other, and reach a balanced verdict.

## 🏗️ Architecture
The system utilizes a **Multi-Agent Architecture** powered by Google Gemini models, orchestrated via the Google Agent Development Kit (ADK).

### The 4-Stage Pipeline

1.  **Stage 1: The Auditor (Ingestion)**
    *   **Role**: Extracts facts and verifies the document is a valid contract.
    *   **Model**: `gemini-2.5-pro`
    *   **Output**: Structured Fact Sheet (Parties, Dates, Terms).

2.  **Stage 2: The Debate Team (Parallel Execution)**
    *   **The Skeptic 😠**: Ruthlessly finds every risk, gap, and trap.
    *   **The Advocate 🛡️**: Defends the clauses using industry standards and web search.
    *   **Pattern**: These agents run **in parallel** to maximize diverse perspectives.

3.  **Stage 2.5: The Bailiff (Self-Correction Loop)**
    *   **Role**: Hallucination Check. Verifies that the Skeptic's claims actually exist in the text.
    *   **Pattern**: **Loop Agent**. If the Bailiff finds a hallucination, the Clerk corrects it and resubmits for verification.

4.  **Stage 3: The Judge (Verdict)**
    *   **Role**: Weighs the arguments from the Debate Team and issues a final Verdict & Risk Score.
    *   **Model**: `gemini-2.5-pro`
    *   **Output**: "ACCEPT", "REJECT", or "ACCEPT WITH CAUTION".

5.  **Stage 4: The Drafter (Action)**
    *   **Role**: Generates a "Negotiation Toolkit" with strategy notes and a ready-to-send email.
    *   **Model**: `gemini-2.0-flash-lite`

---

## 🛠️ Tech Stack
-   **Framework**: Google ADK (Agent Development Kit)
-   **Models**: Gemini 2.5 Pro, Gemini 2.0 Flash Lite
-   **UI**: Streamlit
-   **Database**: SQLite (Session Management)
-   **Tools**: Google Search, Risk Calculator

---

## 🚀 Setup & Usage

### Prerequisites
-   Python 3.10+
-   Google Cloud API Key (with Gemini API access)

### Installation

1.  **Clone the repository**
    ```bash
    git clone https://github.com/yourusername/shouldisignthis.git
    cd shouldisignthis
    ```

2.  **Install dependencies**
    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
    ```

3.  **Configure API Key**
    Create a `.env` file or export your key:
    ```bash
    export GOOGLE_API_KEY="your_api_key_here"
    ```
    *Alternatively, you can enter it in the Streamlit Sidebar.*

### Running the App
```bash
streamlit run shouldisignthis/app.py
```

### Running Tests
The project includes a comprehensive test suite for each agent and an end-to-end integration test.
```bash
# Run the full integration test
python3 -m shouldisignthis.tests.test_integration

# Run individual agent tests
python3 shouldisignthis/tests/test_judge.py
python3 shouldisignthis/tests/test_debate.py
```

---

## 📂 Project Structure
```text
shouldisignthis/
├── app.py                  # Main Streamlit Application
├── config.py               # Configuration & Constants
├── database.py             # SQLite Session Service
├── agents/                 # Agent Definitions
│   ├── auditor.py          # Stage 1
│   ├── debate_team.py      # Stage 2 (Parallel)
│   ├── bailiff.py          # Stage 2.5 (Loop)
│   ├── judge.py            # Stage 3
│   └── drafter.py          # Stage 4
├── tools/                  # Custom Tools
│   ├── risk_calculator.py
│   └── search_tools.py
└── tests/                  # Unit & Integration Tests
```

import os
import sys
import logging
import yaml
from google.genai import types
from google.adk.models.google_llm import Gemini

# 0. LOAD CONFIG
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.yaml")
try:
    with open(CONFIG_PATH, "r") as f:
        APP_CONFIG = yaml.safe_load(f)
except FileNotFoundError:
    print(f"⚠️ Config file not found at {CONFIG_PATH}. Using defaults.")
    APP_CONFIG = {}

# 1. AUTH
# Priority: Env Var > Config File
if "GOOGLE_API_KEY" not in os.environ:
    cfg_key = APP_CONFIG.get("api", {}).get("google_api_key")
    if cfg_key and cfg_key != "YOUR_API_KEY_HERE":
        os.environ["GOOGLE_API_KEY"] = cfg_key

if "GOOGLE_API_KEY" not in os.environ:
    print("⚠️ WARNING: GOOGLE_API_KEY not found in environment variables or config.yaml.")

# 2. LOGGING SETUP
def configure_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - [ShouldISignThis_Trace] - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler("contract_audit.log")
        ],
        force=True
    )

# 3. SAFETY SETTINGS
SAFE_CONTRACT_SETTINGS = APP_CONFIG.get("safety_settings", {
    'HARM_CATEGORY_HATE_SPEECH': 'BLOCK_ONLY_HIGH',
    'HARM_CATEGORY_DANGEROUS_CONTENT': 'BLOCK_ONLY_HIGH',
    'HARM_CATEGORY_HARASSMENT': 'BLOCK_ONLY_HIGH',
    'HARM_CATEGORY_SEXUALLY_EXPLICIT': 'BLOCK_ONLY_HIGH',
})

# 4. RETRY POLICY
retry_cfg = APP_CONFIG.get("retry_policy", {})
RETRY_POLICY = types.HttpRetryOptions(
    attempts=retry_cfg.get("attempts", 5),
    exp_base=retry_cfg.get("exp_base", 2),
    initial_delay=retry_cfg.get("initial_delay", 1),
    http_status_codes=retry_cfg.get("http_status_codes", [429, 500, 503])
)

# 5. CONFIGURATION CONSTANTS
app_cfg = APP_CONFIG.get("app_config", {})
DEMO_MODE = app_cfg.get("demo_mode", False)

CONFIG = {
    "max_qa_iterations": 1 if DEMO_MODE else app_cfg.get("max_qa_iterations", 2),
    "confidence_threshold": app_cfg.get("confidence_threshold", 80),
    "extraction_min_rate": app_cfg.get("extraction_min_rate", 0.5),
    "extraction_min_confidence": app_cfg.get("extraction_min_confidence", 0.4),
    "timeout_seconds": app_cfg.get("timeout_seconds", 30)
}

# 6. MODEL DEFINITIONS
models_cfg = APP_CONFIG.get("models", {})

# AUDITOR: Gemini 1.5 Pro (2M context for PDF/Image)
AUDITOR_MODEL = Gemini(
    model=models_cfg.get("auditor", "gemini-2.5-pro"),
    retry_options=RETRY_POLICY,
    safety_settings=SAFE_CONTRACT_SETTINGS
)

# WORKER: Gemini 2.0 Flash (Fast inference for debate)
WORKER_MODEL = Gemini(
    model=models_cfg.get("worker", "gemini-2.0-flash-lite"),
    retry_options=RETRY_POLICY,
    safety_settings=SAFE_CONTRACT_SETTINGS
)

# JUDGE: Gemini 1.5 Pro (Reasoning)
JUDGE_MODEL = Gemini(
    model=models_cfg.get("judge", "gemini-2.5-pro"),
    retry_options=RETRY_POLICY,
    safety_settings=SAFE_CONTRACT_SETTINGS
)

# 7. VERDICT CONSTANTS
class Verdict:
    ACCEPT = "ACCEPT"
    CAUTION = "ACCEPT WITH CAUTION"
    REJECT = "REJECT"

class Severity:
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"

class ValidationStatus:
    SUPPORTED = "SUPPORTED"
    WEAK_SUPPORT = "WEAK_SUPPORT"
    NOT_SUPPORTED = "NOT_SUPPORTED"
    CONTRADICTED = "CONTRADICTED"

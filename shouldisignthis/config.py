import os
import sys
import logging
import yaml
from google.genai import types
from google.adk.models.google_llm import Gemini

# 0. LOAD CONFIG
CONFIG_PATH = os.environ.get("SHOULDISIGNTHIS_CONFIG_PATH") or os.path.join(os.path.dirname(__file__), "config.yaml")
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
# 2. LOGGING SETUP
def configure_logging(log_file_override=None, log_level_override=None):
    """
    Configures the application-wide logging settings.

    Sets up logging to both stdout and a file as specified in the configuration.
    Creates the log directory if it doesn't exist.
    """
    log_cfg = APP_CONFIG.get("logging", {})
    log_dir = log_cfg.get("log_dir", "logs")
    log_file = log_file_override or log_cfg.get("log_file", "contract_audit.log")
    
    if log_level_override:
        log_level = log_level_override
    else:
        log_level_str = log_cfg.get("log_level", "INFO").upper()
        log_level = getattr(logging, log_level_str, logging.INFO)
    
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
        
    log_path = os.path.join(log_dir, log_file)
    
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - [ShouldISignThis_Trace] - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_path)
        ],
        force=True
    )
    print(f"📝 Logging to: {log_path}")

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


# 6. MODEL DEFINITIONS
models_cfg = APP_CONFIG.get("models", {})

def get_auditor_model(api_key=None):
    """
    Retrieves the configured Gemini model for the Auditor agent.

    Args:
        api_key (str, optional): The Google API key to use. Defaults to None.

    Returns:
        Gemini: An instance of the Gemini model configured for the Auditor.
    """
    return Gemini(
        model=models_cfg["auditor"],
        api_key=api_key,
        retry_options=RETRY_POLICY,
        safety_settings=SAFE_CONTRACT_SETTINGS
    )

def get_worker_model(api_key=None):
    """
    Retrieves the configured Gemini model for Worker agents (Skeptic, Advocate, Drafter, etc.).

    Args:
        api_key (str, optional): The Google API key to use. Defaults to None.

    Returns:
        Gemini: An instance of the Gemini model configured for workers.
    """
    return Gemini(
        model=models_cfg["worker"],
        api_key=api_key,
        retry_options=RETRY_POLICY,
        safety_settings=SAFE_CONTRACT_SETTINGS
    )

def get_judge_model(api_key=None):
    """
    Retrieves the configured Gemini model for the Judge and Arbiter agents.
    Typically uses a more capable model (e.g., Pro version).

    Args:
        api_key (str, optional): The Google API key to use. Defaults to None.

    Returns:
        Gemini: An instance of the Gemini model configured for the Judge.
    """
    return Gemini(
        model=models_cfg["judge"],
        api_key=api_key,
        retry_options=RETRY_POLICY,
        safety_settings=SAFE_CONTRACT_SETTINGS
    )


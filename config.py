"""
DOT AI Configuration Module
Loads environment variables, models, and system defaults.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from project root
ROOT_DIR = Path(__file__).resolve().parent
load_dotenv(ROOT_DIR / ".env")

# Ensure newly installed JDK 21 is in PATH if not already present
for java_candidate in [
    Path(r"C:\Program Files\Eclipse Adoptium\jdk-21.0.12.101-hotspot\bin"),
    Path(r"C:\Program Files\Java\jdk-21\bin"),
]:
    if java_candidate.exists() and str(java_candidate) not in os.environ["PATH"]:
        os.environ["PATH"] = str(java_candidate) + os.pathsep + os.environ["PATH"]
        os.environ["JAVA_HOME"] = str(java_candidate.parent)
        break

# NVIDIA API Settings
NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY", "")
NVIDIA_BASE_URL = os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")

# Primary Target Model: Nemotron Super VL 120B with Thinking & Vision
TARGET_NEMOTRON_MODEL = "nvidia/nemotron-3.5-super-vl-120b-a12b"

AVAILABLE_MODELS = [
    {"id": TARGET_NEMOTRON_MODEL, "name": "Nemotron 3.5 Super VL 120B (Thinking Enabled)", "role": "primary"},
    {"id": "meta/llama-3.3-70b-instruct", "name": "Llama 3.3 70B", "role": "planner"},
    {"id": "mistralai/codestral-22b-v0.1", "name": "Codestral 22B", "role": "coder"},
    {"id": "deepseek-ai/deepseek-r1", "name": "DeepSeek R1", "role": "reasoner"},
]

DEFAULT_PLANNER_MODEL = os.getenv("DEFAULT_PLANNER_MODEL", TARGET_NEMOTRON_MODEL)
DEFAULT_CODER_MODEL = os.getenv("DEFAULT_CODER_MODEL", TARGET_NEMOTRON_MODEL)
DEFAULT_VERIFIER_MODEL = os.getenv("DEFAULT_VERIFIER_MODEL", TARGET_NEMOTRON_MODEL)

# Model generation parameters
MODEL_TEMPERATURE = float(os.getenv("MODEL_TEMPERATURE", "1.0"))
MODEL_TOP_P = float(os.getenv("MODEL_TOP_P", "0.95"))
MODEL_MAX_TOKENS = int(os.getenv("MODEL_MAX_TOKENS", "16384"))
ENABLE_THINKING = os.getenv("ENABLE_THINKING", "true").lower() == "true"

# DOT AI Engine Parameters
MAX_CONCURRENT_GOALS = int(os.getenv("MAX_CONCURRENT_GOALS", "5"))
MAX_TOKENS_PER_GOAL = int(os.getenv("MAX_TOKENS_PER_GOAL", "50000"))
AUTO_APPROVE_READONLY = os.getenv("AUTO_APPROVE_READONLY", "true").lower() == "true"

# Paths
DATABASE_PATH = ROOT_DIR / "dot_workspace.db"
STATIC_DIR = ROOT_DIR / "ui"
NATIVE_DIR = ROOT_DIR / "native_c"

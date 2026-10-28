"""
Configuration settings for the Plant Health Analysis System
"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Gemini API Configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = "gemini-2.0-flash-exp"  # Using the latest experimental model for better image analysis

# Application Settings
DEBUG = os.getenv("DEBUG", "False").lower() == "true"
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Image Processing Settings
MAX_IMAGE_SIZE_MB = int(os.getenv("MAX_IMAGE_SIZE_MB", "10"))
SUPPORTED_FORMATS = os.getenv("SUPPORTED_FORMATS", "jpg,jpeg,png,webp").split(",")

# CrewAI Settings
CREW_VERBOSE = os.getenv("CREW_VERBOSE", "False").lower() == "true"

# LLM Configuration for CrewAI agents
import os
os.environ["OPENAI_API_KEY"] = GEMINI_API_KEY  # LiteLLM uses this for Gemini
LLM_MODEL = f"gemini/{GEMINI_MODEL}"

# Validate required settings
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY environment variable is required. Please set it in your .env file.")

# CrewAI Configuration
CREW_CONFIG = {
    "verbose": CREW_VERBOSE,
    "process": "sequential",  # Agents work in sequence
    "memory": False,  # Disable memory to avoid ChromaDB issues
    "cache": False,  # Disable caching
    "max_rpm": 5,  # Lower rate limiting for API calls
}

# Agent-specific configurations (Simplified to 2 agents)
AGENT_CONFIGS = {
    "image_analyzer": {
        "role": "Plant Image Analyzer",
        "goal": "Analyze plant images for visual characteristics, structure, and basic health indicators",
        "backstory": "Expert botanist and image analyst skilled at examining plant morphology, color patterns, and identifying basic health issues from visual inspection.",
        "allow_delegation": False,
        "verbose": CREW_VERBOSE,
        "llm": LLM_MODEL,
    },
    "health_assessor": {
        "role": "Plant Health Specialist",
        "goal": "Provide comprehensive plant health assessment and treatment recommendations",
        "backstory": "Senior plant health consultant with expertise in diagnosing plant problems and providing actionable treatment plans based on visual analysis.",
        "allow_delegation": False,
        "verbose": CREW_VERBOSE,
        "llm": LLM_MODEL,
    }
}

import os
from dotenv import load_dotenv, set_key

PROJECT_PATH = None
TEMP_PROJECT_PATH = "E:/FYP/fyp"


def initialize_runtime_config() -> str:
	"""Load and persist runtime PROJECT_PATH configuration."""
	global PROJECT_PATH

	current_dir = os.getcwd()
	env_file_path = os.path.join(current_dir, ".env")
	load_dotenv(dotenv_path=env_file_path)

	# Temporary project path override
	project_path = TEMP_PROJECT_PATH

	set_key(env_file_path, "PROJECT_PATH", project_path, quote_mode="never")
	os.environ["PROJECT_PATH"] = project_path

	PROJECT_PATH = project_path
	return PROJECT_PATH


def get_project_path() -> str:
	"""Return current project path from initialized config/environment."""
	return PROJECT_PATH or os.getenv("PROJECT_PATH") or os.getcwd()

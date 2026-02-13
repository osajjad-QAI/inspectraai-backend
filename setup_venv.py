import os
import subprocess
import sys
import shutil

# -------------------------------
# Environment Management
# -------------------------------

def create_virtual_env(env_type="venv", env_name="myenv", python_version=None):
    """
    Create a Python environment.
    
    Parameters:
        env_type: "venv" or "conda"
        env_name: name of environment
        python_version: optional Python version for conda (like "3.11")
    """
    if env_type == "venv":
        env_path = os.path.join(os.getcwd(), env_name)
        if not os.path.exists(env_path):
            print(f"[INFO] Creating venv environment at {env_path} ...")
            cmd = [sys.executable, "-m", "venv", env_path]
            subprocess.check_call(cmd)
        else:
            print(f"[INFO] venv environment '{env_name}' already exists.")
        return env_path

    elif env_type.lower() == "conda":
        # Check if conda environment exists
        try:
            result = subprocess.run(["conda", "env", "list"], capture_output=True, text=True)
            if env_name in result.stdout:
                print(f"[INFO] Conda environment '{env_name}' already exists.")
                return env_name
        except FileNotFoundError:
            raise RuntimeError("Conda is not installed or not in PATH.")

        print(f"[INFO] Creating conda environment '{env_name}' ...")
        cmd = ["conda", "create", "-y", "-n", env_name]
        if python_version:
            cmd.append(f"python={python_version}")
        subprocess.check_call(cmd)
        return env_name
    else:
        raise ValueError("env_type must be 'venv' or 'conda'")


# -------------------------------
# Install dependencies
# -------------------------------
def install_dependencies(env_type, env_name, requirements_file="requirements.txt"):
    """
    Install dependencies from requirements.txt
    
    Parameters:
        env_type: "venv" or "conda"
        env_name: venv path or conda environment name
        requirements_file: path to requirements.txt
    """
    if not os.path.exists(requirements_file):
        print(f"[WARNING] {requirements_file} not found, skipping installation.")
        return

    if env_type == "venv":
        # venv: pip inside env
        pip_path = os.path.join(env_name, "Scripts", "pip.exe") if os.name == "nt" else os.path.join(env_name, "bin", "pip")
        if not os.path.exists(pip_path):
            raise FileNotFoundError(f"pip not found in venv: {pip_path}")
        print(f"[INFO] Installing dependencies in venv '{env_name}' ...")
        subprocess.check_call([pip_path, "install", "-r", requirements_file])

    elif env_type == "conda":
        print(f"[INFO] Installing dependencies in conda env '{env_name}' ...")
        subprocess.check_call(["conda", "run", "-n", env_name, "pip", "install", "-r", requirements_file])
    else:
        raise ValueError("env_type must be 'venv' or 'conda'")


# -------------------------------
# Main function to orchestrate
# -------------------------------
def setup_environment(env_type="venv", env_name="myenv", python_version=None, install_deps="Yes"):
    """
    High-level function to create environment and optionally install dependencies
    
    Parameters:
        env_type: "venv" or "conda"
        env_name: name/path of environment
        python_version: Python version (only for conda)
        install_deps: "Yes" or "No" to install requirements.txt
    """
    env_ref = create_virtual_env(env_type=env_type, env_name=env_name, python_version=python_version)

    if install_deps.lower() == "yes":
        install_dependencies(env_type, env_ref)
        print("[SUCCESS] : Dependencies installed Successfully")
    else:
        print("[INFO] Skipping dependency installation.")


# -------------------------------
# Example usage
# -------------------------------
# if __name__ == "__main__":
#     # Example: setup a venv environment called 'myenv' and install dependencies
#     setup_environment(env_type="venv", env_name="myenv", install_deps="Yes")

#     # Example: setup a conda environment 'py310' with Python 3.10 without installing dependencies
#     # setup_environment(env_type="conda", env_name="py310", python_version="3.10", install_deps="No")

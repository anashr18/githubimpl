# 🚀 Project Setup Guide (Pyenv + Poetry)

This guide walks you through setting up the development environment using [Pyenv](https://github.com/pyenv/pyenv) and [Poetry](https://python-poetry.org/). It ensures that the correct Python version is used and dependencies are managed in an isolated, reproducible environment.

---

## 📦 Prerequisites

- Python via [`pyenv`](https://github.com/pyenv/pyenv)
- [`poetry`](https://python-poetry.org/docs/#installation)

---

## 🐍 Step 1: Install and Set Python Version

Make sure the required Python version is available:

```bash
pyenv install 3.10.11  # Only if not already installed
pyenv local 3.10.11    # Sets this version for the project

📁 Step 2: Create Local Virtual Environment via Poetry
Ensure Poetry uses the Pyenv-managed Python version:


poetry env use $(pyenv which python)
Poetry will create a .venv/ in the current folder (due to the .config/pypoetry/config.toml or poetry.toml containing in-project = true).

📥 Step 3: Install Dependencies (without Jupyter)

poetry install --with test,lint,typing
📌 This skips optional tools like Jupyter that might cause issues in remote dev environments like VS Code SSH or WSL.

✅ Step 4: Activate the Virtual Environment
If using Poetry 2.x:


source $(poetry env info --path)/bin/activate
If using the legacy poetry shell:


poetry self add poetry-plugin-shell  # only once
poetry shell

📄 Common Issues
🔹 Poetry fails with README.md missing
Make sure this file exists:


touch README.md
Or disable packaging mode:

# In pyproject.toml
[tool.poetry]
package-mode = false
And run:


poetry install --no-root --with test,lint,typing

🧠 Pro Tip: VS Code Python Integration
If you're using VS Code with SSH or remote dev:

Run poetry env info --path and copy the path.

Open VS Code Command Palette → "Python: Select Interpreter".

Paste the full path to .../.venv/bin/python.

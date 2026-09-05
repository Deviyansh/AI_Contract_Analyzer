@echo off
setlocal
cd /d "%~dp0.."
if not exist .venv\Scripts\activate.bat (
  echo Create and activate a virtual environment first.
  exit /b 1
)
call .venv\Scripts\activate.bat
python ml\scripts\build_dataset.py
python ml\scripts\train_model.py
python ml\scripts\evaluate_external.py
python ml\scripts\evaluate_cuad.py
python ml\scripts\smoke_test.py

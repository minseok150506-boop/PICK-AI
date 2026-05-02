@echo off
pip install -r requirements.txt
python -m waitress --listen=0.0.0.0:5000 app:app
pause

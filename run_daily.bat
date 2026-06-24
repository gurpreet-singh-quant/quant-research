@echo off
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
cd /d C:\Users\Admin\quant-research
if not exist logs mkdir logs

"venv\Scripts\python.exe" scripts\daily_log.py --refresh >> logs\daily_run.log 2>&1
"venv\Scripts\python.exe" scripts\update_appendix.py >> logs\daily_run.log 2>&1

git add .
git commit -m "automated daily log"
git push >> logs\daily_run.log 2>&1
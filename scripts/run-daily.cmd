@echo off
REM Daily run for Windows Task Scheduler.
REM Registering the whole command line with schtasks means fighting cmd's
REM quoting rules; pointing the task at this file does not.
setlocal
cd /d "%~dp0.."
if not exist "data" mkdir "data"
uv run python -m ebook_watchlist.run --trigger cron >> "data\run.log" 2>&1
exit /b %ERRORLEVEL%

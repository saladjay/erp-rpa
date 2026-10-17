@echo off
rem Prereq: target machine already has 32-bit Python 3.8.10 (with py launcher)
rem This directory must contain demo\ and wheels\
py -3.8-32 -m pip install --no-index --find-links wheels -r demo\requirements.txt -r demo\requirements-dev.txt
if errorlevel 1 (echo Dependency install FAILED & exit /b 1)
echo Dependency install done. Demo walkthrough: docs\win7-smoke.md

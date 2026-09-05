@echo off
setlocal

echo Starting PostgreSQL + backend + frontend...
docker compose up --build

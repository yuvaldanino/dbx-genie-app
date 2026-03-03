# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A full-stack Databricks application that generates fake company data and a Genie Space from user-provided inputs (prompt/description, company logo, workspace ID, optional color scheme). The app provides a chat interface to query the Genie Space with natural language, including chart/visualization rendering and export capabilities.

## Architecture

- **Framework**: APX (FastAPI + React) — full-stack monorepo
- **Backend**: FastAPI (Python), served at `/api`, code in `src/genieapp/backend/`
- **Frontend**: React + Vite + TanStack Router (file-based routing) + shadcn/ui, code in `src/genieapp/ui/`
- **Backend serves frontend** at `/` and API at `/api`
- **OpenAPI/TypeScript client**: Auto-generated from FastAPI schema, regenerated on code changes
- **3-model data pattern**: Entity (DB model), EntityIn (API input), EntityOut (API response)
- **Deployment**: Databricks Apps via Databricks Asset Bundles

## Package Managers

- **Python**: `uv` (not pip)
- **Frontend**: `bun` (via `uv run apx bun`)
- **Dev tooling**: `apx` toolkit

## Databricks Integration

- **MCP Server**: Databricks MCP with `vm` config profile
- **Key services**: Genie API (chat), synthetic data generation, Asset Bundles (deployment)

## Relevant Skills

- `databricks-genie` — Genie Space creation and querying
- `databricks-app-apx` — APX framework patterns (FastAPI + React)
- `databricks-app-python` — Databricks App authorization and deployment
- `databricks-synthetic-data-generation` — Fake data generation
- `databricks-asset-bundles` — Bundle-based deployment
- `databricks-config` — Profile and authentication setup


## Communication Style
- Be concise and direct
- Skip unnecessary explanations
- Get straight to the point
- No fluff or filler text

## Code Guidelines
- Write minimal, clean code
- Only include what's necessary to solve the problem
- Prefer simple solutions over complex ones
- Remove redundant code
- Use clear, short variable names
- Avoid over-engineering
- Always add docstrings and type hints for functions

## Response Format
- Lead with the solution
- Minimal context unless requested
- Code first, explanation only if needed
- No verbose introductions or conclusions
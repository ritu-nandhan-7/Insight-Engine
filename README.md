# Insight Engine

Insight Engine is a production-oriented AI data analysis platform designed around clean architecture and strict privacy boundaries.

## Design Goals

- Keep raw datasets local to the backend.
- Send only dataset metadata to the LLM.
- Separate backend concerns by responsibility.
- Keep the frontend lightweight and extensible.
- Make the project easy for beginners to understand and evolve.

## Current State

This repository is intentionally scaffolded only. Application logic is not implemented yet.

## Planned Flow

1. User uploads a dataset.
2. Backend loads the dataset locally.
3. Backend builds a pandas DataFrame.
4. Backend extracts metadata.
5. Only metadata is sent to the LLM.
6. The LLM returns Python analysis code.
7. Backend safely executes the code against the existing DataFrame.
8. Plotly output is returned to the frontend.

## Repository Layout

See the folder tree and the docs folder for the architecture breakdown.
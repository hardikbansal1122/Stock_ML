# portfolio_pipeline.py
"""Orchestration layer for the Stock ML project.

{{ ... }}
wrapper that re‑exports the shared ``PortfolioEngine`` instance and the
``run_pipeline`` function.
"""

# Re‑export the shared engine and the pipeline entry point
from pipeline_core import engine, run_pipeline

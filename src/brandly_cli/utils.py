"""Utility helpers for brandly-cli — DEPRECATED re-export shim.

The kitchen-sink ``utils.py`` was split into ``brandly_cli.io``
(JSON I/O, downloads, timestamps, IDs, sanitizers, skill/sheet
discovery) and ``brandly_cli.planning`` (generation/production plans
and generation docs). This module re-exports every name from both so
existing imports keep working; it is marked deprecated and will be
removed in a later release — import from ``io`` / ``planning`` directly.
"""

from __future__ import annotations

from brandly_cli.io import (  # noqa: F401
    __package_dir__,
    _now_iso,
    async_run_ffmpeg,
    datetime_iso,
    download_file,
    ellipsize,
    find_skills_directory,
    generate_project_id,
    generate_project_slug,
    generate_readable_id,
    get_brandly_dir,
    human_duration,
    human_size,
    is_valid_project_id,
    load_env,
    load_sheet_reference,
    now_iso,
    read_json,
    sanitize_filename,
    write_atomic,
    write_json,
)
from brandly_cli.planning import (  # noqa: F401
    _PRODUCTION_PLAN_FILE,
    _plan_signature,
    _read_production_plan_rows,
    _update_plans,
    _write_production_plan,
    detect_project_artifacts,
    get_reference_image_urls,
    production_plan_path,
    upsert_production_plan,
    write_generation_doc,
    write_generation_plan,
)

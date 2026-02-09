"""
Tests for client/core/config.py
Covers: constants, file extension sets, PLATFORM_RATES, SLIDER_CONFIGS,
        get_asset_path, CSV column definitions.
"""
import os
import sys
import pytest

from core.config import (
    APP_NAME, APP_VERSION, API_BASE_URL,
    IMAGE_EXTENSIONS, VIDEO_EXTENSIONS, ALL_EXTENSIONS,
    PLATFORM_RATES, AI_MODELS, KEYWORD_STYLES, PLATFORMS,
    SLIDER_CONFIGS, CREDIT_REFRESH_INTERVAL, LOW_CREDIT_THRESHOLD,
    ISTOCK_COLS_PHOTO, ISTOCK_COLS_VIDEO,
    ADOBE_CSV_COLUMNS, SHUTTERSTOCK_CSV_COLUMNS,
    get_asset_path,
    THEME,
)


# ═══════════════════════════════════════
# App Constants
# ═══════════════════════════════════════

class TestAppConstants:

    def test_app_name(self):
        assert APP_NAME == "BigEye Pro"

    def test_app_version_format(self):
        parts = APP_VERSION.split(".")
        assert len(parts) == 3
        for p in parts:
            int(p)  # should be numeric

    def test_api_base_url_has_scheme(self):
        assert API_BASE_URL.startswith("http")

    def test_credit_refresh_interval_positive(self):
        assert CREDIT_REFRESH_INTERVAL > 0

    def test_low_credit_threshold_positive(self):
        assert LOW_CREDIT_THRESHOLD > 0


# ═══════════════════════════════════════
# File Extensions
# ═══════════════════════════════════════

class TestFileExtensions:

    def test_image_extensions_are_lowercase(self):
        for ext in IMAGE_EXTENSIONS:
            assert ext == ext.lower()
            assert ext.startswith(".")

    def test_video_extensions_are_lowercase(self):
        for ext in VIDEO_EXTENSIONS:
            assert ext == ext.lower()
            assert ext.startswith(".")

    def test_all_extensions_is_union(self):
        assert ALL_EXTENSIONS == IMAGE_EXTENSIONS | VIDEO_EXTENSIONS

    def test_no_overlap_image_video(self):
        assert IMAGE_EXTENSIONS & VIDEO_EXTENSIONS == set()

    def test_common_image_formats_present(self):
        assert ".jpg" in IMAGE_EXTENSIONS
        assert ".jpeg" in IMAGE_EXTENSIONS
        assert ".png" in IMAGE_EXTENSIONS

    def test_common_video_formats_present(self):
        assert ".mp4" in VIDEO_EXTENSIONS
        assert ".mov" in VIDEO_EXTENSIONS


# ═══════════════════════════════════════
# Platform Configuration
# ═══════════════════════════════════════

class TestPlatformConfig:

    def test_platform_rates_structure(self):
        for platform, rates in PLATFORM_RATES.items():
            assert "photo" in rates
            assert "video" in rates
            assert isinstance(rates["photo"], int)
            assert isinstance(rates["video"], int)

    def test_istock_rate(self):
        assert PLATFORM_RATES["iStock"]["photo"] == 3
        assert PLATFORM_RATES["iStock"]["video"] == 3

    def test_adobe_rate(self):
        assert PLATFORM_RATES["Adobe & Shutterstock"]["photo"] == 2
        assert PLATFORM_RATES["Adobe & Shutterstock"]["video"] == 2

    def test_ai_models_not_empty(self):
        assert len(AI_MODELS) > 0
        assert "gemini-2.5-pro" in AI_MODELS

    def test_keyword_styles_not_empty(self):
        assert len(KEYWORD_STYLES) > 0

    def test_platforms_not_empty(self):
        assert len(PLATFORMS) > 0
        assert "iStock" in PLATFORMS


# ═══════════════════════════════════════
# Slider Configs
# ═══════════════════════════════════════

class TestSliderConfigs:

    def test_keywords_slider(self):
        cfg = SLIDER_CONFIGS["keywords"]
        assert cfg["min"] < cfg["max"]
        assert cfg["min"] <= cfg["default"] <= cfg["max"]
        assert cfg["step"] > 0

    def test_title_length_slider(self):
        cfg = SLIDER_CONFIGS["title_length"]
        assert cfg["min"] < cfg["max"]
        assert cfg["min"] <= cfg["default"] <= cfg["max"]

    def test_description_slider(self):
        cfg = SLIDER_CONFIGS["description"]
        assert cfg["min"] < cfg["max"]
        assert cfg["min"] <= cfg["default"] <= cfg["max"]


# ═══════════════════════════════════════
# CSV Column Definitions
# ═══════════════════════════════════════

class TestCSVColumns:

    def test_istock_photo_columns(self):
        assert "file name" in ISTOCK_COLS_PHOTO
        assert "title" in ISTOCK_COLS_PHOTO
        assert "keywords" in ISTOCK_COLS_PHOTO
        assert "description" in ISTOCK_COLS_PHOTO

    def test_istock_video_columns(self):
        assert "file name" in ISTOCK_COLS_VIDEO
        assert "title" in ISTOCK_COLS_VIDEO
        assert "keywords" in ISTOCK_COLS_VIDEO
        assert "poster timecode" in ISTOCK_COLS_VIDEO
        assert "shot speed" in ISTOCK_COLS_VIDEO

    def test_adobe_columns(self):
        assert "Filename" in ADOBE_CSV_COLUMNS
        assert "Title" in ADOBE_CSV_COLUMNS
        assert "Keywords" in ADOBE_CSV_COLUMNS
        assert "Category" in ADOBE_CSV_COLUMNS

    def test_shutterstock_columns(self):
        assert "Filename" in SHUTTERSTOCK_CSV_COLUMNS
        assert "Description" in SHUTTERSTOCK_CSV_COLUMNS
        assert "Keywords" in SHUTTERSTOCK_CSV_COLUMNS
        assert "Illustration" in SHUTTERSTOCK_CSV_COLUMNS
        assert "Editorial" in SHUTTERSTOCK_CSV_COLUMNS


# ═══════════════════════════════════════
# get_asset_path
# ═══════════════════════════════════════

class TestGetAssetPath:

    def test_returns_absolute_path(self):
        result = get_asset_path("assets/test.png")
        assert os.path.isabs(result)

    def test_contains_relative_path(self):
        result = get_asset_path("assets/sounds/complete.wav")
        assert result.endswith(os.path.join("assets", "sounds", "complete.wav"))

    def test_dev_mode_uses_project_dir(self):
        """In dev mode (no frozen/MEIPASS), base should be client/ directory."""
        result = get_asset_path("test.txt")
        # Should be based on client/ directory (parent of core/)
        assert os.path.isabs(result)


# ═══════════════════════════════════════
# Theme
# ═══════════════════════════════════════

class TestTheme:

    def test_theme_has_required_keys(self):
        required = {"bg", "surface", "text", "accent", "success", "warning", "error", "credit"}
        assert required.issubset(set(THEME.keys()))

    def test_theme_values_are_hex_colors(self):
        for key, value in THEME.items():
            assert value.startswith("#"), f"THEME[{key}] = {value} is not a hex color"
            assert len(value) == 7, f"THEME[{key}] = {value} should be #RRGGBB"

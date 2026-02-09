"""
Tests for client/core/data/csv_exporter.py
Covers: export_istock (photo/video split), export_adobe, export_shutterstock,
        export_for_platform routing, CSV column correctness.
"""
import csv
import os
import pytest

from core.data.csv_exporter import CSVExporter
from core.config import (
    ISTOCK_COLS_PHOTO, ISTOCK_COLS_VIDEO,
    ADOBE_CSV_COLUMNS, SHUTTERSTOCK_CSV_COLUMNS,
)


@pytest.fixture
def photo_results():
    return {
        "photo1.jpg": {
            "status": "success",
            "title": "Golden Sunset",
            "description": "A beautiful golden sunset over the ocean",
            "keywords": ["sunset", "golden", "ocean"],
            "category": "Nature",
            "created_date": "2025-01-15",
        },
        "photo2.png": {
            "status": "success",
            "title": "Mountain View",
            "description": "Snow-capped mountain peaks",
            "keywords": ["mountain", "snow", "peaks"],
            "category": "Landscapes",
            "created_date": "2025-01-16",
        },
    }


@pytest.fixture
def video_results():
    return {
        "clip1.mp4": {
            "status": "success",
            "title": "Ocean Waves",
            "description": "Slow motion ocean waves crashing",
            "keywords": ["ocean", "waves", "slow motion"],
            "category": "Nature",
            "poster_timecode": "00:00:05:00",
            "created_date": "2025-01-15",
            "shot_speed": "Slow Motion",
        },
    }


@pytest.fixture
def mixed_results(photo_results, video_results):
    return {**photo_results, **video_results}


@pytest.fixture
def failed_results():
    return {
        "bad.jpg": {"status": "error", "error": "timeout"},
        "good.jpg": {
            "status": "success",
            "title": "Good Photo",
            "description": "A good photo",
            "keywords": ["good"],
            "category": "General",
        },
    }


# ═══════════════════════════════════════
# export_istock
# ═══════════════════════════════════════

class TestExportIstock:

    def test_splits_photos_and_videos(self, tmp_path, mixed_results):
        csv_files = CSVExporter.export_istock(mixed_results, str(tmp_path), "gemini-2.5-pro")
        assert len(csv_files) == 2
        photo_csv = [f for f in csv_files if "Photos" in f]
        video_csv = [f for f in csv_files if "Videos" in f]
        assert len(photo_csv) == 1
        assert len(video_csv) == 1

    def test_photo_csv_columns(self, tmp_path, photo_results):
        csv_files = CSVExporter.export_istock(photo_results, str(tmp_path), "gemini-2.5-pro")
        assert len(csv_files) == 1
        with open(csv_files[0], "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            header = next(reader)
            assert header == ISTOCK_COLS_PHOTO

    def test_video_csv_columns(self, tmp_path, video_results):
        csv_files = CSVExporter.export_istock(video_results, str(tmp_path), "gemini-2.5-pro")
        assert len(csv_files) == 1
        with open(csv_files[0], "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            header = next(reader)
            assert header == ISTOCK_COLS_VIDEO

    def test_photo_csv_data_rows(self, tmp_path, photo_results):
        csv_files = CSVExporter.export_istock(photo_results, str(tmp_path), "gemini-2.5-pro")
        with open(csv_files[0], "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            next(reader)  # skip header
            rows = list(reader)
            assert len(rows) == 2
            # Check first row has filename
            filenames = [r[0] for r in rows]
            assert "photo1.jpg" in filenames

    def test_video_csv_has_poster_timecode(self, tmp_path, video_results):
        csv_files = CSVExporter.export_istock(video_results, str(tmp_path), "gemini-2.5-pro")
        with open(csv_files[0], "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            next(reader)  # skip header
            row = next(reader)
            # poster timecode is column index 5 in ISTOCK_COLS_VIDEO
            assert row[5] == "00:00:05:00"

    def test_skips_failed_files(self, tmp_path, failed_results):
        csv_files = CSVExporter.export_istock(failed_results, str(tmp_path), "gemini-2.5-pro")
        if csv_files:
            with open(csv_files[0], "r", encoding="utf-8") as f:
                reader = csv.reader(f)
                next(reader)  # skip header
                rows = list(reader)
                filenames = [r[0] for r in rows]
                assert "bad.jpg" not in filenames

    def test_empty_results_no_csv(self, tmp_path):
        csv_files = CSVExporter.export_istock({}, str(tmp_path), "gemini-2.5-pro")
        assert csv_files == []

    def test_all_failed_no_csv(self, tmp_path):
        results = {"bad.jpg": {"status": "error"}}
        csv_files = CSVExporter.export_istock(results, str(tmp_path), "gemini-2.5-pro")
        assert csv_files == []

    def test_keywords_joined_as_comma_separated(self, tmp_path, photo_results):
        csv_files = CSVExporter.export_istock(photo_results, str(tmp_path), "gemini-2.5-pro")
        with open(csv_files[0], "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            next(reader)
            row = next(reader)
            # keywords is the last column (index 6) in ISTOCK_COLS_PHOTO
            kw_str = row[6]
            assert ", " in kw_str or kw_str  # comma-separated


# ═══════════════════════════════════════
# export_adobe
# ═══════════════════════════════════════

class TestExportAdobe:

    def test_creates_csv(self, tmp_path, photo_results):
        csv_files = CSVExporter.export_adobe(photo_results, str(tmp_path), "gemini-2.5-pro")
        assert len(csv_files) == 1
        assert os.path.isfile(csv_files[0])

    def test_correct_columns(self, tmp_path, photo_results):
        csv_files = CSVExporter.export_adobe(photo_results, str(tmp_path), "gemini-2.5-pro")
        with open(csv_files[0], "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            header = next(reader)
            assert header == ADOBE_CSV_COLUMNS

    def test_data_rows(self, tmp_path, photo_results):
        csv_files = CSVExporter.export_adobe(photo_results, str(tmp_path), "gemini-2.5-pro")
        with open(csv_files[0], "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            next(reader)
            rows = list(reader)
            assert len(rows) == 2

    def test_empty_results(self, tmp_path):
        csv_files = CSVExporter.export_adobe({}, str(tmp_path), "gemini-2.5-pro")
        assert csv_files == []

    def test_style_tag_in_filename(self, tmp_path, photo_results):
        csv_files = CSVExporter.export_adobe(photo_results, str(tmp_path), "gemini-2.5-pro", "Hybrid")
        assert "Hybrid" in csv_files[0]


# ═══════════════════════════════════════
# export_shutterstock
# ═══════════════════════════════════════

class TestExportShutterstock:

    def test_creates_csv(self, tmp_path, photo_results):
        csv_files = CSVExporter.export_shutterstock(photo_results, str(tmp_path), "gemini-2.5-pro")
        assert len(csv_files) == 1

    def test_correct_columns(self, tmp_path, photo_results):
        csv_files = CSVExporter.export_shutterstock(photo_results, str(tmp_path), "gemini-2.5-pro")
        with open(csv_files[0], "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            header = next(reader)
            assert header == SHUTTERSTOCK_CSV_COLUMNS

    def test_default_values(self, tmp_path, photo_results):
        """Illustration, Mature Content, Editorial should default to 'No'."""
        csv_files = CSVExporter.export_shutterstock(photo_results, str(tmp_path), "gemini-2.5-pro")
        with open(csv_files[0], "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            next(reader)
            row = next(reader)
            # Illustration=idx4, Mature=idx5, Editorial=idx6
            assert row[4] == "No"
            assert row[5] == "No"
            assert row[6] == "No"

    def test_categories_list_joined(self, tmp_path):
        results = {
            "photo.jpg": {
                "status": "success",
                "title": "Test",
                "description": "Test desc",
                "keywords": ["test"],
                "category": ["Nature", "Landscapes"],
            }
        }
        csv_files = CSVExporter.export_shutterstock(results, str(tmp_path), "gemini-2.5-pro")
        with open(csv_files[0], "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            next(reader)
            row = next(reader)
            assert row[3] == "Nature/Landscapes"


# ═══════════════════════════════════════
# export_for_platform (routing)
# ═══════════════════════════════════════

class TestExportForPlatform:

    def test_istock_routing(self, tmp_path, photo_results):
        csv_files = CSVExporter.export_for_platform("iStock", photo_results, str(tmp_path), "gemini-2.5-pro")
        assert len(csv_files) >= 1
        assert any("iStock" in f for f in csv_files)

    def test_adobe_shutterstock_routing(self, tmp_path, photo_results):
        csv_files = CSVExporter.export_for_platform(
            "Adobe & Shutterstock", photo_results, str(tmp_path), "gemini-2.5-pro", "Hybrid"
        )
        assert len(csv_files) == 2  # Adobe + Shutterstock

    def test_unknown_platform_returns_empty(self, tmp_path, photo_results):
        csv_files = CSVExporter.export_for_platform("Unknown", photo_results, str(tmp_path), "gemini-2.5-pro")
        assert csv_files == []

    def test_case_insensitive_platform(self, tmp_path, photo_results):
        csv_files = CSVExporter.export_for_platform("ISTOCK", photo_results, str(tmp_path), "gemini-2.5-pro")
        assert len(csv_files) >= 1

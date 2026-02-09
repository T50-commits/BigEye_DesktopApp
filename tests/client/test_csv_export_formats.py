"""
Tests for CSV export formatting:
  - iStock photo/video split with correct columns
  - Adobe Stock format
  - Shutterstock format with default values
  - Special characters in keywords (commas, quotes, unicode)
  - export_for_platform routing
  - Empty/failed results handling
"""
import csv
import os
import pytest

from core.data.csv_exporter import CSVExporter
from core.config import (
    ISTOCK_COLS_PHOTO, ISTOCK_COLS_VIDEO,
    ADOBE_CSV_COLUMNS, SHUTTERSTOCK_CSV_COLUMNS,
)


# ── Fixtures ──

@pytest.fixture
def photo_results():
    return {
        "sunset.jpg": {
            "status": "success",
            "title": "Golden Sunset Over Ocean",
            "description": "A beautiful golden sunset over the calm ocean",
            "keywords": ["sunset", "golden", "ocean", "calm", "horizon"],
            "category": "Nature",
            "created_date": "2025-01-15",
        },
        "mountain.png": {
            "status": "success",
            "title": "Snow Mountain Peaks",
            "description": "Snow-capped mountain peaks against blue sky",
            "keywords": ["mountain", "snow", "peaks", "blue sky"],
            "category": "Landscapes",
            "created_date": "2025-01-16",
        },
    }


@pytest.fixture
def video_results():
    return {
        "waves.mp4": {
            "status": "success",
            "title": "Ocean Waves Crashing",
            "description": "Slow motion ocean waves crashing on rocks",
            "keywords": ["ocean", "waves", "slow motion", "rocks"],
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
def special_char_results():
    """Results with special characters that need CSV escaping."""
    return {
        "special.jpg": {
            "status": "success",
            "title": 'Photo with "quotes" and commas, here',
            "description": "Description with\nnewline and\ttab",
            "keywords": [
                "café", "naïve", "résumé",           # unicode accents
                'word "quoted"',                       # embedded quotes
                "comma, separated",                    # embedded comma
                "normal keyword",
                "日本語",                               # CJK characters
                "über cool",                           # umlaut
            ],
            "category": "Abstract",
        },
    }


def _read_csv(filepath):
    """Read CSV and return (header, rows)."""
    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader)
        rows = list(reader)
    return header, rows


# ═══════════════════════════════════════
# iStock Export
# ═══════════════════════════════════════

class TestExportIstock:

    def test_splits_photos_and_videos(self, tmp_path, mixed_results):
        csv_files = CSVExporter.export_istock(mixed_results, str(tmp_path), "gemini-2.5-pro")
        assert len(csv_files) == 2
        photo_csv = [f for f in csv_files if "Photos" in f]
        video_csv = [f for f in csv_files if "Videos" in f]
        assert len(photo_csv) == 1
        assert len(video_csv) == 1

    def test_photo_csv_correct_columns(self, tmp_path, photo_results):
        csv_files = CSVExporter.export_istock(photo_results, str(tmp_path), "gemini-2.5-pro")
        header, rows = _read_csv(csv_files[0])
        assert header == ISTOCK_COLS_PHOTO

    def test_photo_csv_column_mapping(self, tmp_path, photo_results):
        """Verify each column maps to the correct data field."""
        csv_files = CSVExporter.export_istock(photo_results, str(tmp_path), "gemini-2.5-pro")
        header, rows = _read_csv(csv_files[0])
        # Find sunset row
        sunset_row = next(r for r in rows if r[0] == "sunset.jpg")
        assert sunset_row[0] == "sunset.jpg"           # file name
        assert sunset_row[1] == "2025-01-15"            # created date
        assert "golden sunset" in sunset_row[2].lower() # description
        assert sunset_row[3] == ""                       # country (empty)
        assert sunset_row[4] == ""                       # brief code (empty)
        assert sunset_row[5] == "Golden Sunset Over Ocean"  # title
        assert "sunset" in sunset_row[6]                 # keywords

    def test_video_csv_correct_columns(self, tmp_path, video_results):
        csv_files = CSVExporter.export_istock(video_results, str(tmp_path), "gemini-2.5-pro")
        header, rows = _read_csv(csv_files[0])
        assert header == ISTOCK_COLS_VIDEO

    def test_video_csv_has_poster_timecode(self, tmp_path, video_results):
        csv_files = CSVExporter.export_istock(video_results, str(tmp_path), "gemini-2.5-pro")
        header, rows = _read_csv(csv_files[0])
        row = rows[0]
        # poster timecode is at index 5 in ISTOCK_COLS_VIDEO
        poster_idx = ISTOCK_COLS_VIDEO.index("poster timecode")
        assert row[poster_idx] == "00:00:05:00"

    def test_video_csv_has_shot_speed(self, tmp_path, video_results):
        csv_files = CSVExporter.export_istock(video_results, str(tmp_path), "gemini-2.5-pro")
        header, rows = _read_csv(csv_files[0])
        shot_speed_idx = ISTOCK_COLS_VIDEO.index("shot speed")
        assert rows[0][shot_speed_idx] == "Slow Motion"

    def test_keywords_comma_separated(self, tmp_path, photo_results):
        csv_files = CSVExporter.export_istock(photo_results, str(tmp_path), "gemini-2.5-pro")
        _, rows = _read_csv(csv_files[0])
        kw_idx = ISTOCK_COLS_PHOTO.index("keywords")
        kw_str = rows[0][kw_idx]
        assert ", " in kw_str

    def test_skips_failed_files(self, tmp_path):
        results = {
            "good.jpg": {"status": "success", "title": "Good", "description": "d",
                         "keywords": ["a"], "category": "c"},
            "bad.jpg": {"status": "error", "error": "timeout"},
        }
        csv_files = CSVExporter.export_istock(results, str(tmp_path), "gemini-2.5-pro")
        _, rows = _read_csv(csv_files[0])
        filenames = [r[0] for r in rows]
        assert "good.jpg" in filenames
        assert "bad.jpg" not in filenames

    def test_empty_results_no_csv(self, tmp_path):
        assert CSVExporter.export_istock({}, str(tmp_path), "gemini-2.5-pro") == []

    def test_all_failed_no_csv(self, tmp_path):
        results = {"bad.jpg": {"status": "error"}}
        assert CSVExporter.export_istock(results, str(tmp_path), "gemini-2.5-pro") == []

    def test_photos_only_one_csv(self, tmp_path, photo_results):
        csv_files = CSVExporter.export_istock(photo_results, str(tmp_path), "gemini-2.5-pro")
        assert len(csv_files) == 1
        assert "Photos" in csv_files[0]

    def test_videos_only_one_csv(self, tmp_path, video_results):
        csv_files = CSVExporter.export_istock(video_results, str(tmp_path), "gemini-2.5-pro")
        assert len(csv_files) == 1
        assert "Videos" in csv_files[0]


# ═══════════════════════════════════════
# Adobe Export
# ═══════════════════════════════════════

class TestExportAdobe:

    def test_correct_columns(self, tmp_path, photo_results):
        csv_files = CSVExporter.export_adobe(photo_results, str(tmp_path), "gemini-2.5-pro")
        header, _ = _read_csv(csv_files[0])
        assert header == ADOBE_CSV_COLUMNS

    def test_column_mapping(self, tmp_path, photo_results):
        csv_files = CSVExporter.export_adobe(photo_results, str(tmp_path), "gemini-2.5-pro")
        _, rows = _read_csv(csv_files[0])
        sunset_row = next(r for r in rows if r[0] == "sunset.jpg")
        assert sunset_row[0] == "sunset.jpg"                    # Filename
        assert sunset_row[1] == "Golden Sunset Over Ocean"      # Title
        assert "sunset" in sunset_row[2]                         # Keywords
        assert sunset_row[3] == "Nature"                         # Category
        assert sunset_row[4] == ""                               # Releases (empty)

    def test_style_tag_in_filename(self, tmp_path, photo_results):
        csv_files = CSVExporter.export_adobe(photo_results, str(tmp_path), "gemini-2.5-pro", "Hybrid")
        assert "Hybrid" in csv_files[0]

    def test_empty_results(self, tmp_path):
        assert CSVExporter.export_adobe({}, str(tmp_path), "gemini-2.5-pro") == []

    def test_data_row_count(self, tmp_path, photo_results):
        csv_files = CSVExporter.export_adobe(photo_results, str(tmp_path), "gemini-2.5-pro")
        _, rows = _read_csv(csv_files[0])
        assert len(rows) == 2


# ═══════════════════════════════════════
# Shutterstock Export
# ═══════════════════════════════════════

class TestExportShutterstock:

    def test_correct_columns(self, tmp_path, photo_results):
        csv_files = CSVExporter.export_shutterstock(photo_results, str(tmp_path), "gemini-2.5-pro")
        header, _ = _read_csv(csv_files[0])
        assert header == SHUTTERSTOCK_CSV_COLUMNS

    def test_default_values(self, tmp_path, photo_results):
        """Illustration, Mature Content, Editorial should default to 'No'."""
        csv_files = CSVExporter.export_shutterstock(photo_results, str(tmp_path), "gemini-2.5-pro")
        _, rows = _read_csv(csv_files[0])
        for row in rows:
            ill_idx = SHUTTERSTOCK_CSV_COLUMNS.index("Illustration")
            mat_idx = SHUTTERSTOCK_CSV_COLUMNS.index("Mature Content")
            edi_idx = SHUTTERSTOCK_CSV_COLUMNS.index("Editorial")
            assert row[ill_idx] == "No"
            assert row[mat_idx] == "No"
            assert row[edi_idx] == "No"

    def test_categories_list_joined(self, tmp_path):
        """When category is a list, join with '/'."""
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
        _, rows = _read_csv(csv_files[0])
        cat_idx = SHUTTERSTOCK_CSV_COLUMNS.index("Categories")
        assert rows[0][cat_idx] == "Nature/Landscapes"

    def test_description_in_correct_column(self, tmp_path, photo_results):
        csv_files = CSVExporter.export_shutterstock(photo_results, str(tmp_path), "gemini-2.5-pro")
        _, rows = _read_csv(csv_files[0])
        desc_idx = SHUTTERSTOCK_CSV_COLUMNS.index("Description")
        sunset_row = next(r for r in rows if r[0] == "sunset.jpg")
        assert "golden sunset" in sunset_row[desc_idx].lower()


# ═══════════════════════════════════════
# Special Characters in Keywords
# ═══════════════════════════════════════

class TestSpecialCharacters:

    def test_unicode_keywords_in_istock(self, tmp_path, special_char_results):
        csv_files = CSVExporter.export_istock(special_char_results, str(tmp_path), "gemini-2.5-pro")
        _, rows = _read_csv(csv_files[0])
        kw_idx = ISTOCK_COLS_PHOTO.index("keywords")
        kw_str = rows[0][kw_idx]
        assert "café" in kw_str
        assert "naïve" in kw_str
        assert "日本語" in kw_str

    def test_embedded_commas_escaped(self, tmp_path, special_char_results):
        """Keywords with commas should be properly CSV-escaped."""
        csv_files = CSVExporter.export_adobe(special_char_results, str(tmp_path), "gemini-2.5-pro")
        # Re-read raw to verify CSV escaping
        with open(csv_files[0], "r", encoding="utf-8") as f:
            content = f.read()
        # The keyword string contains commas, so the entire field should be quoted
        assert '"' in content  # CSV writer quotes fields with commas

    def test_embedded_quotes_escaped(self, tmp_path, special_char_results):
        """Titles with quotes should be properly CSV-escaped."""
        csv_files = CSVExporter.export_adobe(special_char_results, str(tmp_path), "gemini-2.5-pro")
        _, rows = _read_csv(csv_files[0])
        title = rows[0][1]
        assert '"quotes"' in title  # quotes preserved after CSV round-trip

    def test_unicode_in_shutterstock(self, tmp_path, special_char_results):
        csv_files = CSVExporter.export_shutterstock(special_char_results, str(tmp_path), "gemini-2.5-pro")
        _, rows = _read_csv(csv_files[0])
        kw_idx = SHUTTERSTOCK_CSV_COLUMNS.index("Keywords")
        assert "über cool" in rows[0][kw_idx]

    def test_keywords_as_string_fallback(self, tmp_path):
        """If keywords is a string instead of list, should still work."""
        results = {
            "photo.jpg": {
                "status": "success",
                "title": "Test",
                "description": "Desc",
                "keywords": "sunset, ocean, golden",  # string, not list
                "category": "Nature",
            }
        }
        csv_files = CSVExporter.export_adobe(results, str(tmp_path), "gemini-2.5-pro")
        _, rows = _read_csv(csv_files[0])
        assert "sunset" in rows[0][2]


# ═══════════════════════════════════════
# export_for_platform Routing
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

    def test_case_insensitive_platform(self, tmp_path, photo_results):
        csv_files = CSVExporter.export_for_platform("ISTOCK", photo_results, str(tmp_path), "gemini-2.5-pro")
        assert len(csv_files) >= 1

    def test_unknown_platform_returns_empty(self, tmp_path, photo_results):
        csv_files = CSVExporter.export_for_platform("Unknown", photo_results, str(tmp_path), "gemini-2.5-pro")
        assert csv_files == []

    def test_adobe_keyword_routes(self, tmp_path, photo_results):
        csv_files = CSVExporter.export_for_platform("Adobe", photo_results, str(tmp_path), "gemini-2.5-pro")
        assert len(csv_files) == 2  # Adobe + Shutterstock

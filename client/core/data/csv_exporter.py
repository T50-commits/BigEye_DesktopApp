"""
BigEye Pro — CSV Exporter (Task B-08)
Generates platform-specific CSV files from processed metadata.
Supports iStock (photo/video split), Adobe Stock, and Shutterstock formats.
"""
import csv
import os
import logging
from datetime import datetime

from core.config import (
    ISTOCK_COLS_PHOTO, ISTOCK_COLS_VIDEO,
    ADOBE_CSV_COLUMNS, SHUTTERSTOCK_CSV_COLUMNS,
    IMAGE_EXTENSIONS, VIDEO_EXTENSIONS,
)
from utils.helpers import is_video, is_image

logger = logging.getLogger("bigeye")


class CSVExporter:
    """Exports metadata results to platform-specific CSV formats."""

    @staticmethod
    def export_istock(results: dict, folder_path: str, model: str, keyword_style: str = "") -> list:
        """
        Export iStock CSV — auto-splits into photos + videos.
        results: {filename: {title, description, keywords, category, status, ...}}
        Returns list of created CSV file paths.
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_files = []

        # Split results into photos and videos
        photos = {}
        videos = {}
        for filename, data in results.items():
            if data.get("status") != "success":
                continue
            ext = os.path.splitext(filename)[1].lower()
            if ext in VIDEO_EXTENSIONS:
                videos[filename] = data
            else:
                photos[filename] = data

        # Export photos CSV
        if photos:
            filepath = os.path.join(folder_path, f"Metadata iStock Photos_{model}_{timestamp}.csv")
            CSVExporter._write_istock_photo_csv(filepath, photos, ISTOCK_COLS_PHOTO)
            csv_files.append(filepath)
            logger.info(f"iStock photos CSV: {len(photos)} files → {filepath}")

        # Export videos CSV
        if videos:
            filepath = os.path.join(folder_path, f"Metadata iStock Videos_{model}_{timestamp}.csv")
            CSVExporter._write_istock_video_csv(filepath, videos, ISTOCK_COLS_VIDEO)
            csv_files.append(filepath)
            logger.info(f"iStock videos CSV: {len(videos)} files → {filepath}")

        return csv_files

    @staticmethod
    def export_adobe(results: dict, folder_path: str, model: str, keyword_style: str = "") -> list:
        """
        Export Adobe Stock CSV.
        Returns list of created CSV file paths.
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        style_tag = f"_{keyword_style}" if keyword_style else ""
        filepath = os.path.join(folder_path, f"Metadata Adobe{style_tag}_{model}_{timestamp}.csv")

        success = {fn: d for fn, d in results.items() if d.get("status") == "success"}
        if not success:
            return []

        try:
            with open(filepath, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(ADOBE_CSV_COLUMNS)
                for filename, data in success.items():
                    keywords = data.get("keywords", [])
                    kw_str = ", ".join(keywords) if isinstance(keywords, list) else str(keywords)
                    writer.writerow([
                        filename,                          # Filename
                        data.get("title", ""),             # Title
                        kw_str,                            # Keywords
                        data.get("category", ""),          # Category
                        "",                                # Releases
                    ])
            logger.info(f"Adobe CSV: {len(success)} files → {filepath}")
            return [filepath]
        except OSError as e:
            logger.error(f"Adobe CSV export failed: {e}")
            return []

    @staticmethod
    def export_shutterstock(results: dict, folder_path: str, model: str, keyword_style: str = "") -> list:
        """
        Export Shutterstock CSV.
        Returns list of created CSV file paths.
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        style_tag = f"_{keyword_style}" if keyword_style else ""
        filepath = os.path.join(folder_path, f"Metadata Shutterstock{style_tag}_{model}_{timestamp}.csv")

        success = {fn: d for fn, d in results.items() if d.get("status") == "success"}
        if not success:
            return []

        try:
            with open(filepath, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(SHUTTERSTOCK_CSV_COLUMNS)
                for filename, data in success.items():
                    keywords = data.get("keywords", [])
                    kw_str = ", ".join(keywords) if isinstance(keywords, list) else str(keywords)
                    categories = data.get("category", "")
                    if isinstance(categories, list):
                        categories = "/".join(categories)
                    writer.writerow([
                        filename,                          # Filename
                        data.get("description", ""),       # Description
                        kw_str,                            # Keywords
                        categories,                        # Categories
                        "No",                              # Illustration
                        "No",                              # Mature Content
                        "No",                              # Editorial
                    ])
            logger.info(f"Shutterstock CSV: {len(success)} files → {filepath}")
            return [filepath]
        except OSError as e:
            logger.error(f"Shutterstock CSV export failed: {e}")
            return []

    @staticmethod
    def export_adobe_shutterstock(results: dict, folder_path: str, model: str, keyword_style: str = "") -> list:
        """
        Export both Adobe and Shutterstock CSVs.
        Returns combined list of created CSV file paths.
        """
        files = []
        files.extend(CSVExporter.export_adobe(results, folder_path, model, keyword_style))
        files.extend(CSVExporter.export_shutterstock(results, folder_path, model, keyword_style))
        return files

    @staticmethod
    def export_for_platform(platform: str, results: dict,
                            folder_path: str, model: str,
                            keyword_style: str = "") -> list:
        """
        Export CSV for the specified platform name.
        Convenience method used by JobManager.
        """
        if "istock" in platform.lower():
            return CSVExporter.export_istock(results, folder_path, model)
        elif "adobe" in platform.lower() or "shutterstock" in platform.lower():
            return CSVExporter.export_adobe_shutterstock(results, folder_path, model, keyword_style)
        else:
            logger.warning(f"Unknown platform for CSV export: {platform}")
            return []

    # ── Internal ──

    @staticmethod
    def _write_istock_photo_csv(filepath: str, results: dict, columns: list):
        """Write iStock Photo CSV with correct column mapping."""
        try:
            with open(filepath, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(columns)
                for filename, data in results.items():
                    keywords = data.get("keywords", [])
                    kw_str = ", ".join(keywords) if isinstance(keywords, list) else str(keywords)
                    writer.writerow([
                        filename,                              # file name
                        data.get("created_date", ""),           # created date
                        data.get("description", ""),            # description
                        "",                                     # country
                        "",                                     # brief code
                        data.get("title", ""),                  # title
                        kw_str,                                 # keywords
                    ])
        except OSError as e:
            logger.error(f"iStock Photo CSV write failed: {e}")

    @staticmethod
    def _write_istock_video_csv(filepath: str, results: dict, columns: list):
        """Write iStock Video CSV with correct column mapping."""
        try:
            with open(filepath, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(columns)
                for filename, data in results.items():
                    keywords = data.get("keywords", [])
                    kw_str = ", ".join(keywords) if isinstance(keywords, list) else str(keywords)
                    writer.writerow([
                        filename,                              # file name
                        data.get("description", ""),            # description
                        "",                                     # country
                        data.get("title", ""),                  # title
                        kw_str,                                 # keywords
                        data.get("poster_timecode", ""),        # poster timecode
                        data.get("created_date", ""),           # date created
                        data.get("shot_speed", ""),             # shot speed
                    ])
        except OSError as e:
            logger.error(f"iStock Video CSV write failed: {e}")

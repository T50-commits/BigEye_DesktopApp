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
    def export_istock(results: dict, folder_path: str, model: str) -> list:
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
            filepath = os.path.join(folder_path, f"iStock_Photos_{model}_{timestamp}.csv")
            CSVExporter._write_istock_csv(filepath, photos, ISTOCK_COLS_PHOTO)
            csv_files.append(filepath)
            logger.info(f"iStock photos CSV: {len(photos)} files → {filepath}")

        # Export videos CSV
        if videos:
            filepath = os.path.join(folder_path, f"iStock_Videos_{model}_{timestamp}.csv")
            CSVExporter._write_istock_csv(filepath, videos, ISTOCK_COLS_VIDEO)
            csv_files.append(filepath)
            logger.info(f"iStock videos CSV: {len(videos)} files → {filepath}")

        return csv_files

    @staticmethod
    def export_adobe(results: dict, folder_path: str, model: str) -> list:
        """
        Export Adobe Stock CSV.
        Returns list of created CSV file paths.
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = os.path.join(folder_path, f"Adobe_{model}_{timestamp}.csv")

        success = {fn: d for fn, d in results.items() if d.get("status") == "success"}
        if not success:
            return []

        try:
            with open(filepath, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(ADOBE_CSV_COLUMNS)
                for filename, data in success.items():
                    keywords = data.get("keywords", [])
                    kw_str = ",".join(keywords) if isinstance(keywords, list) else str(keywords)
                    writer.writerow([
                        filename,
                        data.get("title", ""),
                        kw_str,
                        data.get("category", ""),
                        "",  # Releases
                    ])
            logger.info(f"Adobe CSV: {len(success)} files → {filepath}")
            return [filepath]
        except OSError as e:
            logger.error(f"Adobe CSV export failed: {e}")
            return []

    @staticmethod
    def export_shutterstock(results: dict, folder_path: str, model: str) -> list:
        """
        Export Shutterstock CSV.
        Returns list of created CSV file paths.
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = os.path.join(folder_path, f"Shutterstock_{model}_{timestamp}.csv")

        success = {fn: d for fn, d in results.items() if d.get("status") == "success"}
        if not success:
            return []

        try:
            with open(filepath, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(SHUTTERSTOCK_CSV_COLUMNS)
                for filename, data in success.items():
                    keywords = data.get("keywords", [])
                    kw_str = ",".join(keywords) if isinstance(keywords, list) else str(keywords)
                    categories = data.get("category", "")
                    if isinstance(categories, list):
                        categories = "/".join(categories)
                    writer.writerow([
                        filename,
                        data.get("description", ""),
                        kw_str,
                        categories,
                        "no",  # Editorial
                    ])
            logger.info(f"Shutterstock CSV: {len(success)} files → {filepath}")
            return [filepath]
        except OSError as e:
            logger.error(f"Shutterstock CSV export failed: {e}")
            return []

    @staticmethod
    def export_adobe_shutterstock(results: dict, folder_path: str, model: str) -> list:
        """
        Export both Adobe and Shutterstock CSVs.
        Returns combined list of created CSV file paths.
        """
        files = []
        files.extend(CSVExporter.export_adobe(results, folder_path, model))
        files.extend(CSVExporter.export_shutterstock(results, folder_path, model))
        return files

    @staticmethod
    def export_for_platform(platform: str, results: dict,
                            folder_path: str, model: str) -> list:
        """
        Export CSV for the specified platform name.
        Convenience method used by JobManager.
        """
        if "istock" in platform.lower():
            return CSVExporter.export_istock(results, folder_path, model)
        elif "adobe" in platform.lower() or "shutterstock" in platform.lower():
            return CSVExporter.export_adobe_shutterstock(results, folder_path, model)
        else:
            logger.warning(f"Unknown platform for CSV export: {platform}")
            return []

    # ── Internal ──

    @staticmethod
    def _write_istock_csv(filepath: str, results: dict, columns: list):
        """Write iStock-format CSV."""
        try:
            with open(filepath, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(columns)
                for filename, data in results.items():
                    keywords = data.get("keywords", [])
                    kw_str = ",".join(keywords) if isinstance(keywords, list) else str(keywords)
                    row = [
                        filename,
                        data.get("title", ""),
                        data.get("description", ""),
                        kw_str,
                        data.get("category", ""),
                    ]
                    # Pad or trim to match columns
                    while len(row) < len(columns):
                        row.append("")
                    writer.writerow(row[:len(columns)])
        except OSError as e:
            logger.error(f"iStock CSV write failed: {e}")

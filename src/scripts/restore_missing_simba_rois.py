import argparse
import json
import os
import sys

import pandas as pd

SCRIPT_DIR = os.path.dirname(__file__)
SRC_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
if SRC_DIR not in sys.path:
    sys.path.append(SRC_DIR)

from simba_roi_bridge import (
    CIRCLE_HEADERS,
    POLYGON_HEADERS,
    RECTANGLE_HEADERS,
    _create_rectangle_from_line,
    _load_existing_roi_frames,
    _map_zones_to_model_rois,
    MODEL_ROI_STYLE,
)


def _load_zonas(zonas_path: str) -> list[dict]:
    with open(zonas_path, "r", encoding="utf-8") as file_handle:
        data = json.load(file_handle)
    if not isinstance(data, list):
        raise ValueError(f"Expected a list of zones in {zonas_path}")
    return data


def _load_video_info(project_folder: str) -> pd.DataFrame:
    video_info_path = os.path.join(project_folder, "logs", "video_info.csv")
    if not os.path.exists(video_info_path):
        raise FileNotFoundError(f"video_info.csv not found: {video_info_path}")
    return pd.read_csv(video_info_path)


def _get_pixels_per_mm(video_info_df: pd.DataFrame, video_name: str) -> float:
    row = video_info_df.loc[video_info_df["Video"].astype(str) == str(video_name)]
    if row.empty:
        return 2.5
    value = pd.to_numeric(row.iloc[0].get("pixels/mm"), errors="coerce")
    return float(value) if pd.notna(value) and float(value) > 0 else 2.5


def restore_missing_rois(project_folder: str, zonas_list: list[dict], include_existing: bool = False) -> dict:
    video_info_df = _load_video_info(project_folder)
    roi_path = os.path.join(project_folder, "logs", "measures", "ROI_definitions.h5")
    os.makedirs(os.path.dirname(roi_path), exist_ok=True)

    rectangles_df, circles_df, polygon_df = _load_existing_roi_frames(roi_path)

    existing_roi_videos = set(rectangles_df["Video"].dropna().astype(str).tolist())
    target_videos = video_info_df["Video"].dropna().astype(str).tolist()
    if not include_existing:
        target_videos = [video_name for video_name in target_videos if video_name not in existing_roi_videos]

    restored_videos: list[str] = []
    roi_map = _map_zones_to_model_rois(zonas_list)

    for video_name in target_videos:
        pixels_per_mm = _get_pixels_per_mm(video_info_df, video_name)
        rectangles_df = rectangles_df[rectangles_df["Video"].astype(str) != video_name].reset_index(drop=True)
        circles_df = circles_df[circles_df["Video"].astype(str) != video_name].reset_index(drop=True)
        polygon_df = polygon_df[polygon_df["Video"].astype(str) != video_name].reset_index(drop=True)

        new_rows: list[dict] = []
        for roi_name, zone_data in roi_map.items():
            if str(zone_data.get("type", "rect")).lower() == "line":
                row = _create_rectangle_from_line(video_name, roi_name, zone_data, pixels_per_mm)
                row["Color name"] = MODEL_ROI_STYLE[roi_name][0]
                row["Color BGR"] = MODEL_ROI_STYLE[roi_name][1]
                new_rows.append(row)
            else:
                new_rows.append(
                    _create_rectangle_from_zone(
                        video_name,
                        roi_name,
                        zone_data,
                        pixels_per_mm,
                        color_override=MODEL_ROI_STYLE[roi_name],
                    )
                )

        if new_rows:
            rectangles_df = pd.concat(
                [rectangles_df, pd.DataFrame(new_rows, columns=RECTANGLE_HEADERS)],
                ignore_index=True,
            )
            restored_videos.append(video_name)

    with pd.HDFStore(roi_path, mode="w") as store:
        store["rectangles"] = rectangles_df.reindex(columns=RECTANGLE_HEADERS)
        store["circleDf"] = circles_df.reindex(columns=CIRCLE_HEADERS)
        store["polygons"] = polygon_df.reindex(columns=POLYGON_HEADERS)

    return {
        "roi_path": roi_path,
        "restored_videos": restored_videos,
        "restored_count": len(restored_videos),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Restore missing ROI rows in a SimBA project from a Streamlit zones template.")
    parser.add_argument("--project_folder", required=True, help="Path to SimBA project_folder")
    parser.add_argument("--zonas", required=True, help="Path to JSON file with Streamlit zones")
    parser.add_argument("--include_existing", action="store_true", help="Also rewrite videos that already have ROI rows")
    args = parser.parse_args()

    result = restore_missing_rois(
        project_folder=os.path.abspath(args.project_folder),
        zonas_list=_load_zonas(os.path.abspath(args.zonas)),
        include_existing=args.include_existing,
    )
    print(result)

import sqlite3
import pandas as pd

DB_PATH = "creator_core.db"
XLSX_PATH = "ytstats.xlsx"


def _sort_desc(df: pd.DataFrame, column: str) -> pd.DataFrame:
    if column in df.columns and not df.empty:
        return df.sort_values(by=column, ascending=False, kind="stable")
    return df


def _combine_unique(values) -> str:
    seen = []
    for value in values:
        if pd.isna(value):
            continue
        text = str(value).strip()
        if text and text not in seen:
            seen.append(text)
    return "; ".join(seen)


def export_to_excel() -> None:
    conn = sqlite3.connect(DB_PATH)

    try:
        # Load tables from SQLite
        videos = pd.read_sql_query("SELECT * FROM videos", conn)
        playlists = pd.read_sql_query("SELECT * FROM playlists", conn)
        playlist_videos = pd.read_sql_query("SELECT * FROM playlist_videos", conn)
        comments = pd.read_sql_query("SELECT * FROM creator_comments", conn)

        # --- FIX: ensure IDs match properly ---
        videos["video_id"] = videos["video_id"].astype(str).str.strip()
        playlist_videos["video_id"] = playlist_videos["video_id"].astype(str).str.strip()
        playlist_videos["playlist_id"] = playlist_videos["playlist_id"].astype(str).str.strip()
        playlists["playlist_id"] = playlists["playlist_id"].astype(str).str.strip()

        # Sort raw sheets newest-first where a date exists
        videos = _sort_desc(videos, "published_at")
        comments = _sort_desc(comments, "published_at")
        playlists = _sort_desc(playlists, "playlist_name")

        # Build one playlist-name cell per video_id so MASTER stays one row per video
        playlist_names = pd.DataFrame(columns=["video_id", "playlist_name"])

        if not playlist_videos.empty and not playlists.empty:
            playlist_lookup = playlist_videos.merge(
                playlists[["playlist_id", "playlist_name"]],
                on="playlist_id",
                how="left",
            )

            playlist_names = (
                playlist_lookup
                .groupby("video_id", as_index=False)["playlist_name"]
                .agg(_combine_unique)
            )

        # MASTER = videos + playlist names
        master = videos.merge(playlist_names, on="video_id", how="left")
        master = _sort_desc(master, "published_at")

        # Keep MASTER clean and readable
        master_columns = [
            "video_id",
            "title",
            "published_at",
            "view_count",
            "like_count",
            "comment_count",
            "playlist_name",
        ]
        master = master[[col for col in master_columns if col in master.columns]]

        # Overwrite workbook completely, no manual deleting needed
        with pd.ExcelWriter(XLSX_PATH, engine="openpyxl", mode="w") as writer:
            master.to_excel(writer, sheet_name="MASTER", index=False)
            videos.to_excel(writer, sheet_name="videos_raw", index=False)
            playlists.to_excel(writer, sheet_name="playlists", index=False)
            playlist_videos.to_excel(writer, sheet_name="playlist_videos", index=False)
            comments.to_excel(writer, sheet_name="creator_comments", index=False)

        print("Excel updated cleanly ✅")

    finally:
        conn.close()


if __name__ == "__main__":
    export_to_excel()
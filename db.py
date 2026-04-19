from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Iterable


def get_connection(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.execute('PRAGMA foreign_keys = ON;')
    return conn


def init_db(conn: sqlite3.Connection, schema_path: str = 'db/schema.sql') -> None:
    sql = Path(schema_path).read_text(encoding='utf-8')
    conn.executescript(sql)
    conn.commit()


def upsert_videos(conn: sqlite3.Connection, videos: Iterable[dict]) -> None:
    rows = [
        (
            v['video_id'],
            v.get('title') or '',
            v.get('description') or '',
            v.get('thumbnail_url'),
            v.get('published_at') or '',
            int(v.get('view_count') or 0),
            int(v.get('like_count') or 0),
            int(v.get('comment_count') or 0),
            v.get('duration_seconds'),
        )
        for v in videos
    ]
    if not rows:
        return

    conn.executemany(
        '''
        INSERT INTO videos (
            video_id, title, description, thumbnail_url, published_at,
            view_count, like_count, comment_count, duration_seconds
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(video_id) DO UPDATE SET
            title = excluded.title,
            description = excluded.description,
            thumbnail_url = excluded.thumbnail_url,
            published_at = excluded.published_at,
            view_count = excluded.view_count,
            like_count = excluded.like_count,
            comment_count = excluded.comment_count,
            duration_seconds = excluded.duration_seconds
        ''',
        rows,
    )
    conn.commit()


def upsert_playlists(conn: sqlite3.Connection, playlists: Iterable[dict]) -> None:
    rows = [
        (p['playlist_id'], p.get('playlist_name') or '')
        for p in playlists
    ]
    if not rows:
        return

    conn.executemany(
        '''
        INSERT INTO playlists (playlist_id, playlist_name)
        VALUES (?, ?)
        ON CONFLICT(playlist_id) DO UPDATE SET
            playlist_name = excluded.playlist_name
        ''',
        rows,
    )
    conn.commit()


def upsert_playlist_videos(conn: sqlite3.Connection, mappings: Iterable[dict]) -> None:
    rows = [
        (
            m['playlist_id'],
            m['video_id'],
            int(m.get('position') or 0),
        )
        for m in mappings
    ]
    if not rows:
        return

    conn.executemany(
        '''
        INSERT INTO playlist_videos (playlist_id, video_id, position)
        VALUES (?, ?, ?)
        ON CONFLICT(playlist_id, video_id) DO UPDATE SET
            position = excluded.position
        ''',
        rows,
    )
    conn.commit()


def insert_creator_comments(conn: sqlite3.Connection, comments: Iterable[dict]) -> None:
    rows = [
        (
            c['comment_id'],
            c['video_id'],
            c.get('text') or '',
            c.get('published_at') or '',
        )
        for c in comments
    ]
    if not rows:
        return

    conn.executemany(
        '''
        INSERT INTO creator_comments (comment_id, video_id, text, published_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(comment_id) DO NOTHING
        ''',
        rows,
    )
    conn.commit()


def get_status_counts(conn: sqlite3.Connection) -> dict:
    cursor = conn.cursor()
    videos = cursor.execute('SELECT COUNT(*) FROM videos').fetchone()[0]
    playlists = cursor.execute('SELECT COUNT(*) FROM playlists').fetchone()[0]
    comments = cursor.execute('SELECT COUNT(*) FROM creator_comments').fetchone()[0]
    return {
        'videos': videos,
        'playlists': playlists,
        'comments': comments,
    }

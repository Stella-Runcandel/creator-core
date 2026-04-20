from __future__ import annotations

import sys

from config import get_refresh_video_limit, load_config, save_env_value, validate_fetch_config
from db import (
    get_all_video_ids,
    get_connection,
    get_latest_video_ids,
    get_status_counts,
    init_db,
    insert_creator_comments,
    upsert_playlist_videos,
    upsert_playlists,
    upsert_videos,
)
from youtube import (
    YouTubeAPIError,
    get_channel_playlists,
    get_creator_comments,
    get_playlist_mappings,
    get_playlist_video_ids,
    get_uploads_playlist_id,
    get_video_details,
    resolve_channel_id,
)


def print_help() -> None:
    print('Usage:')
    print('  python main.py setup')
    print('  python main.py fetch')
    print('  python main.py update')
    print('  python main.py refresh')
    print('  python main.py status')


def refresh_playlists_and_mappings(api_key: str, channel_id: str) -> tuple[list[dict], list[dict]]:
    playlists = get_channel_playlists(api_key, channel_id)
    mappings: list[dict] = []
    for playlist in playlists:
        playlist_id = playlist['playlist_id']
        mappings.extend(get_playlist_mappings(api_key, playlist_id))
    return playlists, mappings


def run_setup() -> int:
    cfg = load_config()
    api_key = cfg.get('YOUTUBE_API_KEY')

    if not api_key:
        print('YOUTUBE_API_KEY is missing in .env')
        print('Add it first, for example:')
        print('  YOUTUBE_API_KEY=your_api_key_here')
        return 1

    user_input = input('Enter YouTube handle (e.g. @mychannel) or channel ID (UC...): ').strip()
    if not user_input:
        print('No input provided. Setup cancelled.')
        return 1

    print('Resolving channel ID...')
    try:
        channel_id = resolve_channel_id(api_key, user_input)
    except YouTubeAPIError as exc:
        print(f'Error while resolving channel: {exc}')
        return 1

    if not channel_id:
        print('Could not resolve channel ID. Check the handle/ID and try again.')
        return 1

    save_env_value('CHANNEL_ID', channel_id)
    print(f'CHANNEL_ID saved to .env: {channel_id}')
    return 0


def run_fetch() -> int:
    cfg = load_config()
    ok, errors = validate_fetch_config(cfg)
    if not ok:
        for err in errors:
            print(f'- {err}')
        return 1

    api_key = cfg['YOUTUBE_API_KEY']
    channel_id = cfg['CHANNEL_ID']
    db_path = cfg['DB_PATH'] or 'creator_core.db'

    conn = get_connection(db_path)
    init_db(conn)

    try:
        print('Fetching videos...')
        uploads_playlist_id = get_uploads_playlist_id(api_key, channel_id)
        upload_items = get_playlist_video_ids(api_key, uploads_playlist_id)
        video_ids = [item['video_id'] for item in upload_items]
        video_details = get_video_details(api_key, video_ids)

        print('Fetching playlists and playlist mappings...')
        playlists, mappings = refresh_playlists_and_mappings(api_key, channel_id)

        print('Fetching creator comments...')
        creator_comments: list[dict] = []
        for video_id in video_ids:
            creator_comments.extend(get_creator_comments(api_key, video_id, channel_id))

        print('Updating database...')
        upsert_videos(conn, video_details)
        upsert_playlists(conn, playlists)
        upsert_playlist_videos(conn, mappings)
        insert_creator_comments(conn, creator_comments)

        print('Fetch complete.')
        print(f'Videos processed: {len(video_details)}')
        print(f'Playlists processed: {len(playlists)}')
        print(f'Playlist mappings processed: {len(mappings)}')
        print(f'Creator comments processed: {len(creator_comments)}')
        return 0
    except YouTubeAPIError as exc:
        print(f'YouTube API error: {exc}')
        return 1
    finally:
        conn.close()


def run_update() -> int:
    cfg = load_config()
    ok, errors = validate_fetch_config(cfg)
    if not ok:
        for err in errors:
            print(f'- {err}')
        return 1

    api_key = cfg['YOUTUBE_API_KEY']
    channel_id = cfg['CHANNEL_ID']
    db_path = cfg['DB_PATH'] or 'creator_core.db'

    conn = get_connection(db_path)
    init_db(conn)

    try:
        existing_video_ids = get_all_video_ids(conn)
        if not existing_video_ids:
            print('Database is empty. Falling back to full fetch.')
            conn.close()
            return run_fetch()

        print('Checking uploads playlist for new videos...')
        uploads_playlist_id = get_uploads_playlist_id(api_key, channel_id)
        upload_items = get_playlist_video_ids(api_key, uploads_playlist_id)

        new_video_ids: list[str] = []
        for item in upload_items:
            video_id = item['video_id']
            if video_id not in existing_video_ids:
                new_video_ids.append(video_id)
            else:
                if new_video_ids:
                    break

        creator_comments: list[dict] = []

        if new_video_ids:
            print(f'Fetching details for {len(new_video_ids)} new videos...')
            video_details = get_video_details(api_key, new_video_ids)
            upsert_videos(conn, video_details)

            print('Fetching creator comments for new videos...')
            for video_id in new_video_ids:
                creator_comments.extend(get_creator_comments(api_key, video_id, channel_id))
            insert_creator_comments(conn, creator_comments)
        else:
            print('No new videos found.')

        print('Update complete.')
        print(f'New videos: {len(new_video_ids)}')
        print(f'Comments fetched: {len(creator_comments)}')
        return 0
    except YouTubeAPIError as exc:
        print(f'YouTube API error: {exc}')
        return 1
    finally:
        conn.close()


def run_refresh() -> int:
    cfg = load_config()
    ok, errors = validate_fetch_config(cfg)
    if not ok:
        for err in errors:
            print(f'- {err}')
        return 1

    api_key = cfg['YOUTUBE_API_KEY']
    channel_id = cfg['CHANNEL_ID']
    db_path = cfg['DB_PATH'] or 'creator_core.db'
    refresh_limit = get_refresh_video_limit(cfg)

    conn = get_connection(db_path)
    init_db(conn)

    try:
        latest_video_ids = get_latest_video_ids(conn, refresh_limit)
        if latest_video_ids:
            video_details = get_video_details(api_key, latest_video_ids)
            upsert_videos(conn, video_details)
        else:
            video_details = []

        print('Refreshing playlists and playlist mappings...')
        playlists, mappings = refresh_playlists_and_mappings(api_key, channel_id)
        upsert_playlists(conn, playlists)
        upsert_playlist_videos(conn, mappings)

        print('Refresh complete.')
        print(f'Videos refreshed: {len(video_details)}')
        print(f'Playlists processed: {len(playlists)}')
        print(f'Playlist mappings processed: {len(mappings)}')
        return 0
    except YouTubeAPIError as exc:
        print(f'YouTube API error: {exc}')
        return 1
    finally:
        conn.close()


def run_status() -> int:
    cfg = load_config()
    db_path = cfg['DB_PATH'] or 'creator_core.db'

    conn = get_connection(db_path)
    init_db(conn)
    counts = get_status_counts(conn)
    conn.close()

    print('Database status')
    print('---------------')
    print(f"Videos:    {counts['videos']}")
    print(f"Playlists: {counts['playlists']}")
    print(f"Comments:  {counts['comments']}")
    return 0


def main() -> int:
    if len(sys.argv) < 2:
        print_help()
        return 1

    command = sys.argv[1].strip().lower()

    if command == 'setup':
        return run_setup()
    if command == 'fetch':
        return run_fetch()
    if command == 'update':
        return run_update()
    if command == 'refresh':
        return run_refresh()
    if command == 'status':
        return run_status()

    print(f'Unknown command: {command}')
    print_help()
    return 1


if __name__ == '__main__':
    raise SystemExit(main())

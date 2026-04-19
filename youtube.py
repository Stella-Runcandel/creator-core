from __future__ import annotations

import re
from typing import Dict, List, Optional

import requests

BASE_URL = 'https://www.googleapis.com/youtube/v3'


class YouTubeAPIError(Exception):
    pass


def _api_get(endpoint: str, params: dict) -> dict:
    url = f'{BASE_URL}/{endpoint}'
    response = requests.get(url, params=params, timeout=30)
    if response.status_code != 200:
        try:
            payload = response.json()
            msg = payload.get('error', {}).get('message', response.text)
        except ValueError:
            msg = response.text
        raise YouTubeAPIError(f'API request failed ({response.status_code}): {msg}')

    try:
        return response.json()
    except ValueError as exc:
        raise YouTubeAPIError('Invalid JSON returned by YouTube API') from exc


def resolve_channel_id(api_key: str, handle_or_id: str) -> Optional[str]:
    value = (handle_or_id or '').strip()
    if not value:
        return None

    if value.startswith('UC') and len(value) >= 20:
        return value

    handle = value.lstrip('@')
    data = _api_get('channels', {
        'part': 'id',
        'forHandle': handle,
        'key': api_key,
    })
    items = data.get('items') or []
    if not items:
        return None
    return items[0].get('id')


def get_uploads_playlist_id(api_key: str, channel_id: str) -> str:
    data = _api_get('channels', {
        'part': 'contentDetails',
        'id': channel_id,
        'key': api_key,
    })
    items = data.get('items') or []
    if not items:
        raise YouTubeAPIError('Channel not found. Check CHANNEL_ID in .env.')

    details = items[0].get('contentDetails') or {}
    related = details.get('relatedPlaylists') or {}
    uploads_id = related.get('uploads')
    if not uploads_id:
        raise YouTubeAPIError('Could not locate uploads playlist for this channel.')
    return uploads_id


def _parse_duration_seconds(duration: str) -> Optional[int]:
    # Very small ISO-8601 duration parser for YouTube format (e.g. PT1H2M3S)
    if not duration:
        return None
    match = re.fullmatch(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', duration)
    if not match:
        return None
    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    seconds = int(match.group(3) or 0)
    return (hours * 3600) + (minutes * 60) + seconds


def get_playlist_video_ids(api_key: str, playlist_id: str) -> List[dict]:
    results: List[dict] = []
    page_token = None

    while True:
        params = {
            'part': 'snippet,contentDetails',
            'playlistId': playlist_id,
            'maxResults': 50,
            'key': api_key,
        }
        if page_token:
            params['pageToken'] = page_token

        data = _api_get('playlistItems', params)
        for item in data.get('items') or []:
            content = item.get('contentDetails') or {}
            snippet = item.get('snippet') or {}
            video_id = content.get('videoId')
            if not video_id:
                continue
            results.append({
                'video_id': video_id,
                'position': int(snippet.get('position') or 0),
            })

        page_token = data.get('nextPageToken')
        if not page_token:
            break

    return results


def get_video_details(api_key: str, video_ids: List[str]) -> List[dict]:
    details: List[dict] = []
    if not video_ids:
        return details

    for start in range(0, len(video_ids), 50):
        chunk = video_ids[start:start + 50]
        data = _api_get('videos', {
            'part': 'snippet,statistics,contentDetails',
            'id': ','.join(chunk),
            'maxResults': 50,
            'key': api_key,
        })

        for item in data.get('items') or []:
            snippet = item.get('snippet') or {}
            stats = item.get('statistics') or {}
            content = item.get('contentDetails') or {}
            thumbs = snippet.get('thumbnails') or {}
            thumb = (thumbs.get('high') or thumbs.get('medium') or thumbs.get('default') or {}).get('url')

            details.append({
                'video_id': item.get('id'),
                'title': snippet.get('title', ''),
                'description': snippet.get('description', ''),
                'thumbnail_url': thumb,
                'published_at': snippet.get('publishedAt', ''),
                'view_count': int(stats.get('viewCount', 0) or 0),
                'like_count': int(stats.get('likeCount', 0) or 0),
                'comment_count': int(stats.get('commentCount', 0) or 0),
                'duration_seconds': _parse_duration_seconds(content.get('duration', '')),
            })

    return [v for v in details if v.get('video_id')]


def get_channel_playlists(api_key: str, channel_id: str) -> List[dict]:
    playlists: List[dict] = []
    page_token = None

    while True:
        params = {
            'part': 'snippet',
            'channelId': channel_id,
            'maxResults': 50,
            'key': api_key,
        }
        if page_token:
            params['pageToken'] = page_token

        data = _api_get('playlists', params)
        for item in data.get('items') or []:
            snippet = item.get('snippet') or {}
            playlists.append({
                'playlist_id': item.get('id'),
                'playlist_name': snippet.get('title', ''),
            })

        page_token = data.get('nextPageToken')
        if not page_token:
            break

    return [p for p in playlists if p.get('playlist_id')]


def get_playlist_mappings(api_key: str, playlist_id: str) -> List[dict]:
    mappings = []
    items = get_playlist_video_ids(api_key, playlist_id)
    for item in items:
        mappings.append({
            'playlist_id': playlist_id,
            'video_id': item['video_id'],
            'position': item['position'],
        })
    return mappings


def get_creator_comments(api_key: str, video_id: str, creator_channel_id: str) -> List[dict]:
    comments: List[dict] = []
    page_token = None

    while True:
        params = {
            'part': 'snippet',
            'videoId': video_id,
            'maxResults': 100,
            'textFormat': 'plainText',
            'key': api_key,
        }
        if page_token:
            params['pageToken'] = page_token

        try:
            data = _api_get('commentThreads', params)
        except YouTubeAPIError as exc:
            # Comments may be disabled; ignore those videos gracefully.
            if 'commentsDisabled' in str(exc) or 'has disabled comments' in str(exc):
                return comments
            raise

        for thread in data.get('items') or []:
            snippet = (thread.get('snippet') or {}).get('topLevelComment', {}).get('snippet', {})
            author_channel_id = ((snippet.get('authorChannelId') or {}).get('value'))
            if author_channel_id != creator_channel_id:
                continue

            top_level = thread.get('snippet', {}).get('topLevelComment', {})
            comment_id = top_level.get('id')
            if not comment_id:
                continue

            comments.append({
                'comment_id': comment_id,
                'video_id': video_id,
                'text': snippet.get('textDisplay', ''),
                'published_at': snippet.get('publishedAt', ''),
            })

        page_token = data.get('nextPageToken')
        if not page_token:
            break

    return comments

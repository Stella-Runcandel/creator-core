PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS videos (
    video_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    thumbnail_url TEXT,
    published_at TEXT NOT NULL,
    view_count INTEGER NOT NULL DEFAULT 0 CHECK (view_count >= 0),
    like_count INTEGER NOT NULL DEFAULT 0 CHECK (like_count >= 0),
    comment_count INTEGER NOT NULL DEFAULT 0 CHECK (comment_count >= 0),
    duration_seconds INTEGER CHECK (duration_seconds >= 0)
);

CREATE TABLE IF NOT EXISTS playlists (
    playlist_id TEXT PRIMARY KEY,
    playlist_name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS playlist_videos (
    playlist_id TEXT NOT NULL,
    video_id TEXT NOT NULL,
    position INTEGER NOT NULL CHECK (position >= 0),
    PRIMARY KEY (playlist_id, video_id),
    UNIQUE (playlist_id, position),
    FOREIGN KEY (playlist_id) REFERENCES playlists (playlist_id)
        ON UPDATE CASCADE
        ON DELETE CASCADE,
    FOREIGN KEY (video_id) REFERENCES videos (video_id)
        ON UPDATE CASCADE
        ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS creator_comments (
    comment_id TEXT PRIMARY KEY,
    video_id TEXT NOT NULL,
    text TEXT NOT NULL,
    published_at TEXT NOT NULL,
    FOREIGN KEY (video_id) REFERENCES videos (video_id)
        ON UPDATE CASCADE
        ON DELETE CASCADE
);

-- Query optimization indexes
CREATE INDEX IF NOT EXISTS idx_videos_published_at
    ON videos (published_at DESC);

CREATE INDEX IF NOT EXISTS idx_videos_views
    ON videos (view_count DESC);

CREATE INDEX IF NOT EXISTS idx_videos_likes
    ON videos (like_count DESC);

CREATE INDEX IF NOT EXISTS idx_playlist_videos_video
    ON playlist_videos (video_id);

CREATE INDEX IF NOT EXISTS idx_playlist_videos_playlist_position
    ON playlist_videos (playlist_id, position);

CREATE INDEX IF NOT EXISTS idx_playlist_videos_playlist
    ON playlist_videos (playlist_id);

CREATE INDEX IF NOT EXISTS idx_creator_comments_video_published
    ON creator_comments (video_id, published_at DESC);

-- Optional future extension (only if needed later)
-- ALTER TABLE videos ADD COLUMN tags_json TEXT;

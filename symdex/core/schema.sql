-- SymDex database schema
-- Applied on every connection via storage.get_connection()

CREATE TABLE IF NOT EXISTS symbols (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    repo        TEXT NOT NULL,
    file        TEXT NOT NULL,
    name        TEXT NOT NULL,
    kind        TEXT NOT NULL,
    start_byte  INTEGER NOT NULL,
    end_byte    INTEGER NOT NULL,
    signature   TEXT,
    docstring   TEXT,
    embedding   BLOB
);

CREATE INDEX IF NOT EXISTS idx_symbols_repo_name ON symbols(repo, name);
CREATE INDEX IF NOT EXISTS idx_symbols_name ON symbols(name);
CREATE INDEX IF NOT EXISTS idx_symbols_repo_file ON symbols(repo, file);
CREATE INDEX IF NOT EXISTS idx_symbols_repo_kind ON symbols(repo, kind);

CREATE TABLE IF NOT EXISTS edges (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    caller_id   INTEGER NOT NULL REFERENCES symbols(id) ON DELETE CASCADE,
    callee_name TEXT NOT NULL,
    callee_file TEXT,
    UNIQUE(caller_id, callee_name, callee_file)
);

CREATE INDEX IF NOT EXISTS idx_edges_caller ON edges(caller_id);
CREATE INDEX IF NOT EXISTS idx_edges_callee ON edges(callee_name);

CREATE TABLE IF NOT EXISTS files (
    repo        TEXT NOT NULL,
    path        TEXT NOT NULL,
    hash        TEXT NOT NULL,
    indexed_at  DATETIME NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (repo, path)
);

CREATE TABLE IF NOT EXISTS repos (
    name         TEXT PRIMARY KEY,
    root_path    TEXT NOT NULL,
    db_path      TEXT NOT NULL UNIQUE,
    last_indexed DATETIME
);

CREATE TABLE IF NOT EXISTS routes (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    repo        TEXT NOT NULL,
    file        TEXT NOT NULL,
    method      TEXT NOT NULL,
    path        TEXT NOT NULL,
    handler     TEXT,
    start_byte  INTEGER NOT NULL,
    end_byte    INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_routes_repo ON routes(repo);
CREATE INDEX IF NOT EXISTS idx_routes_repo_path ON routes(repo, path);
CREATE INDEX IF NOT EXISTS idx_routes_method ON routes(repo, method);

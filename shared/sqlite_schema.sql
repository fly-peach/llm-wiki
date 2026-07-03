-- LLM Wiki — SQLite Schema
-- 完全基于 Karpathy 三层架构重新设计
-- 位于 .llmwiki/index.db，可删除重建（派生索引）

PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

-- ═══════════════════════════════════════════════════════════════
-- 表 1: workspace — 工作区（一个文件夹 = 一个 workspace）
-- ═══════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS workspace (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL,                 -- 文件夹名
    description TEXT DEFAULT '',
    kind        TEXT NOT NULL DEFAULT 'wiki',  -- 'wiki' | 'course'
    user_id     TEXT NOT NULL,
    created_at  TEXT DEFAULT (datetime('now')),
    UNIQUE(user_id)
);

-- ═══════════════════════════════════════════════════════════════
-- 表 2: documents — 文档元数据（raw + wiki + asset 三类合一）
-- ═══════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS documents (
    id              TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    user_id         TEXT NOT NULL,
    filename        TEXT NOT NULL,              -- 如 'my-note.md'
    title           TEXT,                        -- frontmatter 或推导
    path            TEXT DEFAULT '/' NOT NULL,   -- 目录，如 '/wiki/entities/'
    relative_path   TEXT NOT NULL,               -- 相对路径，UNIQUE
    source_kind     TEXT NOT NULL                -- 'raw' | 'wiki' | 'asset'
        CHECK (source_kind IN ('raw', 'wiki', 'asset')),
    file_type       TEXT NOT NULL,               -- 扩展名
    file_size       INTEGER DEFAULT 0,
    document_number INTEGER,                     -- 自增编号
    status          TEXT DEFAULT 'pending'       -- 'pending'|'processing'|'ready'|'failed'
        CHECK (status IN ('pending', 'processing', 'ready', 'failed')),
    page_count      INTEGER,                     -- PDF/表格页数
    content         TEXT,                        -- 全量文本内容（Markdown 原文）
    tags            TEXT DEFAULT '[]',           -- JSON: ["tag1", "tag2"]
    date            TEXT,
    metadata        TEXT,                        -- JSON: {source_url, clip_kind, ...}
    error_message   TEXT,
    version         INTEGER DEFAULT 0,           -- 乐观锁
    parser          TEXT,                        -- 'text'|'opendataloader'|'mistral'|...
    content_hash    TEXT,                        -- SHA256
    mtime_ns        INTEGER,                     -- 文件修改时间（纳秒）
    last_indexed_at TEXT,
    stale_since     TEXT,
    highlights      TEXT DEFAULT '[]',           -- JSON 高亮数组
    entity_type     TEXT,                        -- (Karpathy新增) 实体类型
    domain          TEXT,                        -- (Karpathy新增) 跨域标签
    created_at      TEXT DEFAULT (datetime('now')),
    updated_at      TEXT DEFAULT (datetime('now')),
    UNIQUE(relative_path)
);

-- ═══════════════════════════════════════════════════════════════
-- 表 3: document_pages — 分页内容（PDF/表格）
-- ═══════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS document_pages (
    id          TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    document_id TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    page        INTEGER NOT NULL,
    content     TEXT NOT NULL,
    elements    TEXT,                             -- JSON 结构化元素
    UNIQUE(document_id, page)
);

-- ═══════════════════════════════════════════════════════════════
-- 表 4: document_chunks — 文本分块（搜索/RAG 用）
-- ═══════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS document_chunks (
    id                TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    document_id       TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index       INTEGER NOT NULL,
    content           TEXT NOT NULL,              -- 物化内容（source + annotations）
    source_content    TEXT NOT NULL DEFAULT '',   -- 原始不可变块文本
    annotations_text  TEXT,                       -- 高亮/注释脚注
    has_highlight     INTEGER NOT NULL DEFAULT 0,
    page              INTEGER,
    start_char        INTEGER,                    -- 文档内起始字符偏移
    token_count       INTEGER NOT NULL,
    header_breadcrumb TEXT,                       -- 如 '研究 > ML > 神经网络'
    created_at        TEXT DEFAULT (datetime('now')),
    UNIQUE(document_id, chunk_index)
);

-- ═══════════════════════════════════════════════════════════════
-- 表 5: document_references — 知识图谱边
-- 只有 wiki→wiki (links_to) 和 wiki→raw (cites)
-- 不存储 raw→raw 边（由 Karpathy 的设计决定）
-- ═══════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS document_references (
    id                  TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    source_document_id  TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    target_document_id  TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    reference_type      TEXT NOT NULL             -- 'cites' | 'links_to'
        CHECK (reference_type IN ('cites', 'links_to')),
    page                INTEGER,
    UNIQUE(source_document_id, target_document_id, reference_type)
);

-- ═══════════════════════════════════════════════════════════════
-- FTS5 全文搜索虚拟表（由触发器自动同步）
-- ═══════════════════════════════════════════════════════════════
CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
    content,
    content='document_chunks',
    content_rowid='rowid',
    tokenize='porter unicode61'
);

-- FTS 同步触发器
CREATE TRIGGER IF NOT EXISTS chunks_fts_insert AFTER INSERT ON document_chunks BEGIN
    INSERT INTO chunks_fts(rowid, content) VALUES (new.rowid, new.content);
END;
CREATE TRIGGER IF NOT EXISTS chunks_fts_delete AFTER DELETE ON document_chunks BEGIN
    INSERT INTO chunks_fts(chunks_fts, rowid, content) VALUES('delete', old.rowid, old.content);
END;
CREATE TRIGGER IF NOT EXISTS chunks_fts_update AFTER UPDATE ON document_chunks BEGIN
    INSERT INTO chunks_fts(chunks_fts, rowid, content) VALUES('delete', old.rowid, old.content);
    INSERT INTO chunks_fts(rowid, content) VALUES (new.rowid, new.content);
END;

-- ═══════════════════════════════════════════════════════════════
-- 索引
-- ═══════════════════════════════════════════════════════════════
CREATE INDEX IF NOT EXISTS idx_documents_relative_path ON documents(relative_path);
CREATE INDEX IF NOT EXISTS idx_documents_path ON documents(path);
CREATE INDEX IF NOT EXISTS idx_documents_source_kind ON documents(source_kind);
CREATE INDEX IF NOT EXISTS idx_documents_status ON documents(status);
CREATE INDEX IF NOT EXISTS idx_documents_entity_type ON documents(entity_type);
CREATE INDEX IF NOT EXISTS idx_documents_domain ON documents(domain);
CREATE INDEX IF NOT EXISTS idx_chunks_doc ON document_chunks(document_id);
-- 部分索引：加速"只看有高亮的块"查询
CREATE INDEX IF NOT EXISTS idx_chunks_annotated
  ON document_chunks(document_id) WHERE has_highlight = 1;
CREATE INDEX IF NOT EXISTS idx_refs_source ON document_references(source_document_id);
CREATE INDEX IF NOT EXISTS idx_refs_target ON document_references(target_document_id);

import sqlite3

db_path = r"\\192.168.18.3\YunYing\DataApp\DataApp1.0\wiki\.llmwiki\index.db"
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row

cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
print("=== 表 ===")
for r in cur.fetchall():
    print(f"  {r[0]}")

cur = conn.execute("SELECT COUNT(*) as cnt FROM documents")
print(f"文档: {cur.fetchone()['cnt']}")

cur = conn.execute("SELECT COUNT(*) as cnt FROM document_chunks")
print(f"分块: {cur.fetchone()['cnt']}")

cur = conn.execute("SELECT COUNT(*) as cnt FROM chunks_fts")
print(f"FTS条目: {cur.fetchone()['cnt']}")

cur = conn.execute("SELECT id, filename, source_kind, status FROM documents LIMIT 5")
print("\n=== 文档 ===")
for r in cur.fetchall():
    print(f"  {r['id'][:8]}  {r['filename']:25s} kind={r['source_kind']:6s} status={r['status']}")

# FTS 搜索测试
print("\n=== FTS搜索 'data' ===")
try:
    cur2 = conn.execute(
        "SELECT snippet(chunks_fts, 0, '<b>', '</b>', '', 24) FROM chunks_fts WHERE chunks_fts MATCH 'data' LIMIT 3"
    )
    for r in cur2.fetchall():
        print(f"  {r[0]}")
except Exception as e:
    print(f"  FTS错误: {e}")

conn.close()

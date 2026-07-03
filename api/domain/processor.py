"""文档处理器 — 统一入口

将 status='pending' 的文档异步处理：提取文本 → 分块 → 写入数据库。
"""

from __future__ import annotations

from pathlib import Path

from domain.file_types import EXTRACTION, is_simple_text
from services.chunker import chunk_text


async def process_document(
    svc,
    ws_id: str,
    doc_id: str,
    workspace: Path,
) -> bool:
    """处理单个文档：提取 → 分块 → 标记 ready。"""
    doc = await svc.get_document(doc_id)
    if not doc:
        return False

    # 乐观锁：claim status pending → processing
    ok = await svc.update_document(doc_id, doc["version"], status="processing")
    if not ok:
        return False

    # 重新读取最新版本
    doc = await svc.get_document(doc_id)

    try:
        file_type = doc["file_type"].lower()
        file_path = workspace / doc["relative_path"]

        # ── 提取文本 ──────────────────────────────────
        content: str = ""

        if is_simple_text(file_type):
            if file_path.exists():
                content = file_path.read_text(encoding="utf-8")
            else:
                content = doc.get("content", "")

        elif file_type == "pdf":
            from services.pdf_extract import extract_pdf_text
            content, page_count = await extract_pdf_text(file_path)
            if page_count:
                await _update_and_refresh(svc, doc_id, page_count=page_count)

        elif file_type in ("html", "htm"):
            if file_path.exists():
                html = file_path.read_text(encoding="utf-8")
                from html_parser.parser import Parser
                result = Parser(html).parse()
                content = result.content
            else:
                content = doc.get("content", "")

        elif file_type in ("pptx", "ppt", "docx", "doc"):
            content = doc.get("content", "") or f"[Office 文档待提取: {doc['filename']}]"

        else:
            content = doc.get("content", "") or f"[{file_type} 文件: {doc['filename']}]"

        # ── 更新文档内容 ───────────────────────────────
        doc = await _update_and_refresh(svc, doc_id, content=content)

        # ── 文本分块 ───────────────────────────────────
        if content and content.strip():
            chunks = chunk_text(content)
            await _save_chunks(svc, ws_id, doc_id, chunks)

        # ── 标记完成 ───────────────────────────────────
        from domain.watcher import _now_iso
        await _update_and_refresh(
            svc, doc_id,
            status="ready",
            last_indexed_at=_now_iso(),
            error_message=None,
        )

        return True

    except Exception as e:
        await _update_and_refresh(
            svc, doc_id,
            status="failed",
            error_message=str(e)[:500],
        )
        import traceback
        traceback.print_exc()
        return False


async def _update_and_refresh(svc, doc_id: str, **fields) -> dict | None:
    """更新文档并返回最新版本。"""
    doc = await svc.get_document(doc_id)
    if not doc:
        return None
    ok = await svc.update_document(doc_id, doc["version"], **fields)
    if ok:
        return await svc.get_document(doc_id)
    return doc


async def _save_chunks(
    svc,
    ws_id: str,
    doc_id: str,
    chunks: list,
) -> None:
    """将分块写入 document_chunks 表（先删旧块，再批量插入）。"""
    db = await svc._get_db(ws_id)

    from infra.db.sqlite import serialized_write
    async with serialized_write():
        # 删除旧块（FTS5 触发器自动同步）
        await db.execute(
            "DELETE FROM document_chunks WHERE document_id = ?",
            (doc_id,),
        )

        # 批量插入
        for ch in chunks:
            await db.execute(
                """INSERT INTO document_chunks
                   (document_id, chunk_index, content, source_content,
                    page, start_char, token_count, header_breadcrumb)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    doc_id,
                    ch.index,
                    ch.content,
                    ch.content,
                    ch.page,
                    ch.start_char,
                    ch.token_count,
                    ch.header_breadcrumb,
                ),
            )

        await db.commit()

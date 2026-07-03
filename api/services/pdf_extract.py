"""PDF 文本提取（双后端策略）

支持两种后端：
  - opendataloader: 默认，本地提取（需 LibreOffice 辅助）
  - mistral: 调用 Mistral OCR API（需 API Key）

当前为 stub 实现，后续 Phase 可接入真实后端。
"""

from __future__ import annotations

from pathlib import Path


async def extract_pdf_text(
    file_path: str | Path,
    backend: str = "opendataloader",
    api_key: str = "",
) -> tuple[str, int]:
    """从 PDF 文件中提取纯文本。

    参数:
        file_path: PDF 文件路径
        backend: 'opendataloader' 或 'mistral'
        api_key: Mistral API Key（仅 mistral 后端需要）

    返回:
        (提取的文本, 页数)
    """
    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(f"PDF file not found: {file_path}")

    if backend == "mistral":
        return await _extract_mistral(file_path, api_key)
    else:
        return await _extract_opendataloader(file_path)


async def _extract_opendataloader(file_path: Path) -> tuple[str, int]:
    """使用 opendataloader 提取 PDF（stub）。

    实际实现依赖 LibreOffice 命令行转换 PDF → 文本。
    或使用 PyMuPDF (fitz) / pdfplumber 等 Python 库。
    """
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(str(file_path))
        pages: list[str] = []
        for page in doc:
            pages.append(page.get_text())
        doc.close()
        return "\n\n".join(pages), len(pages)
    except ImportError:
        pass

    # fallback: 尝试 pdfplumber
    try:
        import pdfplumber
        with pdfplumber.open(str(file_path)) as pdf:
            pages = [p.extract_text() or "" for p in pdf.pages]
        return "\n\n".join(pages), len(pages)
    except ImportError:
        pass

    # 无法提取：返回提示
    return (
        f"[PDF 文本待提取: {file_path.name}]\n"
        "安装 PyMuPDF 或 pdfplumber 以启用 PDF 提取:\n"
        "  pip install PyMuPDF",
        0,
    )


async def _extract_mistral(
    file_path: Path,
    api_key: str,
) -> tuple[str, int]:
    """使用 Mistral OCR API 提取 PDF（stub）。

    需要 MISTRAL_API_KEY 环境变量。
    """
    if not api_key:
        raise ValueError("MISTRAL_API_KEY is required for Mistral PDF backend")

    # TODO: 集成 Mistral OCR
    # client = Mistral(api_key=api_key)
    # response = client.ocr.process(...)
    return (
        f"[Mistral OCR 待接入: {file_path.name}]",
        0,
    )

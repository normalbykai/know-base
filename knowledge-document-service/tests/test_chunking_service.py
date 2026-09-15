from app.schemas.document import DocumentBlock, DocumentModel
from app.services.chunking_service import DocumentChunker


def test_chunker_preserves_heading_path_pages_and_structured_block_boundary() -> None:
    model = DocumentModel(
        document_id="doc-1",
        title="员工手册",
        blocks=[
            DocumentBlock(id="b1", type="heading", level=1, text="员工制度", page=1),
            DocumentBlock(id="b2", type="heading", level=2, text="请假", page=1),
            DocumentBlock(id="b3", type="paragraph", text="员工应提前提交请假申请。", page=1),
            DocumentBlock(id="b4", type="paragraph", text="病假需要提供证明。", page=2),
            DocumentBlock(id="b5", type="table", content="| 类型 | 天数 |\n| --- | --- |", page=2),
        ],
    )

    chunks = DocumentChunker(max_characters=100).chunk(model)

    assert len(chunks) == 2
    assert chunks[0].heading_path == "员工制度 > 请假"
    assert chunks[0].page_start == 1 and chunks[0].page_end == 2
    assert "请假申请" in chunks[0].content
    assert chunks[1].content.startswith("| 类型")
    assert chunks[1].page_start == chunks[1].page_end == 2


def test_chunker_splits_long_content_without_losing_text() -> None:
    content = "甲" * 250
    model = DocumentModel(document_id="doc-1", title="长文", blocks=[DocumentBlock(id="b1", type="paragraph", text=content)])

    chunks = DocumentChunker(max_characters=100).chunk(model)

    assert [len(chunk.content) for chunk in chunks] == [100, 100, 50]
    assert "".join(chunk.content for chunk in chunks) == content

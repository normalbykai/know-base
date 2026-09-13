from app.services.normalizer import DocumentNormalizer


def test_normalizer_isolates_parser_shape() -> None:
    raw = {"title": "员工手册", "page_count": 1, "content_list": [{"type": "title", "text": "第一章", "page_idx": 1}, {"type": "text", "text": "欢迎", "page_idx": 1}]}
    model = DocumentNormalizer().normalize("doc-1", "handbook.pdf", "application/pdf", raw, "")
    assert model.document_id == "doc-1"
    assert model.blocks[0].type == "heading"
    assert model.blocks[1].text == "欢迎"


def test_normalizer_falls_back_to_markdown() -> None:
    model = DocumentNormalizer().normalize("doc-1", "a.pdf", "application/pdf", {}, "# 标题\n正文")
    assert [block.type for block in model.blocks] == ["heading", "paragraph"]

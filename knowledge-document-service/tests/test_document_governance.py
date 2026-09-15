import pytest
from fastapi import HTTPException

from app.api.documents import validate_upload
from app.workers.parse_worker import error_code_for


@pytest.mark.parametrize(
    ("filename", "content_type"),
    [("handbook.pdf", "application/pdf"), ("scan.PNG", "image/png"), ("photo.jpeg", "image/jpeg")],
)
def test_validate_upload_accepts_supported_document_types(filename: str, content_type: str) -> None:
    """前端限制不是安全边界，API 也必须接受当前解析链路支持的格式。"""
    validate_upload(filename, content_type)


@pytest.mark.parametrize(
    ("filename", "content_type"),
    [("notes.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"), ("renamed.pdf", "image/png")],
)
def test_validate_upload_rejects_unsupported_or_mismatched_types(filename: str, content_type: str) -> None:
    with pytest.raises(HTTPException) as exc:
        validate_upload(filename, content_type)
    assert exc.value.status_code == 415


def test_parse_error_codes_are_stable_for_common_remediation_paths() -> None:
    assert error_code_for(RuntimeError("DEEPSEEK_API_KEY is not configured")) == "PARSER_NOT_CONFIGURED"
    assert error_code_for(RuntimeError("DeepSeek vision parsing currently supports PDF and image files only")) == "UNSUPPORTED_FILE"
    assert error_code_for(RuntimeError("MinerU service unavailable or parsing request failed")) == "PARSER_UNAVAILABLE"

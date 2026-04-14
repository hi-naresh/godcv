import io
import markdown
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from backend.db.models import ExportRequest

router = APIRouter(prefix="/api/export", tags=["export"])

CSS = """
@page { size: A4; margin: 8mm; }
body { font-family: Georgia, "Times New Roman", serif; font-size: 11px; line-height: 1.4; color: #111; }
h1 { font-size: 1.15rem; font-weight: 800; margin: 0.5rem 0 0.3rem; }
h2 { font-size: 1.05rem; font-weight: 800; margin: 0.5rem 0 0.3rem; }
h3 { font-size: 0.95rem; font-weight: 700; margin: 0.5rem 0 0.3rem; }
p { margin: 0.2rem 0; }
ul, ol { margin: 0.2rem 0 0.2rem 1.1rem; }
li { margin: 0.1rem 0; }
a { color: #0066cc; }
strong { font-weight: 700; }
hr { border: 0; border-top: 1px solid #bbb; margin: 0.3rem 0; }
"""


@router.post("/pdf")
async def export_pdf(request: ExportRequest):
    try:
        from weasyprint import HTML
        html_content = markdown.markdown(request.markdown, extensions=["tables", "fenced_code"])
        full_html = f"<html><head><style>{CSS}</style></head><body>{html_content}</body></html>"
        pdf_bytes = HTML(string=full_html).write_pdf()
        return StreamingResponse(
            io.BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename=resume.pdf"},
        )
    except ImportError:
        raise HTTPException(status_code=501, detail="WeasyPrint not installed. Use browser print instead.")

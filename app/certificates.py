
from datetime import date
from pathlib import Path
from uuid import uuid4

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfgen import canvas


PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = PROJECT_ROOT / "generated_certificates"


def generate_certificate(
    recipient_name: str,
    course_name: str,
    issuer: str,
    completion_date: date,
) -> Path:
    """Generate one PDF certificate and return its file path."""

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Generate a unique filename; never use the recipient's name as a path.
    filename = f"certificate_{uuid4().hex}.pdf"
    output_path = OUTPUT_DIR / filename

    page_width, page_height = landscape(A4)
    pdf = canvas.Canvas(str(output_path), pagesize=(page_width, page_height))

    # Draw the certificate border.
    margin = 28
    pdf.setStrokeColor(colors.HexColor("#234E70"))
    pdf.setLineWidth(3)
    pdf.rect(
        margin,
        margin,
        page_width - 2 * margin,
        page_height - 2 * margin,
    )

    # Draw the certificate title.
    pdf.setFillColor(colors.HexColor("#234E70"))
    pdf.setFont("Helvetica-Bold", 28)
    pdf.drawCentredString(
        page_width / 2,
        page_height - 100,
        "CERTIFICATE OF COMPLETION",
    )

    # Introductory text.
    pdf.setFillColor(colors.black)
    pdf.setFont("Helvetica", 15)
    pdf.drawCentredString(
        page_width / 2,
        page_height - 155,
        "This certificate is proudly presented to",
    )

    # Recipient's name.
    pdf.setFillColor(colors.HexColor("#234E70"))
    pdf.setFont("Helvetica-Bold", 25)
    pdf.drawCentredString(
        page_width / 2,
        page_height - 205,
        recipient_name,
    )

    # Course details.
    pdf.setFillColor(colors.black)
    pdf.setFont("Helvetica", 14)
    pdf.drawCentredString(
        page_width / 2,
        page_height - 250,
        f"for successfully completing {course_name}",
    )

    pdf.setFont("Helvetica", 12)
    pdf.drawCentredString(
        page_width / 2,
        page_height - 295,
        f"Issued by: {issuer}",
    )
    pdf.drawCentredString(
        page_width / 2,
        page_height - 320,
        f"Completion date: {completion_date.isoformat()}",
    )

    # Finish the PDF document.
    pdf.showPage()
    pdf.save()

    return output_path

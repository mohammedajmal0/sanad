"""Render the Markdown corpus to PDFs, the format Najm's documents really arrive in.

Run (the two libraries are only needed here, so they are not project dependencies):
    uv run --with markdown --with plutoprint python retrieval/build_corpus.py
Then upload retrieval/build/docs/ to /Volumes/sanad/ai/docs/ (see retrieval/README.md).
"""

import csv
import shutil
from pathlib import Path

import markdown
import plutoprint

HERE = Path(__file__).parent
CORPUS = HERE / "corpus"
OUT = HERE / "build" / "docs"

CSS = """body { font-family: sans-serif; font-size: 11pt; line-height: 1.45; margin: 2cm; }
.meta { color: #555; font-size: 9pt; border-bottom: 1px solid #ccc; padding-bottom: 6pt; }"""


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    rows = list(csv.DictReader((CORPUS / "manifest.csv").read_text().splitlines()))
    for row in rows:
        body = markdown.markdown((CORPUS / f"{row['doc_id']}.md").read_text())
        dept = {"it": "IT"}.get(row["department"], row["department"].replace("_", " ").title())
        meta = (
            f"Najm Supply Co. · {dept} · "
            f"{'Policy' if row['doc_type'] == 'policy' else 'Knowledge base'} · "
            f"Effective {row['effective_date']} · {row['doc_id']}"
        )
        html = f"<html><style>{CSS}</style><body><p class='meta'>{meta}</p>{body}</body></html>"
        book = plutoprint.Book(plutoprint.PAGE_SIZE_A4)
        book.load_html(html)
        book.write_to_pdf(str(OUT / f"{row['doc_id']}.pdf"))
    shutil.copy(CORPUS / "manifest.csv", OUT / "manifest.csv")  # metadata travels with the PDFs
    print(f"{len(rows)} PDFs + manifest.csv in {OUT}")


if __name__ == "__main__":
    main()

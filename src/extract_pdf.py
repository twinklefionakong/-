import json
from pathlib import Path

import pymupdf
import pdfplumber


INPUT_DIR = Path("documents")
OUTPUT_DIR = Path("data/parsed_pages")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def clean_cell(cell):
    if cell is None:
        return ""
    return " ".join(str(cell).split())


def extract_pdf(pdf_path):
    output_path = OUTPUT_DIR / f"{pdf_path.stem}.jsonl"

    if output_path.exists():
        print(f"跳过已解析：{pdf_path.name}")
        return

    text_document = pymupdf.open(pdf_path)

    with pdfplumber.open(pdf_path) as table_document, output_path.open(
        "w", encoding="utf-8"
    ) as output_file:

        total_pages = len(text_document)
        table_count = 0

        for page_index in range(total_pages):
            pdf_page = page_index + 1

            # 提取正文，并尽量按照页面阅读顺序排列
            text = text_document[page_index].get_text(
                "text",
                sort=True,
            ).strip()

            # 提取本页表格
            table_settings = {
                "vertical_strategy": "text",
                "horizontal_strategy": "text",
                "snap_tolerance": 3,
                "join_tolerance": 3,
                "intersection_tolerance": 3,
                "text_tolerance": 3,
            }

            raw_tables = table_document.pages[
                page_index
            ].extract_tables(table_settings)

            tables = []


            for table_index, raw_table in enumerate(raw_tables, start=1):
                rows = [
                    [clean_cell(cell) for cell in row]
                    for row in raw_table
                    if row
                ]

                if rows:
                    tables.append(
                        {
                            "table_id": (
                                f"{pdf_path.stem}_"
                                f"p{pdf_page}_t{table_index}"
                            ),
                            "rows": rows,
                        }
                    )
                    table_count += 1

            record = {
                "source_file": pdf_path.name,
                "report_id": pdf_path.stem,
                "pdf_page": pdf_page,
                "text": text,
                "tables": tables,
            }

            output_file.write(
                json.dumps(record, ensure_ascii=False) + "\n"
            )

            if pdf_page % 10 == 0 or pdf_page == total_pages:
                print(
                    f"{pdf_path.name}: "
                    f"{pdf_page}/{total_pages} 页"
                )

    text_document.close()

    print(
        f"完成：{pdf_path.name}，"
        f"共 {total_pages} 页，识别 {table_count} 张表格"
    )
    print(f"输出：{output_path}")


pdf_files = sorted(INPUT_DIR.glob("*.pdf"))

if not pdf_files:
    raise SystemExit("documents 中没有找到 PDF 文件")

for pdf_file in pdf_files:
    extract_pdf(pdf_file)

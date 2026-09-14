import sys
sys.path.insert(0, r'/')
import fitz
from services.pdf_pages import render_pdf_pair_at_common_dpi
from services.Preprocess import preprocess_pipeline
from services.page_matcher import match_pages, get_match_summary

# Create PDFs
doc1 = fitz.open()
page1 = doc1.new_page(width=72*8.5, height=72*11)
page1.insert_text((100, 100), 'SHEET 1 REV A', fontsize=12)
pdf_bytes1 = doc1.tobytes()
doc1.close()

doc2 = fitz.open()
page2 = doc2.new_page(width=72*8.5, height=72*11)
page2.insert_text((100, 100), 'SHEET 1 REV B', fontsize=12)
page2.insert_text((100, 200), 'DIM 100', fontsize=12)
pdf_bytes2 = doc2.tobytes()
doc2.close()

print('PDFs created, rendering at common DPI...')
old_pages, new_pages, common_dpi, size_mismatch, mismatch = render_pdf_pair_at_common_dpi(pdf_bytes1, pdf_bytes2)
print('Common DPI:', common_dpi)
print('Size mismatch:', size_mismatch)
print('Old pages:', len(old_pages))
print('New pages:', len(new_pages))

print('Preprocessing...')
old_gray = [preprocess_pipeline(p['image'])['gray'] for p in old_pages]
new_gray = [preprocess_pipeline(p['image'])['gray'] for p in new_pages]

print('Matching pages...')
old_nums = [p['page_number'] for p in old_pages]
new_nums = [p['page_number'] for p in new_pages]
matches = match_pages(old_gray, new_gray, old_nums, new_nums)
summary = get_match_summary(matches)
print('Match summary:', summary)
print('Done!')
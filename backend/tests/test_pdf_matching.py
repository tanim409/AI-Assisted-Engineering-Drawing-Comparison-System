import sys
sys.path.insert(0, r'/')
import fitz
from services.pdf_pages import pdf_bytes_render_title_block_crops, pdf_bytes_get_page_metadata
from services.page_matcher import extract_signatures_from_crops, match_pages_from_signatures, get_match_summary

doc1 = fitz.open()
for i in range(2):
    page = doc1.new_page(width=72*8.5, height=72*11)
    page.insert_text((500, 750), f'SHEET {i+1} REV A', fontsize=12)
pdf1 = doc1.tobytes()
doc1.close()

doc2 = fitz.open()
for i in range(2):
    page = doc2.new_page(width=72*8.5, height=72*11)
    page.insert_text((500, 750), f'SHEET {i+1} REV B', fontsize=12)
pdf2 = doc2.tobytes()
doc2.close()

print('PDF metadata:')
meta1 = pdf_bytes_get_page_metadata(pdf1)
meta2 = pdf_bytes_get_page_metadata(pdf2)
for m in meta1:
    print('  Page {}: {}x{} in'.format(m["page_number"], m["width_in"], m["height_in"]))

print('Title-block crops:')
crops1 = pdf_bytes_render_title_block_crops(pdf1)
crops2 = pdf_bytes_render_title_block_crops(pdf2)
for c in crops1:
    print('  Page {}: crop shape {}'.format(c["page_number"], c["crop"].shape))

print('Signatures:')
sigs1 = extract_signatures_from_crops(crops1)
sigs2 = extract_signatures_from_crops(crops2)
for s in sigs1:
    print('  Page {}: "{}" (conf={:.1f})'.format(s.page_number, s.signature, s.ocr_confidence))

print('Matching:')
matches = match_pages_from_signatures(sigs1, sigs2)
summary = get_match_summary(matches)
print('  Matched: {}, Added: {}, Removed: {}'.format(summary["total_pages_matched"], summary["pages_added"], summary["pages_removed"]))
for m in matches:
    print('  OLD {} <-> NEW {}: {} ({})'.format(m.old_page_number, m.new_page_number, m.match_method, m.match_score))
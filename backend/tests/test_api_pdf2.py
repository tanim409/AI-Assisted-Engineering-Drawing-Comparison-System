import sys
sys.path.insert(0, r'/')
from fastapi.testclient import TestClient
from main import app
import fitz

client = TestClient(app)

# Create a simple PDF with text in title block region (bottom-right)
doc = fitz.open()
page = doc.new_page(width=72*8.5, height=72*11)
page.insert_text((500, 750), 'SHEET 1 REV A', fontsize=12)
pdf_bytes = doc.tobytes()
doc.close()

# Create another PDF with a change in title block
doc = fitz.open()
page = doc.new_page(width=72*8.5, height=72*11)
page.insert_text((500, 750), 'SHEET 1 REV B', fontsize=12)
page.insert_text((100, 200), 'DIM 100', fontsize=12)
pdf_bytes2 = doc.tobytes()
doc.close()

print('Testing /api/compare with PDFs...')
response = client.post('/api/compare', files={
    'old_drawing': ('test1.pdf', pdf_bytes, 'application/pdf'),
    'new_drawing': ('test2.pdf', pdf_bytes2, 'application/pdf'),
})
print('Status:', response.status_code)
if response.status_code == 200:
    data = response.json()
    print('Report ID:', data['report_id'])
    print('Total pages:', data['total_pages'])
    print('Page matching:', data['page_matching'])
    for p in data['pages']:
        pn = p.get('page_number')
        ps = p.get('page_status')
        pm = p.get('page_match_method')
        ch = len(p.get('changes', []))
        print('  Page {}: status={}, method={}, changes={}'.format(pn, ps, pm, ch))
else:
    print('Error:', response.text)
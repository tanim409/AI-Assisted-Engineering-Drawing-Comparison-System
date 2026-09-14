import sys
sys.path.insert(0, r'/')
from fastapi.testclient import TestClient
from main import app
import fitz

client = TestClient(app)

doc1 = fitz.open()
page1 = doc1.new_page(width=72*8.5, height=72*11)
page1.insert_text((500, 750), 'SHEET 1 REV A', fontsize=12)
pdf1 = doc1.tobytes()
doc1.close()

doc2 = fitz.open()
page2 = doc2.new_page(width=72*8.5, height=72*11)
page2.insert_text((500, 750), 'SHEET 1 REV B', fontsize=12)
page2.insert_text((100, 200), 'DIM 100', fontsize=12)
pdf2 = doc2.tobytes()
doc2.close()

r = client.post('/api/compare', files={
    'old_drawing': ('test1.pdf', pdf1, 'application/pdf'),
    'new_drawing': ('test2.pdf', pdf2, 'application/pdf'),
})
print('Status:', r.status_code)
if r.status_code == 200:
    data = r.json()
    print('Report ID:', data['report_id'])
    print('Total pages:', data['total_pages'])
    for p in data['pages']:
        pn = p.get('page_number')
        ps = p.get('page_status')
        pm = p.get('page_match_method')
        ch = len(p.get('changes', []))
        print('  Page {}: status={}, method={}, changes={}'.format(pn, ps, pm, ch))
else:
    print('Error:', r.text)
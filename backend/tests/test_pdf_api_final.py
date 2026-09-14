import sys
sys.path.insert(0, r'/')
from fastapi.testclient import TestClient
from main import app
import fitz

client = TestClient(app)

doc1 = fitz.open()
for i in range(2):
    page = doc1.new_page(width=72*8.5, height=72*11)
    page.insert_text((500, 750), 'SHEET {} REV A'.format(i+1), fontsize=12)
    page.insert_text((100, 200), 'DIM {}mm'.format(100+i*10), fontsize=10)
pdf1 = doc1.tobytes()
doc1.close()

doc2 = fitz.open()
for i in range(2):
    page = doc2.new_page(width=72*8.5, height=72*11)
    page.insert_text((500, 750), 'SHEET {} REV B'.format(i+1), fontsize=12)
    page.insert_text((100, 200), 'DIM {}mm'.format(120+i*10), fontsize=10)
pdf2 = doc2.tobytes()
doc2.close()

print('Testing PDF API...')
r = client.post('/api/compare', files={
    'old_drawing': ('old.pdf', pdf1, 'application/pdf'),
    'new_drawing': ('new.pdf', pdf2, 'application/pdf'),
})
print('Status:', r.status_code)
if r.status_code == 200:
    data = r.json()
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
    print('Error:', r.text)
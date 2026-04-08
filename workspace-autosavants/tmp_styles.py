from docx import Document
from pathlib import Path
p=Path(r"C:\Users\Qiang\.openclaw\media\outbound\42abaf42-c0fb-4d74-be24-460b98b5494c.docx")
d=Document(p)
out=Path(r"C:\Users\Qiang\.openclaw\workspace-autosavants\tmp_assignment_template_styles.txt")
with out.open('w',encoding='utf-8') as f:
    for i,para in enumerate(d.paragraphs,1):
        txt=(para.text or '').replace('\n',' ').strip()
        if txt:
            f.write(f"{i:03d}\t{para.style.name}\t{txt}\n")
print('ok')

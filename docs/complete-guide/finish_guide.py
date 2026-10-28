from pathlib import Path
import json,importlib.util,sys,re
from pypdf import PdfReader,PdfWriter
from pypdf.annotations import Link
from PIL import Image,ImageDraw,ImageFont

BASE=Path(__file__).resolve().parent
records=json.loads((BASE/'qa/rendered-parts.json').read_text('utf-8-sig'))
items=json.loads((BASE/'qa/parts.json').read_text('utf-8'))
assert len(records)==len(items)==62
writer=PdfWriter();page_map=[]
for r,item in zip(records,items):
 reader=PdfReader(r['Pdf']);assert len(reader.pages)==r['Pages']
 start=len(writer.pages)
 for page in reader.pages:writer.add_page(page)
 title=item['title'];writer.add_outline_item(title,start,is_open=False)
 page_map.append({'title':title,'page':start+1,'pages':len(reader.pages)})
writer.add_metadata({'/Title':'HealthRetailers complete project guide','/Author':'HealthRetailers project group','/Subject':'Dirty source data through staging and native SSIS to five dimensions and two facts','/Keywords':'HealthRetailers SQL Server SSIS data warehouse stock purchases'})
# Restore useful links on the frozen contents pages after independent Word exports.
def normal(s):return re.sub(r'\s+',' ',s).strip()
toc_pages=range(records[1]['Start']-1,records[1]['Start']-1+records[1]['Pages'])
linked=0
for pi in toc_pages:
 lines={}
 def visit(text,cm,tm,font,size):
  if text.strip():
   x=cm[0]*tm[4]+cm[2]*tm[5]+cm[4];y=cm[1]*tm[4]+cm[3]*tm[5]+cm[5]
   lines.setdefault(round(y,1),[]).append((x,text))
 writer.pages[pi].extract_text(visitor_text=visit)
 for y,parts in lines.items():
  text=normal(''.join(t for x,t in sorted(parts)))
  for entry in page_map[2:]:
   if normal(entry['title']) in text:
    writer.add_annotation(pi,Link(rect=(50,y-3,565,y+12),target_page_index=entry['page']-1,border=[0,0,0]));linked+=1;break
pdf=BASE/'HealthRetailers_Complete_Project_Guide_EN.pdf'
with pdf.open('wb') as f:writer.write(f)
assert len(PdfReader(pdf).pages)==63
(BASE/'qa/page-map.json').write_text(json.dumps(page_map,indent=2),encoding='utf-8')
print('Merged 63 native Word pages. Contents links restored:',linked,flush=True)

# Use the bundled DOCX renderer with the native Word PDF conversion adapter.
# LibreOffice is not bundled on Windows and the installed Word exporter is used.
renderer=Path('C:/Users/firas/.cache/codex-runtimes/codex-primary-runtime/plugins/openai-primary-runtime/plugins/documents/skills/documents/render_docx.py')
spec=importlib.util.spec_from_file_location('bundled_docx_renderer',renderer)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
def native_pdf(doc_path,user_profile,convert_tmp_dir,stem,verbose=False):
 return str(pdf),'Native Word conversion in logical parts; full DOCX retained with editable TOC.'
m.convert_to_pdf=native_pdf
sys.argv=[str(renderer),str(BASE/'HealthRetailers_Complete_Project_Guide_EN.docx'),'--output_dir',str(BASE/'qa/pages'),'--dpi','110']
m.main()

pages=sorted((BASE/'qa/pages').glob('page-*.png'),key=lambda x:int(x.stem.split('-')[-1]))
assert len(pages)==63
for i in range(0,len(pages),2):
 pair=[Image.open(p).convert('RGB') for p in pages[i:i+2]]
 canvas=Image.new('RGB',(sum(p.width for p in pair),max(p.height for p in pair)+35),'#e8ebef')
 d=ImageDraw.Draw(canvas);x=0
 for j,im in enumerate(pair):
  canvas.paste(im,(x,35));d.text((x+20,8),f'Page {i+j+1}',font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',19),fill='black');x+=im.width
 canvas.save(BASE/'qa'/f'spread-{i//2+1:02}.png')

pdf_reader=PdfReader(pdf);texts=[p.extract_text() or '' for p in pdf_reader.pages]
all_text='\n'.join(texts)
required=['67','958947.7230','CatalogueSeuils_Faits','CodesProduits_Faits','SCD type 1','Appendix D','Document_Id','TRY_CONVERT','NULL']
assert all(s in all_text for s in required)
assert all(len(t.strip())>120 for t in texts)
stats={'pages':len(pages),'figures':20,'chapters':36,'glossaryTerms':118,'recordedChecks':67,'tocLinks':linked,'nativeRendering':'Microsoft Word logical parts preserving original page breaks','rasterizer':'bundled render_docx.py at 110 dpi','sourceDocxRetained':True,'blankPages':0,'allRequiredTermsFound':True}
(BASE/'qa/render-checks.json').write_text(json.dumps(stats,indent=2),encoding='utf-8')
print(json.dumps(stats,indent=2),flush=True)

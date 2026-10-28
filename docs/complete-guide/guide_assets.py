from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import json,math,textwrap

BASE=Path(__file__).resolve().parent
ASSETS=BASE/'assets';ASSETS.mkdir(exist_ok=True)
FONTS=Path('C:/Windows/Fonts')
NAVY='#223C55';INK='#182735';BLUE='#EAF2F8';GREEN='#EAF4ED';GREY='#F2F3F5';GOLD='#FCF1D8';RED='#F9E8E7'
def font(n,bold=False):return ImageFont.truetype(str(FONTS/('arialbd.ttf' if bold else 'arial.ttf')),n)

def diagram(name,nodes,edges,w=1700,h=1000,fs=32):
 im=Image.new('RGB',(w,h),'white');d=ImageDraw.Draw(im)
 # Each node is key, label, x, y, width, height, optional color.
 boxes={n[0]:n for n in nodes};labels=[]
 for edge in edges:
  a,b=edge[:2];label=edge[2] if len(edge)>2 else ''
  aa,bb=boxes[a],boxes[b]
  ax,ay,aw,ah=aa[2:6];bx,by,bw,bh=bb[2:6]
  if by>=ay+ah-5:
   start=(ax+aw/2,ay+ah);end=(bx+bw/2,by)
   mid=(start[1]+end[1])/2+(edge[3] if len(edge)>3 else 0)
   pts=[start,(start[0],mid),(end[0],mid),end]
  elif bx>=ax+aw:
   start=(ax+aw,ay+ah/2);end=(bx,by+bh/2)
   mid=(start[0]+end[0])/2;pts=[start,(mid,start[1]),(mid,end[1]),end]
  else:
   start=(ax+aw/2,ay);end=(bx+bw/2,by+bh)
   mid=(start[1]+end[1])/2;pts=[start,(start[0],mid),(end[0],mid),end]
  d.line(pts,fill=NAVY,width=4,joint='curve')
  p,q=pts[-2],pts[-1];ang=math.atan2(q[1]-p[1],q[0]-p[0]);r=15
  d.polygon([q,(q[0]-r*math.cos(ang-.45),q[1]-r*math.sin(ang-.45)),(q[0]-r*math.cos(ang+.45),q[1]-r*math.sin(ang+.45))],fill=NAVY)
  if label:
   f=font(max(23,fs-7));bbox=d.textbbox((0,0),label,font=f);tw=bbox[2];th=bbox[3]-bbox[1]
   x=(start[0]+end[0])/2
   if by>=ay+ah-5:y=mid
   elif bx>=ax+aw and tw+12<=bx-ax-aw:y=(start[1]+end[1])/2
   else:y=max(fs,ay-35)
   labels.append((x,y,tw,th,label,f))
 for x,y,tw,th,label,f in labels:
   d.rectangle((x-tw/2-8,y-th/2-5,x+tw/2+8,y+th/2+8),fill='white')
   d.text((x-tw/2,y-th/2-2),label,font=f,fill=INK)
 for n in nodes:
  _,label,x,y,nw,nh,*color=n;fill=color[0] if color else BLUE
  d.rounded_rectangle((x,y,x+nw,y+nh),radius=12,fill=fill,outline=NAVY,width=3)
  f=font(fs);lines=[]
  for raw in label.split('\n'):
   words=raw.split();line=''
   for word in words:
    candidate=(line+' '+word).strip()
    if d.textlength(candidate,font=f)>nw-36 and line:lines.append(line);line=word
    else:line=candidate
   lines.append(line)
  lineh=fs+7;yy=y+(nh-lineh*len(lines))/2
  for line in lines:
   d.text((x+(nw-d.textlength(line,font=f))/2,yy),line,font=f,fill=INK);yy+=lineh
 path=ASSETS/(name+'.png');im.save(path);return path

def flow_from_xml(task,name=None,subset=None):
 cs=task['components'];cs=[c for c in cs if subset is None or c['id'] in subset]
 keys={c['id']:c for c in cs};edges=[];rank={k:0 for k in keys}
 for p in task['paths']:
  a=p['startId'].split('.Outputs[')[0];b=p['endId'].split('.Inputs[')[0]
  if a in keys and b in keys:edges.append((a,b,p['name']))
 for _ in cs:
  for a,b,_ in edges:rank[b]=max(rank[b],rank[a]+1)
 groups={}
 for c in cs:groups.setdefault(rank[c['id']],[]).append(c)
 nodes=[];w=1700;step=185;boxw=440;boxh=126
 positions={};parents={k:[] for k in keys};children={k:[] for k in keys}
 for a,b,_ in edges:parents[b].append(a);children[a].append(b)
 for level,items in sorted(groups.items()):
  items=sorted(items,key=lambda c:c['name'])
  for i,c in enumerate(items):
   # Keep main source/transform path in the centre, INSERT left, UPDATE right.
   x=630
   if len(items)>1:x=60+i*(w-boxw-120)/(len(items)-1)
   if len(parents[c['id']])==1:
    parent=parents[c['id']][0]
    if len(children[parent])==1:x=positions[parent]
   if 'OLEDBDestination' in c['type'] or 'OLEDBCommand' in c['type']:
    fill=GREEN if 'Destination' in c['type'] else GOLD
   elif 'ConditionalSplit' in c['type']:fill=GOLD
   else:fill=BLUE
   nodes.append((c['id'],c['name'],int(x),35+level*step,boxw,boxh,fill))
   positions[c['id']]=int(x)
 nice=[]
 for a,b,label in edges:
  low=label.lower()
  if 'sans correspondance' in low or 'no match' in low:label='No match  INSERT'
  elif 'avec correspondance' in low or 'match output' in low:label='Match'
  elif label in ['UPDATE','INSERT']:pass
  elif 'factures' in low:label='Accepted'
  elif 'other' in low or 'brouillons' in low:label='Excluded'
  else:label=''
  nice.append((a,b,label))
 return diagram(name or task['name'],nodes,nice,w=w,h=65+(max(rank.values())+1)*step,fs=31)

def create_assets():
 inventory=json.loads((BASE/'inventory.json').read_text('utf-8'))
 tasks={t['name']:t for t in inventory['ETL_SA_DW.dtsx']['tasks']}
 for name in ['alim_dim_client','alim_dim_produit','alim_dim_fournisseur','alim_dim_paiement','alim_fait_stock_actuel']:
  flow_from_xml(tasks[name])
 p=tasks['alim_fait_achats']
 ids={c['id'] for c in p['components'] if not (c['name'].startswith('INSERT') or c['name'].startswith('UPDATE') or c['name']=='Recherche du fait existant' or 'valeurs modifiees' in c['name'])}
 flow_from_xml(p,'purchase_selection',ids)
 diagram('journey',[
  ('a','17 dirty CSV files\n244300 source rows',30,70,350,170,BLUE),('b','Staging database\nraw text and caches',460,70,350,170,GREY),('c','SSIS transformations\n6 native Data Flows',890,70,350,170,GOLD),('d','Warehouse\n5 dimensions  2 facts',1320,70,350,170,GREEN)], [('a','b'),('b','c'),('c','d')],h=320,fs=35)
 diagram('architecture',[
  ('o','data/original\nUnmodified source bytes',70,40,650,150,BLUE),('t','data/transport\nUTF16 CSV copies',980,40,650,150,BLUE),
  ('s','SA_Health_Dimensions\n17 raw staging tables',525,300,650,150,GREY),('c','Technical preparation\n2 caches and exclusion log',40,560,650,150,GOLD),
  ('d','DW_Health_Dimensions\n5 dimensions and 2 facts',995,560,650,150,GREEN)], [('o','t','Encoding conversion'),('t','s','EL_SI_SA'),('s','c','Preparation'),('s','d','Dimensions'),('c','d','Fact Data Flows')],h=780,fs=36)
 diagram('setup_execution',[
  ('a','One time setup\nSQL schemas  views  functions\nprocedures  SSIS build',50,70,650,190,GREY),('b','Repeated execution\nMaster.dtsx',1000,70,650,190,BLUE),
  ('c','SQL Server databases\ncreated and ready',50,400,650,150,GREEN),('d','Loaded and validated\nwarehouse tables',1000,400,650,150,GREEN)], [('a','c'),('c','b','Ready for execution'),('b','d')],h=630,fs=36)
 diagram('transport',[
  ('a','Read original bytes\nUTF8 BOM or CP1252 as needed',100,40,700,145,BLUE),('b','Parse CSV cells\nCorrect delimiter and quote rules',100,270,700,145,BLUE),
  ('c','Write UTF16 transport\nSame parsed values and duplicates',100,500,700,145,GREEN),('d','SHA256 checks\nOriginal bytes and\nmultiset of cell values',1050,270,550,230,GOLD)], [('a','b'),('b','c'),('a','d','Byte hash'),('b','d','Cell hash')],h=720,fs=36)
 diagram('staging',[
  ('a','Reset raw staging\nExisting raw rows are cleared',50,50,450,150,GREY),('b','Flat File Source\nUnicode and text qualifier',625,50,450,150,BLUE),('c','OLE DB Destination\nNVARCHAR staging columns',1200,50,450,150,GREEN)], [('a','b','Success'),('b','c','Rows')],h=300,fs=36)
 diagram('master',[
  ('a','EL_SI_SA\nExecute Package',30,70,350,175,BLUE),('b','Calendrier\nExecute SQL',460,70,350,175,GREY),('c','ETL_SA_DW\nExecute Package',890,70,350,175,BLUE),('d','Verification\nExecute SQL',1320,70,350,175,GREEN)], [('a','b','Success'),('b','c','Success'),('c','d','Success')],h=330,fs=37)
 diagram('etl_control',[
  ('p','alim_dim_paiement',25,30,385,125,BLUE),('s','alim_dim_fournisseur',445,30,385,125,BLUE),('c','alim_dim_client',865,30,385,125,BLUE),('r','alim_dim_produit',1285,30,385,125,BLUE),
  ('a','Preparation des deux faits\nCaches  guards  stale key removal',475,310,750,155,GREY),('b','alim_fait_stock_actuel\nNative Data Flow',475,600,750,150,GOLD),('d','alim_fait_achats\nNative Data Flow',475,875,750,150,GOLD)], [('p','a'),('s','a'),('c','a'),('r','a'),('a','b','Success'),('b','d','Success')],h=1090,fs=35)
 diagram('schema',[
  ('p','dim_produit\nPK Product_Id\nLibelle  Famille  Marque',20,30,500,215,BLUE),('t','dim_temps\nPK DateKey\nDate  year  month  quarter',600,30,500,215,BLUE),('s','dim_fournisseur\nPK Fournisseur_Id\nNom',1180,30,500,215,BLUE),
  ('st','fait_stock_actuel\nPK and FK Product_Id\nNullable FK DateKey\nQuantiteActuelle\nQuantiteAlerte  EstSousSeuil',30,440,680,330,GREEN),('ac','fait_achats\nPK Id  Document_Id\nFK DateKey  Product_Id\nFK Fournisseur_Id\nQuantiteAchetee  MontantAchat_HT',990,440,680,330,GREEN),
  ('cl','dim_client\nPK Company_Id\nNom  TypeClient\nEstClientIdentifie',120,990,640,240,GREY),('pa','dim_paiement\nPK PaymentMode_Id\nPaymentModeName\nAvailable for future facts',940,990,640,240,GREY)], [('p','st','',-70),('p','ac','',-35),('t','st','Optional date',0),('t','ac','',35),('s','ac','',70)],h=1290,fs=34)
 diagram('product_matching',[
  ('e','Latest product event\nProduct id  code  label',20,30,500,150,BLUE),('l','Document item descriptions\nStock id to product id\nHTML cleaned',600,30,500,150,BLUE),('c','Products catalogue\nDistinct complete variants\nSame code may repeat',1180,30,500,150,BLUE),
  ('a','Candidate matches\n1 code  2 item label  3 event label',460,320,780,155,GOLD),('b','Choose one catalogue variant\nPriority  family completeness\nCode  ExportId',460,620,780,155,GOLD),('d','Final product attributes\nSafe label fallbacks\nFamily and brand or explicit unknown',460,920,780,180,GREEN)], [('e','a'),('l','a'),('c','a'),('a','b'),('b','d')],h=1170,fs=36)
 diagram('upsert',[
  ('s','Incoming business row',580,30,540,120,BLUE),('l','Lookup existing warehouse key',500,250,700,125,BLUE),
  ('i','INSERT new row\nOLE DB Destination',30,510,600,155,GREEN),('c','Conditional Split\nCompare all attributes\nNULL safe comparison',1010,510,650,170,GOLD),
  ('u','UPDATE existing row\nOLE DB Command',1050,840,570,155,GREEN),('n','Unchanged\nNo write is required',280,840,570,155,GREY)], [('s','l'),('l','i','No match'),('l','c','Match'),('c','u','Changed'),('c','n','Equal')],h=1060,fs=37)
 diagram('purchase_joins',[
  ('i','DocumentItem_SA\nId  Document_Id\nProductStock_Id  Quantity\nPrixTotalHt',20,40,500,230,BLUE),('d','Documents_SA\nId  Transaction_Id\nDocumentDate  State\nType 20  TotalNetHt',600,40,500,230,BLUE),('t','Transactions_SA\nId  Company_Id',1180,40,500,230,BLUE),
  ('p','ProductStocks_SA\nId to Product_Id',20,510,500,180,BLUE),('v','v_source_achats\nOne candidate per invoice line\nTyped keys  dates and measures\nDocument discount allocation',720,510,960,235,GREEN)], [('i','d'),('d','t'),('i','p','ProductStock_Id = Id'),('p','v'),('d','v'),('t','v')],h=830,fs=34)
 diagram('prepare_facts',[
  ('r','Raw staging data\nCatalogue and product events',30,40,650,150,BLUE),('c','Rebuild indexed caches\nCatalogueSeuils_Faits\nCodesProduits_Faits',1000,40,650,195,GREY),
  ('v','Check mandatory keys and values\nInvalid core business line fails the load',475,370,750,150,GOLD),('p','Clear exclusions and remove stale facts\nOnly keys no longer eligible are deleted',475,680,750,170,GOLD)], [('r','c'),('c','v'),('v','p')],h=920,fs=37)
 diagram('reclassify',[
  ('a','Validated invoice\nIts lines exist in fait_achats',30,70,500,190,GREEN),('b','Source becomes draft\nState changes from 1 to 0',600,70,500,190,GOLD),('c','Preparation removes its facts\nDraft rows go to Rejets_Faits',1180,70,500,190,GREY),
  ('d','Restore validated source\nThe invoice lines are inserted again',470,490,760,190,GREEN)], [('a','b'),('b','c'),('c','d','Next valid load')],h=760,fs=35)
 return ASSETS

if __name__=='__main__':create_assets();print('Guide diagrams generated from implementation metadata.')

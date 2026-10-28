"""Configure Amal's native SSIS project; preserve the original CSV bytes."""
from pathlib import Path
import csv, hashlib, json, re, shutil, subprocess, uuid, xml.etree.ElementTree as E
ROOT=Path(__file__).resolve().parents[1]
P=ROOT/'HealthRetailers_SSIS'
D='{www.microsoft.com/SqlServer/Dts}'
S='{www.microsoft.com/SqlServer/SSIS}'
E.register_namespace('DTS',D[1:-1]); E.register_namespace('SSIS',S[1:-1]); E.register_namespace('xsi','http://www.w3.org/2001/XMLSchema-instance')
settings=json.loads((ROOT/'settings.json').read_text('utf-8-sig')) if (ROOT/'settings.json').exists() else {'Server':'localhost','StagingDatabase':'SA_Health_Dimensions','WarehouseDatabase':'DW_Health_Dimensions'}
for k,v in settings.items():
    if not re.fullmatch(r'[\w\\.\-]+',v): raise ValueError('Invalid setting: '+k)
def upstream(path):
    b=subprocess.check_output(['git','show','3d52d4f48c66da6eccee05ee1050188ae1a4af6d:'+path],cwd=ROOT)
    return b.decode('utf-16' if b.startswith(b'\xff\xfe') else 'utf-8-sig').replace('\r\n','\n')
def write(path,s): path.write_text('\n'.join(line.rstrip() for line in s.splitlines())+'\n',encoding='utf-8-sig')
def connection(s):
    if 'Initial Catalog=' in s:
        s=s.replace('Initial Catalog=SA_Health','Initial Catalog='+settings['StagingDatabase']).replace('Initial Catalog=DW_Health','Initial Catalog='+settings['WarehouseDatabase'])
        if 'Data Source=' not in s:s='Data Source='+settings['Server']+';'+s
    return s
for d in ['data/original','data/transport','reports','docs']: (ROOT/d).mkdir(parents=True,exist_ok=True)
manifest=[]
for spec in json.loads((ROOT/'scripts/sources.json').read_text('utf-8-sig')):
    src=ROOT/'data/original'/spec['source']
    if not src.exists():
        original=ROOT.parent/'DataWarehouseProject_3AI4/ssis-sqlserver/data/original'/spec['source']
        shutil.copyfile(original,src)
    b=src.read_bytes()
    for enc in ['utf-8-sig','cp1252','cp850']:
        try: text=b.decode(enc);break
        except UnicodeDecodeError: pass
    delim=spec['delimiter']
    # Source files and SSIS managers use the same separators; preserve quoted cells.
    rows=list(csv.reader(text.splitlines(keepends=True),delimiter=delim))
    if len(rows[0])!=len(spec['columns']):
        delim=';' if delim==',' else ','
        rows=list(csv.reader(text.splitlines(keepends=True),delimiter=delim))
    if any(len(r)!=len(spec['columns']) for r in rows):raise ValueError('Column mismatch: '+spec['source'])
    dest=ROOT/'data/transport'/spec['transport']
    with dest.open('w',encoding='utf-16',newline='') as f:
        csv.writer(f,delimiter=spec['delimiter'],lineterminator='\r\n').writerows(rows)
    def rowhash(row):
        data=b''
        for cell in row:
            value=cell.encode('utf-16-le');data+=len(value).to_bytes(4,'little')+value
        return hashlib.sha256(data).hexdigest()
    content_hash=hashlib.sha256('\n'.join(sorted(rowhash(r) for r in rows[1:])).encode('ascii')).hexdigest()
    manifest.append(dict(spec,rows=len(rows)-1,encoding=enc,sha256=hashlib.sha256(b).hexdigest(),contentHash=content_hash))
    tree=E.ElementTree(E.fromstring(upstream('HealthRetailers_SSIS/'+spec['manager'])))
    for n in tree.iter():
        if D+'ConnectionString' in n.attrib:n.set(D+'ConnectionString',str(dest));n.set(D+'Unicode','True');n.set(D+'TextQualifier','_x0022_')
        if n.tag==D+'FlatFileColumn':n.set(D+'TextQualified','True')
        if n.get(D+'DataType') in ['129','302']:n.set(D+'DataType',{'129':'130','302':'303'}[n.get(D+'DataType')])
    tree.write(P/spec['manager'],encoding='utf-8',xml_declaration=True)
write(ROOT/'reports/source-manifest.json',json.dumps(manifest,ensure_ascii=False,indent=2))
for name,db in [('01_SA_Health.sql','StagingDatabase'),('02_DW_Health.sql','WarehouseDatabase')]:
    batches=[f"IF DB_ID(N'$({db})') IS NULL EXEC(N'CREATE DATABASE [$({db})]');",'GO',f'USE [$({db})];','GO','SET ANSI_NULLS ON; SET QUOTED_IDENTIFIER ON;','GO']
    functions=[]
    for batch in re.split(r'^GO\s*$',upstream('sql/'+name),flags=re.M|re.I):
        m=re.search(r'\bCREATE\s+(TABLE|FUNCTION|PROCEDURE)\b',batch,re.I)
        if not m:continue
        obj=batch[m.start():].strip()
        if m[1].upper()=='TABLE':
            if db=='WarehouseDatabase' and not re.match(r'CREATE TABLE \[dbo\]\.\[dim_',obj,re.I):continue
            obj=obj.replace('[varchar]','[nvarchar]')
            table=re.search(r'CREATE TABLE (\[dbo\]\.\[[^]]+\])',obj)[1]
            batches += [f"IF OBJECT_ID(N'{table}',N'U') IS NULL\n"+obj,'GO']
        else:functions.append(obj)
    write(ROOT/'sql'/name,'\n'.join(batches))
    if functions:
        source='\nGO\n'.join(functions)
        source=re.sub(r'CREATE\s+(FUNCTION|PROCEDURE)',r'CREATE OR ALTER \1',source,flags=re.I)
        source=source.replace("e.Libelle LIKE", "e.Libelle COLLATE Latin1_General_100_BIN2 LIKE")
        # Keep separate catalogue records even when Excel damaged multiple codes identically.
        source=source.replace('SELECT Code, Libelle, Famille, Marque, Libelle COLLATE','SELECT ROW_NUMBER() OVER (ORDER BY Code, Libelle, Famille, Marque) AS ExportId, Code, Libelle, Famille, Marque, Libelle COLLATE')
        source=source.replace('PARTITION BY LTRIM(RTRIM(p.Code)) ORDER BY (SELECT 1)', 'PARTITION BY LTRIM(RTRIM(p.Code)), p.[Libellé], p.Famille, p.Marque ORDER BY (SELECT 1)')
        source=source.replace('SELECT Product_Id, Code, prio, sans_famille','SELECT Product_Id, ExportId, Code, prio, sans_famille').replace('e.Code, 1 AS prio','e.ExportId, e.Code, 1 AS prio').replace('e.Code, 2, CASE','e.ExportId, e.Code, 2, CASE').replace('e.Code, 3, CASE','e.ExportId, e.Code, 3, CASE')
        source=source.replace('SELECT Product_Id, Code\n','SELECT Product_Id, ExportId, Code\n').replace('FROM (SELECT Product_Id, Code,','FROM (SELECT Product_Id, ExportId, Code,').replace('prio, sans_famille, Code)', 'prio, sans_famille, Code, ExportId)').replace('e.Code = b.Code','e.ExportId = b.ExportId')
        source=source.replace('LTRIM(RTRIM(p.Code)) AS Code','CAST(LTRIM(RTRIM(p.Code)) AS nvarchar(200)) AS Code')
        source=source.replace('ON e.Code = ev.cde','ON e.Code = ev.cde AND ((SELECT COUNT(*) FROM #exp z WHERE z.Code=e.Code)=1 OR e.k=ev.k)')
        source=source.replace("CHARINDEX(N'<', @s)","CHARINDEX(N'<', @s COLLATE Latin1_General_100_BIN2)").replace("CHARINDEX(N'>', @s, @a)","CHARINDEX(N'>', @s COLLATE Latin1_General_100_BIN2, @a)").replace("@b - @a + 1, N'')","@b - @a + 1, N' ')")
        source=source.replace('-- 3. Export Produits (une ligne par code, accents réparés une seule fois)','-- 3. Export Produits : conserver les lignes distinctes, même si le code a été endommagé.')
        write(ROOT/'sql/04_dimension_sources.sql',"USE [$(StagingDatabase)];\nGO\nSET ANSI_NULLS ON; SET QUOTED_IDENTIFIER ON;\nGO\n"+source+'\nGO\n')
calendar=upstream('sql/03_alim_dim_temps.sql').replace('USE DW_Health;','USE [$(WarehouseDatabase)];')
write(ROOT/'sql/03_alim_dim_temps.sql',calendar)
for file in P.iterdir():
    if file.suffix not in ['.dtsx','.conmgr','.dtproj'] or file.name in [x['manager'] for x in manifest]:continue
    text=upstream('HealthRetailers_SSIS/'+file.name)
    tree=E.ElementTree(E.fromstring(text))
    for n in tree.iter():
        for k,v in list(n.attrib.items()):
            if k.endswith('ConnectionString'):n.set(k,connection(v))
        if n.tag=='TargetServerVersion':n.text='SQLServer2022'
        if n.get(S+'Name')=='TargetServerVersion' and n.text=='170':n.text='160'
        if n.get(S+'Name')=='Value' and n.text:n.text=connection(n.text)
        if file.name=='EL_SI_SA.dtsx':
            for k in ['dataType','cachedDataType']:
                if n.get(k) in ['str','text']:n.set(k,{'str':'wstr','text':'nText'}[n.get(k)])
            for k in ['codePage','cachedCodePage']:n.attrib.pop(k,None)
        if n.tag=='property' and n.get('name') in ['Expression','FriendlyExpression'] and n.text and ' != ' in n.text:
            expr=n.text
            if n.get('name')=='FriendlyExpression':expr=expr.replace('NomFournisseur)', 'NomFournisseurDW)').replace('!= NomFournisseur','!= NomFournisseurDW')
            # Every comparison returns a definite Boolean, including NULL -> value updates.
            fun='[ISNULL]' if '#{' in expr else 'ISNULL'
            def safe(m):
                a,b=m[1],m[2]
                return f'({fun}({a}) ? !{fun}({b}) : ({fun}({b}) ? TRUE : {a} != {b}))'
            expr=re.sub(r'(\#\{[^}]+\}|\b\w+)\s*!=\s*(\#\{[^}]+\}|\b\w+)',safe,expr)
            n.text=expr
    if file.suffix=='.dtproj':tree.getroot().set('xmlns:xsd','http://www.w3.org/2001/XMLSchema')
    tree.write(file,encoding='utf-8',xml_declaration=True)
# Calendar and automatic checks are part of the Master execution.
tree=E.parse(P/'Master.dtsx'); root=tree.getroot()
cm=E.parse(P/'DW_Health.conmgr').getroot()
cmid='{E415D806-6083-41BF-973B-C756808208A1}'
cm.set(D+'DTSID',cmid);cm.set(D+'ObjectName','Warehouse');cm.set(D+'refId','Package.ConnectionManagers[Warehouse]')
cms=E.Element(D+'ConnectionManagers');cms.append(cm);root.insert(1,cms)
T='{www.microsoft.com/sqlserver/dts/tasks/sqltask}'
E.register_namespace('SQLTask',T[1:-1])
executables=root.find(D+'Executables'); constraints=root.find(D+'PrecedenceConstraints')
constraints.clear()
calendar_sql=re.sub(r'^GO\s*$','',re.sub(r'^USE .*?;\s*$','',calendar,flags=re.M),flags=re.M)
validation=(ROOT/'sql/99_verifications.sql').read_text('utf-8-sig')
validation=validation.replace('$(StagingDatabase)',settings['StagingDatabase']).replace('$(WarehouseDatabase)',settings['WarehouseDatabase'])
validation=re.sub(r'^GO\s*$','',re.sub(r'^USE .*?;\s*$','',validation,flags=re.M),flags=re.M)
for name,sql in [('Calendrier',calendar_sql),('Verification',validation)]:
    task=E.SubElement(executables,D+'Executable',{D+'refId':'Package\\'+name,D+'CreationName':'Microsoft.ExecuteSQLTask',D+'ExecutableType':'Microsoft.ExecuteSQLTask',D+'ObjectName':name,D+'DTSID':'{'+str(uuid.uuid4()).upper()+'}'})
    E.SubElement(task,D+'Variables')
    data=E.SubElement(task,D+'ObjectData')
    E.SubElement(data,T+'SqlTaskData',{T+'Connection':cmid,T+'SqlStatementSource':sql})
chain=['EL_SI_SA','Calendrier','ETL_SA_DW','Verification']
for i,(a,b) in enumerate(zip(chain,chain[1:])):
    E.SubElement(constraints,D+'PrecedenceConstraint',{D+'refId':f'Package.PrecedenceConstraints[Success{i}]',D+'DTSID':'{'+str(uuid.uuid4()).upper()+'}',D+'From':'Package\\'+a,D+'To':'Package\\'+b,D+'LogicalAnd':'True',D+'ObjectName':f'Success{i}'})
# Layout all four tasks vertically in the designer.
layout=root.find(D+'DesignTimeProperties')
if layout is not None:
    layout.text='''<Objects Version="8"><Package design-time-name="Package"><LayoutInfo><GraphLayout Capacity="4" xmlns="clr-namespace:Microsoft.SqlServer.IntegrationServices.Designer.Model.Serialization;assembly=Microsoft.SqlServer.IntegrationServices.Graph">'''+''.join(f'<NodeLayout Size="180,42" Id="Package\\{name}" TopLeft="100,{40+i*110}" />' for i,name in enumerate(chain))+'''</GraphLayout></LayoutInfo></Package></Objects>'''
tree.write(P/'Master.dtsx',encoding='utf-8',xml_declaration=True)
write(ROOT/'settings.example.json',json.dumps(settings,indent=2))
print('Configured 17 Unicode staging sources and five dimension tables.')

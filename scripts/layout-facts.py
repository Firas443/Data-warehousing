"""Preserve the product layout and place the generated SSIS components."""
from pathlib import Path
import subprocess,xml.etree.ElementTree as E
root=Path(__file__).resolve().parents[1]
D='{www.microsoft.com/SqlServer/Dts}'
G='{clr-namespace:Microsoft.SqlServer.IntegrationServices.Designer.Model.Serialization;assembly=Microsoft.SqlServer.IntegrationServices.Graph}'
E.register_namespace('DTS',D[1:-1])
original=E.fromstring(subprocess.check_output(['git','show','3d52d4f48c66da6eccee05ee1050188ae1a4af6d:HealthRetailers_SSIS/ETL_SA_DW.dtsx'],cwd=root).decode('utf-8-sig'))
layout=E.fromstring(original.find(D+'DesignTimeProperties').text)
graph=layout.find('Package/LayoutInfo/'+G+'GraphLayout')
facts=['alim_fait_stock_actuel','alim_fait_achats','alim_fait_ventes','alim_fait_encaissements','alim_fait_decaissements']
dimensions=['alim_dim_client','alim_dim_fournisseur','alim_dim_paiement']
for host in layout.findall('TaskHost'):
 if host.get('design-time-name') in {'Package\\'+name for name in dimensions}:layout.remove(host)
for i,name in enumerate(['Preparation des faits',*facts]):
 E.SubElement(graph,G+'NodeLayout',Size='250,42',Id='Package\\'+name,TopLeft=f'350,{180+i*110}')
graph.set('Capacity',str(len(graph.findall(G+'NodeLayout'))))
path=root/'HealthRetailers_SSIS/ETL_SA_DW.dtsx'
tree=E.parse(path)
for task in tree.getroot().find(D+'Executables'):
 task_name=task.get(D+'ObjectName')
 if task_name not in facts+dimensions:continue
 pipe=task.find(D+'ObjectData/pipeline')
 components=list(pipe.find('components')); edges=list(pipe.find('paths'))
 ranks={c.get('refId'):0 for c in components}
 for _ in components:
  for edge in edges:
   a=edge.get('startId').split('.Outputs[')[0];b=edge.get('endId').split('.Inputs[')[0]
   ranks[b]=max(ranks[b],ranks[a]+1)
 host=E.SubElement(layout,'TaskHost',{'design-time-name':task.get(D+'refId')})
 gi=E.SubElement(E.SubElement(host,'LayoutInfo'),G+'GraphLayout',Capacity=str(len(components)))
 rows={}
 for c in components:rows.setdefault(ranks[c.get('refId')],[]).append(c)
 width=max(len(row) for row in rows.values())
 for c in components:
  name=c.get('name');x=300
  if name.startswith('INSERT'):x=0
  if name.startswith('UPDATE') or 'valeurs modifiees' in name:x=600
  if name=='SA - conserver les lignes exclues':x=750
  if task_name in dimensions:
   row=rows[ranks[c.get('refId')]]
   x=(width-len(row))*175+row.index(c)*350
  E.SubElement(gi,G+'NodeLayout',Size='280,44',Id=c.get('refId'),TopLeft=f'{x},{25+ranks[c.get("refId")]*110}')
n=E.SubElement(tree.getroot(),D+'DesignTimeProperties')
n.text=E.tostring(layout,encoding='unicode')
tree.write(path,encoding='utf-8',xml_declaration=True)
path.write_text('\n'.join(line.rstrip() for line in path.read_text('utf-8').splitlines())+'\n',encoding='utf-8')
print('Product layout preserved; three dimension and five fact diagrams laid out.')

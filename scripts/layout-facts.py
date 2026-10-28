"""Restore Amal's designer layouts after the SSIS SDK saves runtime metadata."""
from pathlib import Path
import subprocess,xml.etree.ElementTree as E
root=Path(__file__).resolve().parents[1]
D='{www.microsoft.com/SqlServer/Dts}'
G='{clr-namespace:Microsoft.SqlServer.IntegrationServices.Designer.Model.Serialization;assembly=Microsoft.SqlServer.IntegrationServices.Graph}'
E.register_namespace('DTS',D[1:-1])
original=E.fromstring(subprocess.check_output(['git','show','3d52d4f48c66da6eccee05ee1050188ae1a4af6d:HealthRetailers_SSIS/ETL_SA_DW.dtsx'],cwd=root).decode('utf-8-sig'))
layout=E.fromstring(original.find(D+'DesignTimeProperties').text)
graph=layout.find('Package/LayoutInfo/'+G+'GraphLayout')
for name,xy in [('Preparation des deux faits','350,180'),('alim_fait_stock_actuel','350,300'),('alim_fait_achats','350,420')]:
 E.SubElement(graph,G+'NodeLayout',Size='250,42',Id='Package\\'+name,TopLeft=xy)
path=root/'HealthRetailers_SSIS/ETL_SA_DW.dtsx'
tree=E.parse(path)
for task in tree.getroot().find(D+'Executables'):
 if task.get(D+'ObjectName') not in ['alim_fait_stock_actuel','alim_fait_achats']:continue
 pipe=task.find(D+'ObjectData/pipeline')
 components=list(pipe.find('components')); edges=list(pipe.find('paths'))
 ranks={c.get('refId'):0 for c in components}
 for _ in components:
  for edge in edges:
   a=edge.get('startId').split('.Outputs[')[0];b=edge.get('endId').split('.Inputs[')[0]
   ranks[b]=max(ranks[b],ranks[a]+1)
 host=E.SubElement(layout,'TaskHost',{'design-time-name':task.get(D+'refId')})
 gi=E.SubElement(E.SubElement(host,'LayoutInfo'),G+'GraphLayout',Capacity=str(len(components)))
 for c in components:
  name=c.get('name');x=300
  if name.startswith('INSERT'):x=0
  if name.startswith('UPDATE') or 'valeurs modifiees' in name:x=600
  if name=='SA - conserver les lignes exclues':x=750
  E.SubElement(gi,G+'NodeLayout',Size='280,44',Id=c.get('refId'),TopLeft=f'{x},{25+ranks[c.get("refId")]*110}')
n=E.SubElement(tree.getroot(),D+'DesignTimeProperties')
n.text=E.tostring(layout,encoding='unicode')
tree.write(path,encoding='utf-8',xml_declaration=True)
path.write_text('\n'.join(line.rstrip() for line in path.read_text('utf-8').splitlines())+'\n',encoding='utf-8')
print('Original dimension layouts restored; two fact diagrams laid out.')

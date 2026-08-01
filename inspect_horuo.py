# -*- coding: utf-8 -*-
import importlib.util as u
spec = u.spec_from_file_location('rd', 'src/railway_data.py')
R = u.module_from_spec(spec); spec.loader.exec_module(R)
print('和若铁路 =', R.LINE_ORDER.get('和若铁路'))
print('昆玉站 邻接 =', R.GRAPH.get('昆玉站'))
print('和田站 邻接 =', R.GRAPH.get('和田站'))
# 检查昆玉站是否通过 SYN 接到和田
print('昆玉站 lines =', R.STATION_INFO.get('昆玉站', {}).get('lines'))
# 检查 v2.19 基线中的和若铁路
import importlib.machinery as m
def load(p):
    ldr=m.SourceFileLoader('mod',p); sp=u.spec_from_loader('mod',ldr); md=u.module_from_spec(sp); ldr.exec_module(md); return md
B=load('src/railway_data_v2.19.bak')
print('v2.19 和若铁路 =', B.LINE_ORDER.get('和若铁路'))
# 是否有站只在 SYN 里出现导致孤儿
orphan=[s for s in R.STATION_INFO if s not in R.GRAPH]
print('v2.20 orphan stations (in SI not in GRAPH):', orphan[:20], 'count=', len(orphan))

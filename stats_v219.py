# -*- coding: utf-8 -*-
import importlib.machinery as m, importlib.util as u
def load(p):
    ldr = m.SourceFileLoader('mod', p)
    spec = u.spec_from_loader('mod', ldr)
    mod = u.module_from_spec(spec); ldr.exec_module(mod)
    return mod
R = load('src/railway_data_v2.19.bak')
print('v2.19 version:', R.META.get('version'))
print('LINE_ORDER:', len(R.LINE_ORDER))
print('STATION_INFO:', len(R.STATION_INFO))
print('CITY_TO_STATIONS keys:', len(R.CITY_TO_STATIONS))
print('CITY_ALIAS:', len(R.CITY_ALIAS))
print('GRAPH nodes:', len(R.GRAPH))
print('PROVINCE keys:', len(set(v.get('province') for v in R.STATION_INFO.values())))
print('CTS 山南市/林芝市 =', R.CITY_TO_STATIONS.get('山南市'), R.CITY_TO_STATIONS.get('林芝市'))
print('CTS 南市/芝市米林市 =', R.CITY_TO_STATIONS.get('南市'), R.CITY_TO_STATIONS.get('芝市米林市'))

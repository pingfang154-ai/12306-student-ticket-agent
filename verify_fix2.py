# -*- coding: utf-8 -*-
import importlib.util as u
spec = u.spec_from_file_location('rd', 'src/railway_data.py')
R = u.module_from_spec(spec); spec.loader.exec_module(R)
for q in ['山南市','林芝市','拉萨市','乌鲁木齐市','库尔勒市','昆明市']:
    try:
        print(' resolve_location(%s) ->' % q, R.resolve_location(q))
    except Exception as e:
        print(' resolve_location(%s) -> ERR %s' % (q, e))
print('南市 in CTS?', '南市' in R.CITY_TO_STATIONS, '| 芝市米林市 in CTS?', '芝市米林市' in R.CITY_TO_STATIONS)
print('南市 in CAL?', '南市' in R.CITY_ALIAS, '| 芝市米林市 in CAL?', '芝市米林市' in R.CITY_ALIAS)
# 确认 5 站 lines 仍正确（拉林铁路）
for s in ['贡嘎站','扎囊站','桑日站','加查站','岗嘎站']:
    print(' ', s, 'lines=', R.STATION_INFO[s].get('lines'))

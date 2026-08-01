# -*- coding: utf-8 -*-
import importlib.util as u
spec = u.spec_from_file_location('rd', 'src/railway_data.py')
R = u.module_from_spec(spec); spec.loader.exec_module(R)
print('=== CITY_TO_STATIONS 含 南市/山南市/芝市/林芝市 的键 ===')
for k in R.CITY_TO_STATIONS:
    if any(t in k for t in ['南市','山南','芝市','林芝']):
        print(' ', repr(k), R.CITY_TO_STATIONS[k])
print('=== PROVINCE_TO_STATIONS 西藏 下列表(节选) ===')
xz = R.PROVINCE_TO_STATIONS.get('西藏', [])
print(' 西藏 station count:', len(xz))
print(' 含拉林5站?', [s for s in ['贡嘎站','扎囊站','桑日站','加查站','岗嘎站'] if s in xz])
print('=== CITY_ALIAS 含 南市/山南/芝市/林芝/米林 ===')
for k,v in R.CITY_ALIAS.items():
    if any(t in k for t in ['南市','山南','芝市','林芝','米林']):
        print(' ', repr(k), '->', repr(v))
print('=== resolve_location 测试 ===')
# resolve_location(q) 返回 (station_or_none, city_key_or_none, ...)
for q in ['山南市','林芝市','南市','芝市米林市','贡嘎站','岗嘎站']:
    try:
        res = R.resolve_location(q)
        print(' ', q, '->', res)
    except Exception as e:
        print(' ', q, 'ERR', e)

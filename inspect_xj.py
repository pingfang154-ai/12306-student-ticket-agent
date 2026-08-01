# -*- coding: utf-8 -*-
import importlib.util as u
spec = u.spec_from_file_location('rd', 'src/railway_data.py')
R = u.module_from_spec(spec); spec.loader.exec_module(R)
print('=== 新疆相关 CITY_TO_STATIONS 键 ===')
for k in sorted(R.CITY_TO_STATIONS):
    if '新疆' in k or '巴州' in k or '库尔勒' in k or '乌鲁木齐' in k:
        print(' ', k, '->', R.CITY_TO_STATIONS[k])
print('=== 库尔勒站 / 和田站 / 图木舒克站 city ===')
for s in ['库尔勒站','和田站','图木舒克站','阿拉尔站','昆玉站']:
    info = R.STATION_INFO.get(s)
    print(' ', s, info.get('city') if info else None)
print('=== 尝试解析候选 home 城市 ===')
for q in ['新疆巴州','库尔勒市','巴音郭楞','乌鲁木齐市','和田市','图木舒克市','阿拉尔市']:
    try:
        print(' ', q, '->', R.resolve_location(q))
    except Exception as e:
        print(' ', q, '-> ERR', e)

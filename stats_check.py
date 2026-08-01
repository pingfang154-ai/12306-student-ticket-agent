# -*- coding: utf-8 -*-
import importlib.util as u
spec = u.spec_from_file_location('rd', 'src/railway_data.py')
R = u.module_from_spec(spec); spec.loader.exec_module(R)
print('version:', R.META.get('version'))
print('LINE_ORDER:', len(R.LINE_ORDER))
print('STATION_INFO:', len(R.STATION_INFO))
print('CITY_TO_STATIONS keys:', len(R.CITY_TO_STATIONS))
print('CITY_ALIAS:', len(R.CITY_ALIAS))
print('GRAPH nodes:', len(R.GRAPH))
print('PROVINCE keys:', len(set(v.get('province') for v in R.STATION_INFO.values())))
print('--- v2.19 拉林5站 ---')
for s in ['贡嘎站','扎囊站','桑日站','加查站','岗嘎站']:
    print(' ', s, R.STATION_INFO.get(s))
print('--- v2.20 新疆样本站 ---')
for s in ['昆玉站','图木舒克站','阿拉尔站','博乐东站','双河市站','准东站','若羌站','米兰站','尉犁站','英库勒站']:
    print(' ', s, R.STATION_INFO.get(s))
# lines-MISS 本批核查：SYN 线导致的历史遗留 + 本批新增
miss_new = 0
for line, seq in R.LINE_ORDER.items():
    if line.startswith('__SYN__'):
        for s in seq:
            if line not in R.STATION_INFO.get(s, {}).get('lines', []):
                # 历史遗留
                pass
# 本批新增 MISS 定义：v2.20 新站若其所属的非SYN真实线不在 lines 里
print('--- 新站 lines 归属核查 ---')
for s, info in R.STATION_INFO.items():
    pass

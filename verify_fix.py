# -*- coding: utf-8 -*-
import importlib.util as u
spec = u.spec_from_file_location('rd', 'src/railway_data.py')
R = u.module_from_spec(spec); spec.loader.exec_module(R)
print('version:', R.META.get('version'))
for q in ['山南市','林芝市','南市','芝市米林市','贡嘎站','岗嘎站','拉萨市']:
    print(' resolve_location(%r) ->' % q, R.resolve_location(q))
# 检查错误键彻底消失
print('南市 in CTS?', '南市' in R.CITY_TO_STATIONS, '| 芝市米林市 in CTS?', '芝市米林市' in R.CITY_TO_STATIONS)
print('南市 in CAL?', '南市' in R.CITY_ALIAS, '| 芝市米林市 in CAL?', '芝市米林市' in R.CITY_ALIAS)

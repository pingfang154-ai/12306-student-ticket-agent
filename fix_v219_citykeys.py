# -*- coding: utf-8 -*-
# v2.19 数据更正：拉林 5 站 city 键被误截为 南市/芝市米林市（parse_city 用 s[6:] 切「西藏自治区」前缀，
# 但该前缀实为 5 字符，吞掉首字）。本脚本仅更正这 5 站 city 键并清理错误键，版本保持 v2.20，不增删任何站/线。
import importlib.util, json, os, re, shutil

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, 'src', 'railway_data.py')
BAK = os.path.join(HERE, 'src', 'railway_data_v2.20_pre_fix.bak')
if not os.path.exists(BAK):
    shutil.copyfile(SRC, BAK); print('backed up pre-fix ->', BAK)

spec = importlib.util.spec_from_file_location('rd', SRC)
R = importlib.util.module_from_spec(spec); spec.loader.exec_module(R)
LO = dict(R.LINE_ORDER); SI = dict(R.STATION_INFO)
CTS = {k: list(v) for k, v in R.CITY_TO_STATIONS.items()}
PTS = {k: list(v) for k, v in R.PROVINCE_TO_STATIONS.items()}
CAL = dict(R.CITY_ALIAS)
GR = {k: list(v) for k, v in R.GRAPH.items()}

# 正确的城市键映射
CORRECT = {
    '贡嘎站': '山南市', '扎囊站': '山南市', '桑日站': '山南市', '加查站': '山南市',
    '岗嘎站': '林芝市',
}
WRONG_CITY_KEYS = ['南市', '芝市米林市']

print('--- before ---')
for s in CORRECT:
    print(' ', s, 'city=', SI[s].get('city'))

# 1) 修正 SI city
for sta, right in CORRECT.items():
    SI[sta] = dict(SI[sta]); SI[sta]['city'] = right

# 2) 重建 CITY_TO_STATIONS：从错误键移除、加入正确键
for sta, right in CORRECT.items():
    wrong = None
    for wk in WRONG_CITY_KEYS:
        if sta in CTS.get(wk, []):
            wrong = wk; break
    if wrong:
        CTS[wrong] = [s for s in CTS[wrong] if s != sta]
        if not CTS[wrong]:
            del CTS[wrong]
    if right not in CTS:
        CTS[right] = []
    if sta not in CTS[right]:
        CTS[right].append(sta)

# 3) 清理 CITY_ALIAS 中的错误键映射（南市/芝市米林市 相关）
for bad in ['南市', '芝市米林', '芝市米林市']:
    CAL.pop(bad, None)
# 确保正确裸别名存在
for b, c in [('山南', '山南市'), ('林芝', '林芝市'), ('山南市', '山南市'), ('林芝市', '林芝市')]:
    if b not in CAL:
        CAL[b] = c

# 4) PTS 维持（5 站 province 本就是 西藏，无需变动）；顺手去重
for p, lst in PTS.items():
    PTS[p] = sorted(set(lst))

# 5) 重新生成 railway_data.py（尾部截取，版本保持 v2.20）
with open(SRC, encoding='utf-8') as f: lines_all = f.readlines()
hi = next((i for i, l in enumerate(lines_all) if l.strip().startswith('LINE_NAME_ALIAS') or 'def resolve_location' in l), None)
if hi is None: raise SystemExit('tail marker not found')
tail = ''.join(lines_all[hi:])
META_DICT = dict(R.META); META_DICT['version'] = 'v2.20'
NOTE = (R.META.get('note', '') or '').rstrip()
NOTE += '（2026-07-30 更正：v2.19 拉林5站 city 键误截为 南市/芝市米林市，已归正为 山南市/林芝市，未增删任何站/线。）'
META_DICT['note'] = NOTE
def jd(d): return json.dumps(d, ensure_ascii=False, indent=0)
header = "# 12306 学生票合规判定 Agent — 铁路数据层（自动合并生成，v2.20）\n"
body = [("META = " + jd(META_DICT)), ("LINE_ORDER = " + jd(LO)), ("STATION_INFO = " + jd(SI)),
        ("CITY_TO_STATIONS = " + jd(CTS)), ("PROVINCE_TO_STATIONS = " + jd(PTS)),
        ("CITY_ALIAS = " + jd(CAL)), ("GRAPH = " + jd(GR))]
new_py = header + "\n".join(body) + "\n\n" + tail
with open(SRC, 'w', encoding='utf-8') as f: f.write(new_py)
print('regenerated', SRC)

print('--- after ---')
for s in CORRECT:
    print(' ', s, 'city=', SI[s].get('city'))
print('CTS keys removed?', [k for k in WRONG_CITY_KEYS if k in CTS])
print('CTS 山南市 =', CTS.get('山南市'))
print('CTS 林芝市 =', CTS.get('林芝市'))
print('CAL has 南市?', '南市' in CAL, '| 芝市米林市?', '芝市米林市' in CAL)
print('GRAPH nodes:', len(GR))

# 6) 同步 7 个 JSON 镜像
def dump(fn, d):
    with open(os.path.join(HERE, 'data', fn), 'w', encoding='utf-8') as f: json.dump(d, f, ensure_ascii=False, indent=0)
for fn, d in [('line_order.json', LO), ('lines_order.json', LO), ('graph_adjacency.json', GR),
              ('station_info.json', SI), ('city_to_stations.json', CTS), ('city_aliases.json', CAL), ('province_to_stations.json', PTS)]:
    dump(fn, d)
print('done; markers GRAPH=/CITY_ALIAS=/PROVINCE_TO_STATIONS= count =',
      new_py.count('GRAPH ='), new_py.count('CITY_ALIAS ='), new_py.count('PROVINCE_TO_STATIONS ='))

# -*- coding: utf-8 -*-
# v2.20 数据更正：v2.20 合并脚本用 NEW_LINES['和若铁路']=['昆玉站'] 把 v2.19 已注册、含 11 站的
# 「和若铁路」线序整体覆盖为 ['昆玉站']（违反「只加不删」铁律）。本脚本恢复完整线序并把 昆玉站
# 按真实地理顺序插入 和田站 之后；保留既有 SYN 接网，不增减线数。版本保持 v2.20。
import importlib.util, json, os, re, shutil, importlib.machinery as m

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, 'src', 'railway_data.py')
BAK = os.path.join(HERE, 'src', 'railway_data_v2.20_pre_heruofix.bak')
if not os.path.exists(BAK):
    shutil.copyfile(SRC, BAK); print('backed up pre-heruofix ->', BAK)

def load(p):
    ldr = m.SourceFileLoader('mod', p); sp = importlib.util.spec_from_loader('mod', ldr)
    md = importlib.util.module_from_spec(sp); ldr.exec_module(md); return md

R = load(SRC)
B = load(os.path.join(HERE, 'src', 'railway_data_v2.19.bak'))
LO = dict(R.LINE_ORDER); SI = dict(R.STATION_INFO)
CTS = {k: list(v) for k, v in R.CITY_TO_STATIONS.items()}
PTS = {k: list(v) for k, v in R.PROVINCE_TO_STATIONS.items()}
CAL = dict(R.CITY_ALIAS)
GR = {k: list(v) for k, v in R.GRAPH.items()}

old = LO.get('和若铁路')
base = B.LINE_ORDER.get('和若铁路')
print('v2.20 和若铁路(被覆盖) =', old)
print('v2.19 和若铁路(完整)   =', base)

# 恢复完整线序，并把 昆玉站 插入 和田站 之后
assert '昆玉站' not in base, '昆玉站 不该出现在 v2.19 和若铁路（它是 v2.20 新增站）'
seq = list(base)
if '昆玉站' in seq:
    seq.remove('昆玉站')
i = seq.index('和田站')
seq.insert(i + 1, '昆玉站')
LO['和若铁路'] = seq
print('restored 和若铁路 =', LO['和若铁路'])

# 重新计算 LINES_OF 并刷新所有 STATION_INFO.lines（与合并脚本同口径，保证一致）
import collections
LINES_OF = collections.defaultdict(set)
for line, s in LO.items():
    for st in s: LINES_OF[st].add(line)
for sta, info in SI.items():
    SI[sta] = dict(info); SI[sta]['lines'] = sorted(LINES_OF[sta])

# 重建 GRAPH
gset = {k: set(v) for k, v in GR.items()}
for line, s in LO.items():
    for a, b in zip(s, s[1:]):
        gset.setdefault(a, set()); gset.setdefault(b, set())
        gset[a].add(b); gset[b].add(a)
GRAPH = {k: sorted(v) for k, v in gset.items()}

with open(SRC, encoding='utf-8') as f: lines_all = f.readlines()
hi = next((i for i, l in enumerate(lines_all) if l.strip().startswith('LINE_NAME_ALIAS') or 'def resolve_location' in l), None)
if hi is None: raise SystemExit('tail marker not found')
tail = ''.join(lines_all[hi:])
META_DICT = dict(R.META); META_DICT['version'] = 'v2.20'
NOTE = (R.META.get('note', '') or '').rstrip()
NOTE += "（2026-07-30 更正：v2.20 合并脚本将已注册的 11 站「和若铁路」线序误覆盖为 单站昆玉站，"
NOTE += "已恢复完整线序并把 昆玉站 插入 和田站 之后，保留既有 SYN 接网，未增减线数。）"
META_DICT['note'] = NOTE
def jd(d): return json.dumps(d, ensure_ascii=False, indent=0)
header = "# 12306 学生票合规判定 Agent — 铁路数据层（自动合并生成，v2.20）\n"
body = [("META = " + jd(META_DICT)), ("LINE_ORDER = " + jd(LO)), ("STATION_INFO = " + jd(SI)),
        ("CITY_TO_STATIONS = " + jd(CTS)), ("PROVINCE_TO_STATIONS = " + jd(PTS)),
        ("CITY_ALIAS = " + jd(CAL)), ("GRAPH = " + jd(GRAPH))]
new_py = header + "\n".join(body) + "\n\n" + tail
with open(SRC, 'w', encoding='utf-8') as f: f.write(new_py)
print('regenerated', SRC)
print('markers GRAPH=/CITY_ALIAS=/PROVINCE_TO_STATIONS= =',
      new_py.count('GRAPH ='), new_py.count('CITY_ALIAS ='), new_py.count('PROVINCE_TO_STATIONS ='))
print('LINE_ORDER count =', len(LO), '| GRAPH nodes =', len(GRAPH), '| orphan =', [s for s in SI if s not in GRAPH])

def dump(fn, d):
    with open(os.path.join(HERE, 'data', fn), 'w', encoding='utf-8') as f: json.dump(d, f, ensure_ascii=False, indent=0)
for fn, d in [('line_order.json', LO), ('lines_order.json', LO), ('graph_adjacency.json', GRAPH),
              ('station_info.json', SI), ('city_to_stations.json', CTS), ('city_aliases.json', CAL), ('province_to_stations.json', PTS)]:
    dump(fn, d)
print('JSON mirrors synced')

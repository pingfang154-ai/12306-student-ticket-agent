# -*- coding: utf-8 -*-
# 任务八：青海省、西藏自治区客运站点总表 → v2.19
# 数据源仅含 拉林铁路 中段 5 站（贡嘎/扎囊/桑日/加查/岗嘎），均为既有线精确插入。
import importlib.util, json, os, re, shutil, collections

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, 'src', 'railway_data.py')
BAK = os.path.join(HERE, 'src', 'railway_data_v2.18.bak')
XLSX = r'C:/Users/cjp15/Desktop/全国客运站点/各省市细分站点/西藏自治区、青海省/青海省、西藏自治区客运站点总表.xlsx'

if not os.path.exists(BAK):
    shutil.copyfile(SRC, BAK); print('backed up v2.18 ->', BAK)

spec = importlib.util.spec_from_file_location('rd', SRC)
R = importlib.util.module_from_spec(spec); spec.loader.exec_module(R)
LO = dict(R.LINE_ORDER); SI = dict(R.STATION_INFO)
CTS = {k: list(v) for k, v in R.CITY_TO_STATIONS.items()}
PTS = {k: list(v) for k, v in R.PROVINCE_TO_STATIONS.items()}
CAL = dict(R.CITY_ALIAS)
GR = {k: list(v) for k, v in R.GRAPH.items()}

def norm_sta(s):
    s = (s or '').strip().split('（')[0].split('(')[0].strip()
    if s in ('', '—', '-'): return ''
    if not s.endswith('站'): s += '站'
    return s

def norm_line(l):
    return str(l).strip() if l else None

# 西藏：裸地级市键（山南市/林芝市），省份「西藏」
def parse_city(raw):
    s = (raw or '').strip()
    if s.startswith('西藏自治区') or s.startswith('西藏'):
        prov = '西藏'; rest = s[6:] if s.startswith('西藏自治区') else s[2:]
    else:
        prov = None; rest = s
    m = re.search(r'[一-龥]+(?:市|地区|自治州|区)', rest)
    pref = m.group(0) if m else rest
    return prov, pref

import openpyxl
wb = openpyxl.load_workbook(XLSX, data_only=True); ws = wb['Sheet']
rows = list(ws.iter_rows(values_only=True))
hdr_idx = next((i for i, r in enumerate(rows) if r and any(isinstance(c, str) and '车站名称' in c for c in r)), 0)
data = [r for r in rows[hdr_idx+1:] if any(x is not None for x in r)]
STA, LINE, SEQ, CITY, PREV, NEXT, NOTE = 0,1,2,3,4,5,6

excel_rows = []
for r in data:
    line = norm_line(r[LINE])
    if line is None: continue
    sta = norm_sta(r[STA])
    if not sta: continue
    note = (r[NOTE] or '').strip()
    if '不办理旅客乘降' in note or '不办客' in note: continue
    excel_rows.append(dict(line=line, sta=sta, prev=norm_sta(r[PREV]), nxt=norm_sta(r[NEXT]),
                           city=(r[CITY] or '').strip(), note=note))

META = {}
for x in excel_rows:
    if x['sta'] not in META: META[x['sta']] = parse_city(x['city'])

# 重建 拉林铁路 线序（既有网已含 拉萨/协荣/山南/朗县/米林/林芝，5 新站按同线顺序+prev/next 精确插入）
REBUILD = {
    '拉林铁路': ['拉萨站','协荣站','贡嘎站','扎囊站','山南站','桑日站','加查站','朗县站','米林站','岗嘎站','林芝站'],
}
for line, seq in REBUILD.items():
    if line not in LO:
        print('WARN rebuild: line %s missing' % line); continue
    # 校验既有锚点均存在
    miss = [s for s in seq if s not in SI]
    if miss: print('WARN rebuild %s anchors not in SI:' % line, miss)
    LO[line] = list(seq)

# 无 NEW_LINES / SYN

LINES_OF = collections.defaultdict(set)
for line, seq in LO.items():
    for s in seq: LINES_OF[s].add(line)

# STATION_INFO 更新
for x in excel_rows:
    sta = x['sta']
    if sta in SI:
        cur = set(SI[sta].get('lines', [])) | LINES_OF[sta]
        SI[sta] = dict(SI[sta]); SI[sta]['lines'] = sorted(cur)
        continue
    prov, pref = META.get(sta, (None, None))
    if prov is None: prov, pref = parse_city(x['city'])
    if prov is None: print('WARN no province for', sta); continue
    SI[sta] = {'province': prov, 'city': pref, 'lines': sorted(LINES_OF[sta])}

# CITY_TO_STATIONS
for x in excel_rows:
    sta = x['sta']
    if sta not in META: continue
    prov, pref = META[sta]
    if pref not in CTS: CTS[pref] = []
    if sta not in CTS[pref]: CTS[pref].append(sta)

# PROVINCE_TO_STATIONS
for sta, info in SI.items():
    if sta not in META: continue
    prov = META[sta][0]
    if prov not in PTS: PTS[prov] = []
    if sta not in PTS[prov]: PTS[prov].append(sta)

# CITY_ALIAS
def bare(k):
    b = k.replace('宁夏', '').replace('新疆', '')
    return re.sub(r'(市|区|县|州|盟|旗|自治县|自治旗)$', '', b)

for key in list(CTS.keys()):
    b = bare(key)
    if b and b not in CAL: CAL[b] = key
    CAL[key] = key

# GRAPH 增量重建
gset = {k: set(v) for k, v in GR.items()}
for line, seq in LO.items():
    for a, b in zip(seq, seq[1:]):
        gset.setdefault(a, set()); gset.setdefault(b, set())
        gset[a].add(b); gset[b].add(a)
GRAPH = {k: sorted(v) for k, v in gset.items()}

# 重新生成 railway_data.py
with open(SRC, encoding='utf-8') as f: lines_all = f.readlines()
hi = next((i for i, l in enumerate(lines_all) if l.strip().startswith('LINE_NAME_ALIAS') or 'def resolve_location' in l), None)
if hi is None: raise SystemExit('tail marker not found')
tail = ''.join(lines_all[hi:])
META_DICT = dict(R.META); META_DICT['version'] = 'v2.19'
NOTE = ('v2.19 青海省、西藏自治区客运站点合并：数据源仅含 拉林铁路 中段 5 站'
        '（贡嘎/扎囊/桑日/加查/岗嘎），按同线顺序与 prev/next 精确重建既有 拉林铁路 线序'
        '（拉萨→协荣→贡嘎→扎囊→山南→桑日→加查→朗县→米林→岗嘎→林芝）；'
        '并入 西藏 城市键（山南市/林芝市）与省份键；仅增量，未删任何原有站/线。')
ADD_SRC = '青海省、西藏自治区客运站点总表.xlsx'
if ADD_SRC not in META_DICT.get('sources', []): META_DICT['sources'] = META_DICT.get('sources', []) + [ADD_SRC]
META_DICT_feature = None
META_DICT['note'] = NOTE
def jd(d): return json.dumps(d, ensure_ascii=False, indent=0)
header = "# 12306 学生票合规判定 Agent — 铁路数据层（自动合并生成，v2.19）\n"
body = [("META = " + jd(META_DICT)), ("LINE_ORDER = " + jd(LO)), ("STATION_INFO = " + jd(SI)),
        ("CITY_TO_STATIONS = " + jd(CTS)), ("PROVINCE_TO_STATIONS = " + jd(PTS)),
        ("CITY_ALIAS = " + jd(CAL)), ("GRAPH = " + jd(GRAPH))]
new_py = header + "\n".join(body) + "\n\n" + tail
with open(SRC, 'w', encoding='utf-8') as f: f.write(new_py)
print('regenerated', SRC, 'lines=', new_py.count(chr(10)))

def dump(fn, d):
    with open(os.path.join(HERE, 'data', fn), 'w', encoding='utf-8') as f: json.dump(d, f, ensure_ascii=False, indent=0)
    print('wrote data/%s (%d)' % (fn, len(d)))
for fn, d in [('line_order.json', LO), ('lines_order.json', LO), ('graph_adjacency.json', GRAPH),
              ('station_info.json', SI), ('city_to_stations.json', CTS), ('city_aliases.json', CAL), ('province_to_stations.json', PTS)]:
    dump(fn, d)

print('\n=== SUMMARY ===')
print('LINE_ORDER lines:', len(LO), '| STATION_INFO:', len(SI), '| CTS keys:', len(CTS), '| CAL:', len(CAL), '| GRAPH nodes:', len(GRAPH))
print('new passenger stations:', len([x for x in excel_rows if x['sta'] in META]))
missing = sum(1 for line, seq in LO.items() for s in seq if s not in SI)
print('LINE_ORDER refs missing from STATION_INFO:', missing)
for marker in ('GRAPH =', 'CITY_ALIAS =', 'PROVINCE_TO_STATIONS ='):
    print(marker, 'count=', new_py.count(marker))

# -*- coding: utf-8 -*-
# 任务九：新疆维吾尔自治区客运站点总表 → v2.20
# 20 客运站 / 9 线标签：既有线精确插入（兰新/南疆/格库重建）+ 6 新线 + SYN 接网。
import importlib.util, json, os, re, shutil, collections

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, 'src', 'railway_data.py')
BAK = os.path.join(HERE, 'src', 'railway_data_v2.19.bak')
XLSX = r'C:/Users/cjp15/Desktop/全国客运站点/各省市细分站点/新疆维吾尔自治区/新疆维吾尔自治区客运站点总表.xlsx'

if not os.path.exists(BAK):
    shutil.copyfile(SRC, BAK); print('backed up v2.19 ->', BAK)

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
    if l is None: return None
    s = str(l).strip()
    return s  # 南疆铁路（图木舒克支线）等保留原线名

# 新疆：所属省市为裸地级市/自治州/地区/兵团市（无「新疆」前缀），需归一为库内「新疆+」键
XJ_NORM = {
    '乌鲁木齐市': '新疆乌鲁木齐市', '克拉玛依市': '新疆克拉玛依市', '吐鲁番市': '新疆吐鲁番市',
    '昌吉回族自治州': '新疆昌吉州', '巴音郭楞蒙古自治州': '新疆巴州', '博尔塔拉蒙古自治州': '新疆博州',
    '塔城地区': '新疆塔城地区', '阿克苏地区': '新疆阿克苏地区',
    '胡杨河市': '新疆胡杨河市', '昆玉市': '新疆昆玉市', '图木舒克市': '新疆图木舒克市',
    '阿拉尔市': '新疆阿拉尔市', '双河市': '新疆双河市',
}
def parse_city(raw):
    s = (raw or '').strip()
    s = re.sub(r'^新疆生产建设兵团第[^师]*师', '', s)
    s = s.replace('（', '(').replace('）', ')')
    s = re.sub(r'\(.*?\)', '', s)  # 去括号注记
    if s.startswith('新疆'):
        rest = s[2:]
    else:
        rest = s
    m = re.search(r'[一-龥]+(?:市|地区|自治州|区)', rest)
    pref = m.group(0) if m else rest
    return '新疆', XJ_NORM.get(pref, '新疆' + pref)

import openpyxl
wb = openpyxl.load_workbook(XLSX, data_only=True); ws = wb['客运站点']
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

# 已在库站（双河市/魏家泉/准东）记下来，避免重复建 meta
EXISTING = {x['sta'] for x in excel_rows if x['sta'] in SI}
META = {}
for x in excel_rows:
    if x['sta'] not in META: META[x['sta']] = parse_city(x['city'])

# ---------- MERGE CONFIG ----------
SPLICE = [
    ('兰新铁路', '乌鲁木齐站', 'after', ['乌西站']),
    ('兰新铁路', '乌鲁木齐南站', 'after', ['达坂城站']),
    ('南疆铁路', '吐鲁番站', 'after', ['鱼儿沟站']),
    ('南疆铁路', '焉耆站', 'after', ['和静站']),
]
# 格库铁路按真实地理链重建（含 4 新站；铁干里克因 prev/next 与主线冲突，改由 SYN 接网）
REBUILD = {
    '格库铁路': ['库尔勒站','尉犁站','英库勒站','库尔木依站','依吞布拉克站','米兰站','若羌站',
                 '格尔木站','乌图美仁站','甘森站','花土沟站','茫崖镇站'],
}
NEW_LINES = {
    '和若铁路': ['昆玉站'],
    '南疆铁路（图木舒克支线）': ['图木舒克站'],
    '阿阿铁路': ['阿瓦提站', '阿拉尔站'],
    '博州支线铁路': ['博乐东站', '双河市站'],
    '奎北铁路': ['四棵树站', '五五站', '玛纳斯湖站'],
    '乌准铁路': ['魏家泉站', '准东站'],
}
SYNMap = {
    '__SYN__格库铁路__铁干里克站__若羌站': ['铁干里克站', '若羌站'],
    '__SYN__和若铁路__昆玉站__和田站': ['昆玉站', '和田站'],
    '__SYN__南疆铁路（图木舒克支线）__图木舒克站__巴楚站': ['图木舒克站', '巴楚站'],
    '__SYN__阿阿铁路__阿瓦提站__阿克苏站': ['阿瓦提站', '阿克苏站'],
    '__SYN__博州支线铁路__博乐东站__精河站': ['博乐东站', '精河站'],
    '__SYN__奎北铁路__四棵树站__奎屯站': ['四棵树站', '奎屯站'],
    '__SYN__乌准铁路__魏家泉站__乌鲁木齐站': ['魏家泉站', '乌鲁木齐站'],
    # 玛纳斯（昌吉/石河子走廊）邻站不在库，以 乌鲁木齐 为可达锚点接网
    '__SYN__兰新铁路__玛纳斯站__乌鲁木齐站': ['玛纳斯站', '乌鲁木齐站'],
}

def insert_seq(seq, boundary, pos, new_stations):
    if boundary not in seq: raise KeyError('boundary %s not in line' % boundary)
    i = seq.index(boundary)
    return seq[:i+1] + new_stations + seq[i+1:] if pos == 'after' else seq[:i] + new_stations + seq[i:]

for (line, boundary, pos, stations) in SPLICE:
    if line not in LO: print('WARN splice: line %s not in LINE_ORDER' % line); continue
    try: LO[line] = insert_seq(list(LO[line]), boundary, pos, stations)
    except KeyError as e: print('WARN', line, e)

for line, seq in REBUILD.items():
    if line not in LO: print('WARN rebuild: line %s missing' % line); continue
    miss = [s for s in seq if s not in SI]
    if miss: print('WARN rebuild %s anchors not in SI:' % line, miss)
    LO[line] = list(seq)

for line, seq in NEW_LINES.items():
    LO[line] = list(seq)
for key, seq in SYNMap.items():
    LO[key] = list(seq)

LINES_OF = collections.defaultdict(set)
for line, seq in LO.items():
    for s in seq: LINES_OF[s].add(line)

# STATION_INFO
for x in excel_rows:
    sta = x['sta']
    if sta in SI:  # 已有站（双河市/魏家泉/准东）仅补线归属
        cur = set(SI[sta].get('lines', [])) | LINES_OF[sta]
        SI[sta] = dict(SI[sta]); SI[sta]['lines'] = sorted(cur)
        continue
    prov, cts_key = META.get(sta, (None, None))
    if prov is None: prov, cts_key = parse_city(x['city'])
    if prov is None: print('WARN no province for', sta); continue
    SI[sta] = {'province': prov, 'city': cts_key, 'lines': sorted(LINES_OF[sta])}

# SYN/NEW 端点中已存在站补线归属
for line, seq in list(NEW_LINES.items()) + [(k, v) for k, v in SYNMap.items()]:
    for s in seq:
        if s in SI:
            cur = set(SI[s].get('lines', [])) | {line}
            SI[s] = dict(SI[s]); SI[s]['lines'] = sorted(cur)

# CTS / PTS
for x in excel_rows:
    sta = x['sta']
    if sta not in META: continue
    prov, cts_key = META[sta]
    if cts_key not in CTS: CTS[cts_key] = []
    if sta not in CTS[cts_key]: CTS[cts_key].append(sta)
    if prov not in PTS: PTS[prov] = []
    if sta not in PTS[prov]: PTS[prov].append(sta)

def bare(k):
    b = k.replace('宁夏', '').replace('新疆', '')
    return re.sub(r'(市|区|县|州|盟|旗|自治县|自治旗)$', '', b)
for key in list(CTS.keys()):
    b = bare(key)
    if b and b not in CAL: CAL[b] = key
    CAL[key] = key

gset = {k: set(v) for k, v in GR.items()}
for line, seq in LO.items():
    for a, b in zip(seq, seq[1:]):
        gset.setdefault(a, set()); gset.setdefault(b, set())
        gset[a].add(b); gset[b].add(a)
GRAPH = {k: sorted(v) for k, v in gset.items()}

with open(SRC, encoding='utf-8') as f: lines_all = f.readlines()
hi = next((i for i, l in enumerate(lines_all) if l.strip().startswith('LINE_NAME_ALIAS') or 'def resolve_location' in l), None)
if hi is None: raise SystemExit('tail marker not found')
tail = ''.join(lines_all[hi:])
META_DICT = dict(R.META); META_DICT['version'] = 'v2.20'
NOTE = ('v2.20 新疆维吾尔自治区客运站点合并：20 客运站 / 9 线标签。'
        '既有线精确插入（兰新+乌西/达坂城、南疆+鱼儿沟/和静、格库铁路按真实地理链重建含尉犁/英库勒/米兰）；'
        '新建 6 线（和若/南疆铁路图木舒克支线/阿阿/博州支线/奎北/乌准）；'
        '8 条 SYN 接网（铁干里克/昆玉/图木舒克/阿阿/博州支线/奎北/乌准/玛纳斯 各接最近可达锚点）；'
        '城市键归一「新疆+地级市/地区/兵团市」（昌吉回族自治州→新疆昌吉州 等）；仅增量，未删任何原有站/线。')
ADD_SRC = '新疆维吾尔自治区客运站点总表.xlsx'
if ADD_SRC not in META_DICT.get('sources', []): META_DICT['sources'] = META_DICT.get('sources', []) + [ADD_SRC]
META_DICT['note'] = NOTE
def jd(d): return json.dumps(d, ensure_ascii=False, indent=0)
header = "# 12306 学生票合规判定 Agent — 铁路数据层（自动合并生成，v2.20）\n"
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
print('new passenger stations:', len([x for x in excel_rows if x['sta'] in META and x['sta'] not in EXISTING]))
print('already-existing stations reused:', sorted(EXISTING))
missing = sum(1 for line, seq in LO.items() for s in seq if s not in SI)
print('LINE_ORDER refs missing from STATION_INFO:', missing)
for marker in ('GRAPH =', 'CITY_ALIAS =', 'PROVINCE_TO_STATIONS ='):
    print(marker, 'count=', new_py.count(marker))

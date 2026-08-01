# -*- coding: utf-8 -*-
import importlib.util, json, os, re, shutil, collections

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, 'src', 'railway_data.py')
BAK = os.path.join(HERE, 'src', 'railway_data_v2.17.bak')
XLSX = r'C:/Users/cjp15/Desktop/全国客运站点/各省市细分站点/甘肃省、宁夏回族自治区/甘肃省、宁夏回族自治区客运站点总表.xlsx'

# ---------- backup current (v2.17) ----------
if not os.path.exists(BAK):
    shutil.copyfile(SRC, BAK)
    print('backed up v2.17 ->', BAK)

# ---------- load current data layer ----------
spec = importlib.util.spec_from_file_location('rd', SRC)
R = importlib.util.module_from_spec(spec); spec.loader.exec_module(R)
LO = dict(R.LINE_ORDER)          # line -> [stations]
SI = dict(R.STATION_INFO)        # station -> info
CTS = {k: list(v) for k, v in R.CITY_TO_STATIONS.items()}
PTS = {k: list(v) for k, v in R.PROVINCE_TO_STATIONS.items()}
CAL = dict(R.CITY_ALIAS)
GR = {k: list(v) for k, v in R.GRAPH.items()}

# ---------- helpers ----------
def norm_sta(s):
    s = (s or '').strip()
    s = s.split('（')[0].split('(')[0].strip()
    if s in ('', '—', '-'): return ''
    if not s.endswith('站'):
        s += '站'
    return s

def norm_line(l):
    if l is None: return None
    s = str(l).strip()
    s = s.replace('包兰线', '包兰铁路').replace('干武线', '干武铁路')
    if '徐兰高速铁路' in s: return '徐兰高速铁路'
    if '敦煌铁路' in s: return '敦煌铁路'
    return s

def parse_city(raw):
    s = (raw or '').strip()
    if s.startswith('甘肃省'):
        prov = '甘肃'; rest = s[3:]
    elif s.startswith('甘肃'):
        prov = '甘肃'; rest = s[2:]
    elif s.startswith('宁夏回族自治区'):
        prov = '宁夏'; rest = s[7:]
    elif s.startswith('宁夏'):
        prov = '宁夏'; rest = s[2:]
    else:
        prov = None; rest = s
    m = re.search(r'[一-龥]+(?:市|州|地区|盟)', rest)
    pref = m.group(0) if m else rest
    after = rest[rest.index(pref)+len(pref):] if pref in rest else ''
    m2 = re.search(r'[一-龥]*(?:自治县|自治旗|[县区旗市])', after)
    county = m2.group(0) if m2 else pref
    return prov, pref, county

# ---------- read excel ----------
import openpyxl
wb = openpyxl.load_workbook(XLSX, data_only=True)
ws = wb['Sheet']
rows = list(ws.iter_rows(values_only=True))
hdr_idx = None
for i, r in enumerate(rows):
    if r and any(isinstance(c, str) and '车站名称' in c for c in r):
        hdr_idx = i; break
if hdr_idx is None:
    hdr_idx = 0
data = [r for r in rows[hdr_idx+1:] if any(x is not None for x in r)]
STA, LINE, SEQ, CITY, PREV, NEXT, NOTE = 0,1,2,3,4,5,6

excel_rows = []  # (line, sta, prev, nxt, city, note)
for r in data:
    line = norm_line(r[LINE])
    if line is None:
        continue  # stray header/non-passenger rows (辉县站/洪庆站/宁东南站)
    sta = norm_sta(r[STA])
    if not sta:
        continue
    note = (r[NOTE] or '').strip()
    if '不办理旅客乘降' in note or '不办客' in note:
        continue  # exclude non-passenger
    prev = norm_sta(r[PREV]); nxt = norm_sta(r[NEXT])
    city = (r[CITY] or '').strip()
    excel_rows.append(dict(line=line, sta=sta, prev=prev, nxt=nxt, city=city, note=note))

# station metadata from excel
META = {}   # sta -> (prov, pref, county)
for x in excel_rows:
    if x['sta'] not in META:
        META[x['sta']] = parse_city(x['city'])

# ---------- MERGE CONFIG (auditable) ----------
# SPLICE: ('line_key', 'boundary_existing_station', 'after'|'before', [ordered_new_stations])
SPLICE = [
    ('银西高速铁路','庆阳站','after',['宁县站']),
    # 银西高铁甘肃/宁夏段补全：曲子—环县—甜水堡—惠安堡—(白土岗缺)—银川
    ('银西高速铁路','曲子站','after',['环县站','甜水堡站','惠安堡站']),
    ('宝中铁路','六盘山站','after',['彭阳站']),
    ('宝中铁路','固原站','after',['沈家河站','二营站','三营站','褚家湾站']),
    ('宝中铁路','七营站','after',['王团庄站','土桥子站','李旺站','韩府湾站']),
    ('宝中铁路','宣和站','after',['大战场站']),
    ('宝中铁路','中宁南站','after',['长农站','艾家村站','石坝站']),
    ('宝中铁路','三关口站','before',['庙庄站','平凉南站','平凉站','新李站']),
    ('徐兰高速铁路','榆中站','after',['定西北站']),
    ('陇海铁路','兰州站','after',['兰州东站','桑园子站','骆驼巷站','夏官营站','许家台站','王家湾站','甘草店站','李家坪站','通安驿站']),
    ('宝成铁路','凤县站','after',['两当站']),
    ('兰新铁路','武威站','after',['武威南站','黄羊镇站','古浪站','龙沟站','打柴沟站','天祝站','永登站','龙泉寺站','河口南站','坡底下站','西固城站']),
    ('兰新铁路','张掖站','after',['玉石站','芨岭站','山丹站']),
    ('兰新铁路','张掖站','after',['平原堡站','临泽站','高台站','许三湾站']),
    ('兰新铁路','玉门站','after',['低窝铺站','疏勒河站']),
    ('兰新铁路','哈密站','after',['柳园站']),
    ('兰青铁路','民和站','after',['海石湾站']),
    ('包兰铁路','兰州站','after',['邵家堂站','水源站']),
    ('包兰铁路','白银西站','after',['朱家窑站','丰水村站','皋兰站']),
    ('包兰铁路','景泰站','before',['长城站']),
    ('包兰铁路','景泰站','after',['营盘水站','干塘站','中卫站','沙坡头站','兴泉堡站','红岘台站']),
    ('包兰铁路','中宁站','before',['青铜峡站']),
    # 大坝站：Excel prev=青铜峡 next=黄羊滩，插入两者之间（库内序为 黄羊滩→青铜峡）
    ('包兰铁路','青铜峡站','before',['大坝站']),
    ('包兰铁路','银川站','after',['惠农站']),
    ('包兰铁路','白银西站','before',['红砂岘站']),
    ('兰新高速铁路','门源站','after',['山丹马场站']),
    ('敦煌铁路','敦煌站','before',['瓜州站']),
    ('太中银铁路','太阳山站','after',['红寺堡站']),
    ('平汝铁路','大磴沟站','after',['白芨沟站','汝箕沟站']),
]

# NEW_LINES: line_key -> full ordered [stations] (incl. existing boundary stations for connectivity)
NEW_LINES = {
    '西平铁路': ['长庆桥站','泾川站'],
    '中川城际铁路': ['陈官营站','福利区站','西固站','兰州新区站','中川机场站','中川机场东站'],
    '干武铁路': ['武威南站','上腰墩站','园墩站','土门子站','黑冲滩站','石峡子站','谭家井站','庆阳山站','干塘站'],
    '红会支线': ['白银西站','白银市站','吴家川站','靖远西站','靖远站','东湾站','长征站'],
    '嘉镜铁路': ['嘉峪关站','狼尾山站'],
    '敦格铁路': ['敦煌站','阿克塞站','肃北站'],
    '酒额铁路': ['酒泉站','肃州站','金塔站','河东里站','东风南站'],
}

# SYNTHETIC connector lines (2-station) for cross-line join
SYN_LINES = [
    '__SYN__西平铁路__泾川站__平凉南站',
    '__SYN__敦煌铁路__柳沟站__瓜州站',
    # 敦煌子网接回兰新主干：柳沟站在兰新线上位于 疏勒河—桥湾 之间（桥湾不在库），以疏勒河为锚
    '__SYN__兰新铁路__疏勒河站__柳沟站',
]
SYN_MAP = {
    '__SYN__西平铁路__泾川站__平凉南站': ['泾川站','平凉南站'],
    '__SYN__敦煌铁路__柳沟站__瓜州站': ['柳沟站','瓜州站'],
    '__SYN__兰新铁路__疏勒河站__柳沟站': ['疏勒河站','柳沟站'],
}

# ---------- apply SPLICE ----------
def insert_seq(seq, boundary, pos, new_stations):
    if boundary not in seq:
        # fallback: find nearest existing station that is the boundary's proxy
        # try boundary without '站' suffix match in seq
        cand = [s for s in seq if s == boundary]
        if not cand:
            # search by prefix equality (e.g. boundary '三关口站' already there)
            raise KeyError('boundary %s not in line' % boundary)
    i = seq.index(boundary)
    if pos == 'after':
        return seq[:i+1] + new_stations + seq[i+1:]
    else:  # before
        return seq[:i] + new_stations + seq[i:]

for (line, boundary, pos, stations) in SPLICE:
    if line not in LO:
        print('WARN splice: line %s not in LINE_ORDER' % line); continue
    seq = list(LO[line])
    try:
        seq = insert_seq(seq, boundary, pos, stations)
    except KeyError as e:
        print('WARN', line, e); continue
    LO[line] = seq

# ---------- apply NEW_LINES ----------
for line, seq in NEW_LINES.items():
    LO[line] = list(seq)

# ---------- apply SYN_LINES ----------
for key, seq in SYN_MAP.items():
    LO[key] = list(seq)

# ---------- build LINES_OF for station metadata ----------
LINES_OF = collections.defaultdict(set)
for line, seq in LO.items():
    for s in seq:
        LINES_OF[s].add(line)

# stations only present in NEW_LINES/SYN configs (not in Excel rows) -> explicit prov/city
NEW_STATION_META = {
    '福利区站': ('甘肃', '兰州市'), '西固站': ('甘肃', '兰州市'),
    '兰州新区站': ('甘肃', '兰州市'), '中川机场东站': ('甘肃', '兰州市'),
    '上腰墩站': ('甘肃', '武威市'), '园墩站': ('甘肃', '武威市'), '土门子站': ('甘肃', '武威市'),
    '黑冲滩站': ('甘肃', '武威市'), '石峡子站': ('甘肃', '武威市'), '谭家井站': ('甘肃', '武威市'),
    '庆阳山站': ('甘肃', '白银市'),
    '白银市站': ('甘肃', '白银市'), '吴家川站': ('甘肃', '白银市'), '靖远西站': ('甘肃', '白银市'),
    '靖远站': ('甘肃', '白银市'), '东湾站': ('甘肃', '白银市'), '长征站': ('甘肃', '白银市'),
    '狼尾山站': ('甘肃', '嘉峪关市'),
    '阿克塞站': ('甘肃', '酒泉市'), '肃北站': ('甘肃', '酒泉市'),
    '肃州站': ('甘肃', '酒泉市'), '金塔站': ('甘肃', '酒泉市'),
    '河东里站': ('甘肃', '酒泉市'), '东风南站': ('甘肃', '酒泉市'),
    '长庆桥站': ('甘肃', '平凉市'), '泾川站': ('甘肃', '平凉市'),
    '柳沟站': ('甘肃', '酒泉市'),
}

# ---------- STATION_INFO update (excel rows) ----------
for x in excel_rows:
    sta = x['sta']
    if sta in SI:  # existing boundary station in new line
        cur = set(SI[sta].get('lines', []))
        cur |= LINES_OF[sta]
        SI[sta] = dict(SI[sta]); SI[sta]['lines'] = sorted(cur)
        continue
    prov, pref, county = META.get(sta, (None, None, None))
    if prov is None:
        # fallback: try to find from city field directly
        prov, pref, county = parse_city(x['city'])
    if prov is None:
        print('WARN no province for', sta); continue
    cts_pref = (pref if prov == '甘肃' else '宁夏' + pref)
    SI[sta] = {'province': prov, 'city': cts_pref, 'lines': sorted(LINES_OF[sta])}

# also patch existing stations referenced in NEW_LINES/SYN that may lack the new line
for line, seq in list(NEW_LINES.items()) + [(k, v) for k, v in SYN_MAP.items()]:
    for s in seq:
        if s in SI:
            cur = set(SI[s].get('lines', [])) | {line}
            SI[s] = dict(SI[s]); SI[s]['lines'] = sorted(cur)

# ---------- STATION_INFO / CTS / PTS for NEW_LINES-only stations ----------
for sta, (prov, pref) in NEW_STATION_META.items():
    cts_pref = pref  # 甘肃 uses bare prefecture
    if sta in SI:
        cur = set(SI[sta].get('lines', [])) | LINES_OF[sta]
        SI[sta] = dict(SI[sta]); SI[sta]['lines'] = sorted(cur)
        continue
    SI[sta] = {'province': prov, 'city': cts_pref, 'lines': sorted(LINES_OF[sta])}
    if cts_pref not in CTS:
        CTS[cts_pref] = []
    if sta not in CTS[cts_pref]:
        CTS[cts_pref].append(sta)
    if prov not in PTS:
        PTS[prov] = []
    if sta not in PTS[prov]:
        PTS[prov].append(sta)
    b = bare(cts_pref)
    if b and b not in CAL:
        CAL[b] = cts_pref
    CAL[cts_pref] = cts_pref

# ---------- CITY_TO_STATIONS ----------
for sta, info in SI.items():
    if sta not in META and sta not in [s for s in excel_rows]:
        # only new excel stations get CTS additions; others already have
        pass
for x in excel_rows:
    sta = x['sta']
    if sta not in META:
        continue
    prov, pref, county = META[sta]
    cts_pref = (pref if prov == '甘肃' else '宁夏' + pref)
    cts_county = (county if prov == '甘肃' else '宁夏' + county)
    for key in (cts_pref, cts_county):
        if key not in CTS:
            CTS[key] = []
        if sta not in CTS[key]:
            CTS[key].append(sta)

# ---------- PROVINCE_TO_STATIONS ----------
for sta, info in SI.items():
    if sta not in META:
        continue
    prov = META[sta][0]
    if prov not in PTS:
        PTS[prov] = []
    if sta not in PTS[prov]:
        PTS[prov].append(sta)

# ---------- CITY_ALIAS ----------
def bare(k):
    b = k.replace('宁夏', '')
    b = re.sub(r'(市|区|县|州|盟|旗|自治县|自治旗)$', '', b)
    return b

for key in list(CTS.keys()):
    b = bare(key)
    if b and b not in CAL:
        CAL[b] = key
    CAL[key] = key

# ---------- GRAPH rebuild (incremental from R.GRAPH) ----------
gset = {k: set(v) for k, v in GR.items()}
for line, seq in LO.items():
    for a, b in zip(seq, seq[1:]):
        if a not in gset: gset[a] = set()
        if b not in gset: gset[b] = set()
        gset[a].add(b); gset[b].add(a)
GRAPH = {k: sorted(v) for k, v in gset.items()}

# ---------- regenerate railway_data.py ----------
with open(SRC, encoding='utf-8') as f:
    lines_all = f.readlines()
hi = None
for i, l in enumerate(lines_all):
    if l.strip().startswith('LINE_NAME_ALIAS') or 'def resolve_location' in l:
        hi = i; break
if hi is None:
    raise SystemExit('tail marker not found')
tail = ''.join(lines_all[hi:])

META_DICT = dict(R.META)
META_DICT['version'] = 'v2.18'
NOTE = ('v2.18 甘肃省/宁夏回族自治区客运站点合并：增量并入 Gansu+Ningxia 新办客站 + '
        '既有干线（兰新/陇海/宝中/包兰/兰青/宝成/银西/徐兰高铁/兰新高铁/太中银/平汝/敦煌/兰渝等）'
        '插站/重建；新增 7 条新线（西平/中川城际/干武/红会支线/嘉镜/敦格/酒额）；2 条 SYN 接网；'
        '仅增量，未删任何原有站/线。')
ADD_SRC = '甘肃省、宁夏回族自治区客运站点总表.xlsx'
if ADD_SRC not in META_DICT.get('sources', []):
    META_DICT['sources'] = META_DICT.get('sources', []) + [ADD_SRC]
META_DICT['note'] = NOTE

def jd(d):
    return json.dumps(d, ensure_ascii=False, indent=0)

header = "# 12306 学生票合规判定 Agent — 铁路数据层（自动合并生成，v2.18）\n"
body = []
body.append("META = " + jd(META_DICT))
body.append("LINE_ORDER = " + jd(LO))
body.append("STATION_INFO = " + jd(SI))
body.append("CITY_TO_STATIONS = " + jd(CTS))
body.append("PROVINCE_TO_STATIONS = " + jd(PTS))
body.append("CITY_ALIAS = " + jd(CAL))
body.append("GRAPH = " + jd(GRAPH))
new_py = header + "\n".join(body) + "\n\n" + tail

with open(SRC, 'w', encoding='utf-8') as f:
    f.write(new_py)
print('regenerated', SRC, 'lines=', new_py.count(chr(10)))

# ---------- sync mirror JSONs ----------
def dump(fn, d):
    with open(os.path.join(HERE, 'data', fn), 'w', encoding='utf-8') as f:
        json.dump(d, f, ensure_ascii=False, indent=0)
    print('wrote data/%s (%d)' % (fn, len(d)))

dump('line_order.json', LO)
dump('lines_order.json', LO)
dump('graph_adjacency.json', GRAPH)
dump('station_info.json', SI)
dump('city_to_stations.json', CTS)
dump('city_aliases.json', CAL)
dump('province_to_stations.json', PTS)

# ---------- summary ----------
new_sta = [s for s in SI if s in META]
print('\n=== SUMMARY ===')
print('LINE_ORDER lines:', len(LO))
print('STATION_INFO stations:', len(SI))
print('CITY_TO_STATIONS keys:', len(CTS))
print('CITY_ALIAS keys:', len(CAL))
print('GRAPH nodes:', len(GRAPH))
print('new passenger stations added:', len([s for s in excel_rows if s['sta'] in SI and s['sta'] in META]))
# integrity: GRAPH vs LINE_ORDER
missing = 0
for line, seq in LO.items():
    for s in seq:
        if s not in SI: missing += 1
print('LINE_ORDER refs missing from STATION_INFO:', missing)
# dup dict markers
for marker in ('GRAPH =', 'CITY_ALIAS =', 'PROVINCE_TO_STATIONS ='):
    print(marker, 'count=', new_py.count(marker))

# -*- coding: utf-8 -*-
"""
merge_liaoning_v221.py — 辽宁省客运站点增量合并 v2.20 → v2.21

数据源：各省市细分站点/辽宁省/辽宁省客运站点总表.xlsx
  R3-R76：74 个办客站（21 个线路标签 → 归一 16 条库内线路）
  R77-R88：12 个停办/货运/乘降所站（仅货运/不办客），全部排除（不入库）

策略（仅增量，只加不删）：
  REBUILD 整链重构 2 条（既有线内部顺序地理修正 + 补全辽宁段）：
    京哈高速铁路（承沈段/京沈段/沈哈段合一，补 牛河梁/喀左/辽宁朝阳/北票/黑山北/新民北/沈阳/沈阳北/铁岭西/开原西/昌图西）
    京哈铁路（普速）（沈山段 8 站 + 沈哈段 3 站，昌黎站地理归位）
  SPLICE 精确插入 4 条：沈丹客运专线+6 / 喀赤高速铁路+2 / 新通客运专线+1 / 锦承铁路+1
  NEW_LINES 全新线 12 条：秦沈客运专线 / 沈大铁路 / 营口支线 / 沟海铁路 / 沈丹铁路 /
    凤上铁路 / 溪田铁路（田桓铁路）/ 溪博铁路（田桓铁路）/ 大郑铁路 / 辽开铁路 / 平齐铁路 / 沈吉铁路
  SYNTHETIC 合成联络线 6 条：苏家屯↔沈阳、普兰店↔大连、陈相屯↔苏家屯、五龙背↔丹东、
    义县↔锦州、八面城↔四平东
"""
import importlib.util, json, os, re, shutil, collections

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, 'src', 'railway_data.py')
BAK = os.path.join(HERE, 'src', 'railway_data_v2.20.bak')
XLSX = r'C:/Users/cjp15/Desktop/全国客运站点/各省市细分站点/辽宁省/辽宁省客运站点总表.xlsx'

# ---------- backup current (v2.20) ----------
if not os.path.exists(BAK):
    shutil.copyfile(SRC, BAK)
    print('backed up v2.20 ->', BAK)

# ---------- load current data layer ----------
spec = importlib.util.spec_from_file_location('rd', SRC)
R = importlib.util.module_from_spec(spec); spec.loader.exec_module(R)
LO = dict(R.LINE_ORDER)
SI = dict(R.STATION_INFO)
CTS = {k: list(v) for k, v in R.CITY_TO_STATIONS.items()}
PTS = {k: list(v) for k, v in R.PROVINCE_TO_STATIONS.items()}
CAL = dict(R.CITY_ALIAS)
GR = {k: list(v) for k, v in R.GRAPH.items()}
LNA = dict(R.LINE_NAME_ALIAS)

# ---------- helpers ----------
def norm_sta(s):
    s = (s or '').strip()
    s = s.split('（')[0].split('(')[0].strip()
    if s in ('', '—', '-'):
        return ''
    if not s.endswith('站'):
        s += '站'
    return s

LINE_ALIAS = {
    '京哈铁路(沈山段)': '京哈铁路（普速）', '京哈铁路（沈山段）': '京哈铁路（普速）',
    '京哈铁路(沈哈段)': '京哈铁路（普速）', '京哈铁路（沈哈段）': '京哈铁路（普速）',
    '京哈高速铁路(秦沈客运专线)': '秦沈客运专线', '京哈高速铁路（秦沈客运专线）': '秦沈客运专线',
    '京哈高速铁路(京沈段)': '京哈高速铁路', '京哈高速铁路（京沈段）': '京哈高速铁路',
    '京哈高速铁路(承沈段)': '京哈高速铁路', '京哈高速铁路（承沈段）': '京哈高速铁路',
    '京哈高速铁路(沈哈段)': '京哈高速铁路', '京哈高速铁路（沈哈段）': '京哈高速铁路',
    '喀赤高铁': '喀赤高速铁路',
    '朝凌高铁': '朝凌高速铁路',
    '溪田铁路(田桓铁路)': '溪田铁路（田桓铁路）', '溪田铁路（田桓铁路）': '溪田铁路（田桓铁路）',
    '溪博铁路(田桓铁路)': '溪博铁路（田桓铁路）', '溪博铁路（田桓铁路）': '溪博铁路（田桓铁路）',
}
def norm_lines(raw):
    """所属线路可含多个（顿号分隔），逐段清洗并归一化。"""
    out = []
    if raw is None:
        return out
    for seg in re.split(r'[、，,]', str(raw).strip()):
        seg = seg.strip()
        if not seg:
            continue
        out.append(LINE_ALIAS.get(seg, seg))
    return out

def parse_city(raw):
    """所属省市 → (prov, pref, county)。prefix 切片用 len() 防吞字（v2.19 教训）。"""
    s = (raw or '').strip()
    prefix = '辽宁省'
    if s.startswith(prefix):
        prov = '辽宁'; rest = s[len(prefix):]
    elif s.startswith('辽宁'):
        prov = '辽宁'; rest = s[len('辽宁'):]
    else:
        prov = None; rest = s
    m = re.match(r'^([\u4e00-\u9fff]+?市)', rest)   # 惰性首"市"（v2.11 修复规则）
    pref = m.group(1) if m else rest
    after = rest[len(pref):] if pref in rest else ''
    m2 = re.match(r'[\u4e00-\u9fff]*(?:自治县|自治旗|县|区|旗|市)', after)
    county = m2.group(0) if m2 else pref
    return prov, pref, county

# ---------- read excel ----------
import openpyxl
wb = openpyxl.load_workbook(XLSX, data_only=True)
ws = wb['客运站点']
rows = list(ws.iter_rows(values_only=True))
hdr_idx = None
for i, r in enumerate(rows):
    if r and any(isinstance(c, str) and '车站名称' in c for c in r):
        hdr_idx = i; break
if hdr_idx is None:
    hdr_idx = 0
data = [r for r in rows[hdr_idx+1:] if any(x is not None for x in r)]
# 列：0 车站名称 1 所属线路 2 同线顺序 3 所属省市 4 前一站 5 后一站 6 备注
excel_rows = []   # dict(line, sta, prev, nxt, city, note, seq)
excluded = []
for r in data:
    if r[0] is None:
        continue
    if r[1] is None:   # 说明行（停办/货运/乘降所），记录后排除
        excluded.append(norm_sta(r[0]))
        continue
    stas = norm_sta(r[0])
    if not stas:
        continue
    lines = norm_lines(r[1])
    note = (r[6] or '').strip()
    if '不办客' in note or '暂缓开通' in note:
        continue
    prev = norm_sta(r[4]); nxt = norm_sta(r[5])
    city = (r[3] or '').strip()
    seq = (r[2] or '').strip()
    for line in lines:
        excel_rows.append(dict(line=line, sta=stas, prev=prev, nxt=nxt, city=city, note=note, seq=seq))

META = {}   # sta -> (prov, pref, county)
for x in excel_rows:
    if x['sta'] not in META:
        META[x['sta']] = parse_city(x['city'])

print('excel 办客行（展开后）:', len(excel_rows))
print('排除站（停办/货运/乘降所）:', excluded)

# ---------- MERGE CONFIG ----------
# REBUILD: line -> 完整新序列（地理顺序，保留全部既有站）
REBUILD = {
    '京哈高速铁路': ['哈尔滨站', '哈尔滨西站', '长春西站', '四平东站', '昌图西站', '开原西站',
                  '铁岭西站', '沈阳北站', '沈阳站', '新民北站', '黑山北站', '北票站', '辽宁朝阳站',
                  '喀左站', '牛河梁站', '平泉北站', '承德县北站', '承德南站', '安匠站', '兴隆县西站',
                  '密云站', '怀柔南站', '顺义西站', '北京朝阳站', '北京站'],
    '京哈铁路（普速）': ['北京站', '蓟州站', '燕郊站', '唐山站', '玉田县站', '昌黎站', '秦皇岛站',
                    '山海关站', '绥中站', '兴城站', '葫芦岛站', '锦州站', '沟帮子站', '大虎山站',
                    '新民站', '马三家站', '沈阳站', '铁岭站', '开原站', '昌图站'],
}
# 校验 REBUILD 不丢站：既有站必须全部保留
for line, seq in REBUILD.items():
    old = set(R.LINE_ORDER.get(line, []))
    new = set(seq)
    lost = old - new
    assert not lost, f'{line} REBUILD lost stations: {lost}'

# SPLICE: (line, boundary, after|before, [new stations])
SPLICE = [
    ('沈丹客运专线', '沈阳站', 'after', ['沈阳南站', '本溪新城站']),
    ('沈丹客运专线', '本溪站', 'after', ['南芬北站', '通远堡西站', '凤城东站', '五龙背东站']),
    ('喀赤高速铁路', '宁城站', 'after', ['建平站', '喀左站']),
    ('新通客运专线', '甘旗卡站', 'after', ['新民北站']),
    ('锦承铁路', '平泉站', 'after', ['义县站']),
]

# NEW_LINES: line -> full ordered stations（含既有边界站以保连通）
NEW_LINES = {
    '秦沈客运专线': ['山海关站', '东戴河站', '绥中北站', '葫芦岛北站', '锦州南站', '凌海南站',
                 '盘锦北站', '台安站', '辽中站', '沈阳北站'],
    '沈大铁路': ['普兰店站', '熊岳城站', '盖州站', '大石桥站', '海城站', '鞍山站', '灯塔站',
             '林盛堡站', '苏家屯站'],
    '营口支线': ['大石桥站', '营口站'],
    '沟海铁路': ['沟帮子站', '盘锦站', '西柳站', '海城站'],
    '沈丹铁路': ['陈相屯站', '石桥子站', '南芬站', '下马塘站', '连山关站', '祁家堡站', '草河口站',
             '通远堡站', '刘家河站', '凤凰城站', '一面山站', '汤山城站', '五龙背站'],
    '凤上铁路': ['凤凰城站', '灌水站', '宽甸站'],
    '溪田铁路（田桓铁路）': ['本溪站', '小市站', '铁刹山站', '大阳站', '八里甸子站', '五女山站'],
    '溪博铁路（田桓铁路）': ['八里甸子站', '花博山站'],
    '大郑铁路': ['大虎山站', '新立屯站', '甘旗卡站', '通辽站'],
    '辽开铁路': ['开原站', '西丰站'],
    '平齐铁路': ['八面城站', '三江口站', '通辽站'],
    '沈吉铁路': ['沈阳站', '抚顺站', '南杂木站', '南口前站', '清原站'],
}

# SYNTHETIC connector lines
SYN_MAP = {
    '__SYN__沈大铁路__苏家屯站__沈阳站': ['苏家屯站', '沈阳站'],
    '__SYN__沈大铁路__普兰店站__大连站': ['普兰店站', '大连站'],
    '__SYN__沈丹铁路__陈相屯站__苏家屯站': ['陈相屯站', '苏家屯站'],
    '__SYN__沈丹铁路__五龙背站__丹东站': ['五龙背站', '丹东站'],
    '__SYN__锦承铁路__义县站__锦州站': ['义县站', '锦州站'],
    '__SYN__平齐铁路__八面城站__四平东站': ['八面城站', '四平东站'],
}

# LINE_NAME_ALIAS 增量（供未来线路名归一使用）
LNA_ADD = {
    '京哈铁路(沈山段)': ['京哈铁路（普速）'], '京哈铁路（沈山段）': ['京哈铁路（普速）'],
    '京哈铁路(沈哈段)': ['京哈铁路（普速）'], '京哈铁路（沈哈段）': ['京哈铁路（普速）'],
    '京哈高速铁路(秦沈客运专线)': ['秦沈客运专线'], '京哈高速铁路（秦沈客运专线）': ['秦沈客运专线'],
    '京哈高速铁路(京沈段)': ['京哈高速铁路'], '京哈高速铁路（京沈段）': ['京哈高速铁路'],
    '京哈高速铁路(承沈段)': ['京哈高速铁路'], '京哈高速铁路（承沈段）': ['京哈高速铁路'],
    '京哈高速铁路(沈哈段)': ['京哈高速铁路'], '京哈高速铁路（沈哈段）': ['京哈高速铁路'],
    '京哈高铁': ['京哈高速铁路'],
    '喀赤高铁': ['喀赤高速铁路'], '朝凌高铁': ['朝凌高速铁路'],
    '溪田铁路': ['溪田铁路（田桓铁路）'], '田桓铁路': ['溪田铁路（田桓铁路）'],
    '溪博铁路': ['溪博铁路（田桓铁路）'],
}

# ---------- apply REBUILD ----------
for line, seq in REBUILD.items():
    LO[line] = list(seq)

# ---------- apply SPLICE ----------
def insert_seq(seq, boundary, pos, new_stations):
    i = seq.index(boundary)
    if pos == 'after':
        return seq[:i+1] + new_stations + seq[i+1:]
    return seq[:i] + new_stations + seq[i:]

for (line, boundary, pos, stations) in SPLICE:
    if line not in LO:
        print('WARN splice: line %s not in LINE_ORDER' % line); continue
    seq = list(LO[line])
    try:
        seq = insert_seq(seq, boundary, pos, stations)
    except ValueError as e:
        print('WARN', line, e); continue
    LO[line] = seq

# ---------- apply NEW_LINES ----------
for line, seq in NEW_LINES.items():
    assert line not in LO, f'NEW_LINES {line} already exists!'
    LO[line] = list(seq)

# ---------- apply SYN_LINES ----------
for key, seq in SYN_MAP.items():
    assert key not in LO, f'SYN {key} already exists!'
    LO[key] = list(seq)

# ---------- build LINES_OF ----------
LINES_OF = collections.defaultdict(set)
for line, seq in LO.items():
    for s in seq:
        LINES_OF[s].add(line)

# ---------- STATION_INFO update ----------
new_sta_count = 0
for x in excel_rows:
    sta = x['sta']
    if sta in SI:
        cur = set(SI[sta].get('lines', [])) | LINES_OF[sta]
        SI[sta] = dict(SI[sta]); SI[sta]['lines'] = sorted(cur)
        continue
    prov, pref, county = META.get(sta, (None, None, None))
    if prov is None:
        prov, pref, county = parse_city(x['city'])
    if prov is None:
        print('WARN no province for', sta); continue
    SI[sta] = {'province': prov, 'city': pref, 'lines': sorted(LINES_OF[sta])}
    new_sta_count += 1

# 既有站回写新线归属（NEW_LINES/SYN/REBUILD/SPLICE 边界站）
_splice_pairs = [(sp[0], sp[3]) for sp in SPLICE]
for line, seq in (list(NEW_LINES.items()) + list(SYN_MAP.items())
                  + list(REBUILD.items()) + _splice_pairs):
    for s in seq:
        if s in SI:
            cur = set(SI[s].get('lines', [])) | {line}
            SI[s] = dict(SI[s]); SI[s]['lines'] = sorted(cur)

# ---------- CITY_TO_STATIONS / PROVINCE_TO_STATIONS ----------
for x in excel_rows:
    sta = x['sta']
    if sta not in META or sta not in SI:
        continue
    prov, pref, county = META[sta]
    for key in (pref, county):
        if key not in CTS:
            CTS[key] = []
        if sta not in CTS[key]:
            CTS[key].append(sta)
    if prov not in PTS:
        PTS[prov] = []
    if sta not in PTS[prov]:
        PTS[prov].append(sta)

# ---------- CITY_ALIAS ----------
def bare(k):
    b = k.replace('辽宁', '')
    b = re.sub(r'(市|区|县|州|盟|旗|自治县|自治旗)$', '', b)
    return b

for key in list(CTS.keys()):
    b = bare(key)
    if b and b not in CAL:
        CAL[b] = key
    CAL[key] = key

# ---------- LINE_NAME_ALIAS ----------
for k, v in LNA_ADD.items():
    if k not in LNA:
        LNA[k] = v

# ---------- GRAPH rebuild (remove old edges of modified lines, then add merged) ----------
gset = {k: set(v) for k, v in GR.items()}
modified = set(REBUILD.keys()) | {sp[0] for sp in SPLICE}
for line in modified:
    for a, b in zip(R.LINE_ORDER.get(line, []), R.LINE_ORDER.get(line, [])[1:]):
        if a in gset: gset[a].discard(b)
        if b in gset: gset[b].discard(a)
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
META_DICT['version'] = 'v2.21'
NOTE = ('v2.21 辽宁省客运站点合并：74 办客站增量并入（12 停办/货运/乘降所站排除）；'
        'REBUILD 整链重构 京哈高速铁路（承沈/京沈/沈哈段合一补全）与 京哈铁路（普速）'
        '（沈山段 8 站 + 沈哈段 3 站 + 昌黎站地理归位）；12 条新线（秦沈客运专线/沈大铁路/营口支线/'
        '沟海铁路/沈丹铁路/凤上铁路/溪田铁路（田桓铁路）/溪博铁路（田桓铁路）/大郑铁路/辽开铁路/'
        '平齐铁路/沈吉铁路）；SPLICE 沈丹客运专线+6/喀赤高速铁路+2/新通客运专线+1/锦承铁路+1；'
        '6 条 SYN 合成联络线接网；仅增量，未删任何既有站/线（重构线保留全部既有站）。')
ADD_SRC = '辽宁省客运站点总表.xlsx'
if ADD_SRC not in META_DICT.get('sources', []):
    META_DICT['sources'] = META_DICT.get('sources', []) + [ADD_SRC]
META_DICT['note'] = NOTE

def jd(d):
    return json.dumps(d, ensure_ascii=False, indent=0)

header = "# 12306 学生票合规判定 Agent — 铁路数据层（自动合并生成，v2.21）\n"
body = []
body.append("META = " + jd(META_DICT))
body.append("LINE_ORDER = " + jd(LO))
body.append("STATION_INFO = " + jd(SI))
body.append("CITY_TO_STATIONS = " + jd(CTS))
body.append("PROVINCE_TO_STATIONS = " + jd(PTS))
body.append("CITY_ALIAS = " + jd(CAL))
body.append("LINE_NAME_ALIAS = " + jd(LNA))
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
print('\n=== SUMMARY ===')
print('LINE_ORDER lines:', len(LO))
print('STATION_INFO stations:', len(SI))
print('CITY_TO_STATIONS keys:', len(CTS))
print('CITY_ALIAS keys:', len(CAL))
print('LINE_NAME_ALIAS keys:', len(LNA))
print('GRAPH nodes:', len(GRAPH))
print('new passenger stations added:', new_sta_count)
print('辽宁 PTS 站数:', len(PTS.get('辽宁', [])))
# integrity: LINE_ORDER refs must exist in SI
missing = 0
for line, seq in LO.items():
    for s in seq:
        if s not in SI:
            missing += 1
            print('  MISSING SI:', line, s)
print('LINE_ORDER refs missing from STATION_INFO:', missing)
# orphan check: 本批 Excel 办客站必须都在 LINE_ORDER
excel_stas = {x['sta'] for x in excel_rows}
not_in_lo = [s for s in excel_stas if s not in LINES_OF]
print('Excel 办客站不在任何线路:', not_in_lo)
# dup dict markers
for marker in ('GRAPH =', 'CITY_ALIAS =', 'PROVINCE_TO_STATIONS =', 'CITY_TO_STATIONS =', 'STATION_INFO =', 'LINE_ORDER =', 'LINE_NAME_ALIAS ='):
    print(marker, 'count=', new_py.count(marker))

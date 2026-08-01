# -*- coding: utf-8 -*-
"""
merge_neimenggu_v223.py — 内蒙古自治区客运站点增量合并 v2.22 → v2.23

数据源：各省市细分站点/内蒙古自治区/内蒙古自治区客运站点总表.xlsx
  R3-R117：115 个办客站（去重；17 库内既有，净增 98）；0 排除站

策略（仅增量，只加不删）：
  REBUILD 整链重构 3 条：滨洲铁路（19→25 站，补 嵯岗/乌奴耳/博克图/巴林/南木/哈拉苏，
    修正 成吉思汗—扎兰屯 顺序）、包兰铁路（23→32 站，补内蒙古段 9 站，修正宁夏段顺序）、
    通霍铁路（4→7 站，补 扎鲁特/吐列毛杜/珠斯花，修正 白音胡硕—西哲里木 顺序；霍林郭勒→霍林河归一）
  SPLICE 精确插入 13 条：京包+7/集通+7/干武+1/平汝+1/平齐+1/大郑+1/通让+2/白阿+8/长白+1/
    京通+14/嫩林+2/锡乌+2/包西+4
  NEW_LINES 全新线 15 条：集二/锡多/呼准鄂/包白/叶赤/赤大白/甘库/牙林/伊加/朝乌/伊敏/博林/
    临哈/新上/锡二
  SYNTHETIC 1 条：阿尔山北↔阿尔山（伊阿线单站接白阿线）
"""
import importlib.util, json, os, re, shutil, collections

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, 'src', 'railway_data.py')
BAK = os.path.join(HERE, 'src', 'railway_data_v2.22.bak')
XLSX = r'C:/Users/cjp15/Desktop/全国客运站点/各省市细分站点/内蒙古自治区/内蒙古自治区客运站点总表.xlsx'

if not os.path.exists(BAK):
    shutil.copyfile(SRC, BAK)
    print('backed up v2.22 ->', BAK)

spec = importlib.util.spec_from_file_location('rd', SRC)
R = importlib.util.module_from_spec(spec); spec.loader.exec_module(R)
LO = dict(R.LINE_ORDER)
SI = dict(R.STATION_INFO)
CTS = {k: list(v) for k, v in R.CITY_TO_STATIONS.items()}
PTS = {k: list(v) for k, v in R.PROVINCE_TO_STATIONS.items()}
CAL = dict(R.CITY_ALIAS)
GR = {k: list(v) for k, v in R.GRAPH.items()}
LNA = dict(R.LINE_NAME_ALIAS)

def norm_sta(s):
    s = (s or '').strip()
    s = s.split('（')[0].split('(')[0].strip()
    if s in ('', '—', '-'):
        return ''
    if not s.endswith('站'):
        s += '站'
    if s == '霍林郭勒站':
        return '霍林河站'   # 归一：库内通霍线终点为霍林河站
    return s

LINE_ALIAS = {
    '京包铁路(兼集二/集通/张集)': '京包铁路', '京包铁路（兼集二/集通/张集）': '京包铁路',
    '京包铁路(旧线)': '京包铁路', '京包铁路（旧线）': '京包铁路',
    '京包铁路(兼京包客专)': '京包铁路', '京包铁路（兼京包客专）': '京包铁路',
    '京包铁路(兼包兰/包白)': '京包铁路', '京包铁路（兼包兰/包白）': '京包铁路',
    '京包客运专线(张呼段)': '京包客运专线', '京包客运专线（张呼段）': '京包客运专线',
    '集通铁路(交会赤大白铁路)': '集通铁路', '集通铁路（交会赤大白铁路）': '集通铁路',
    '呼准鄂铁路(终点)': '呼准鄂铁路', '呼准鄂铁路（终点）': '呼准鄂铁路',
    '包白铁路(终点)': '包白铁路', '包白铁路（终点）': '包白铁路',
    '乌吉线(起点)': '乌吉线', '乌吉线（起点）': '乌吉线',
    '新上铁路(新陶铁路)': '新上铁路', '新上铁路（新陶铁路）': '新上铁路',
    '临哈铁路(临策段+额哈段交汇)': '临哈铁路', '临哈铁路（临策段+额哈段交汇）': '临哈铁路',
    '锡乌铁路(起点)': '锡乌铁路', '锡乌铁路（起点）': '锡乌铁路',
    '锡乌铁路(终点)': '锡乌铁路', '锡乌铁路（终点）': '锡乌铁路',
    '白阿铁路(终点)': '白阿铁路', '白阿铁路（终点）': '白阿铁路',
    '伊阿铁路(两伊铁路)(终点)': '伊阿铁路', '伊阿铁路（两伊铁路）（终点）': '伊阿铁路',
    '滨洲铁路(博林线起点)': '滨洲铁路', '滨洲铁路（博林线起点）': '滨洲铁路',
    '滨洲铁路(牙林线接轨)': '滨洲铁路', '滨洲铁路（牙林线接轨）': '滨洲铁路',
    '滨洲铁路(伊敏线起点)': '滨洲铁路', '滨洲铁路（伊敏线起点）': '滨洲铁路',
    '滨洲铁路(终点)': '滨洲铁路', '滨洲铁路（终点）': '滨洲铁路',
    '牙林铁路(起点)': '牙林铁路', '牙林铁路（起点）': '牙林铁路',
    '牙林铁路(终点)': '牙林铁路', '牙林铁路（终点）': '牙林铁路',
    '伊加铁路(起点)': '伊加铁路', '伊加铁路（起点）': '伊加铁路',
    '伊加铁路(牙林东线)': '伊加铁路', '伊加铁路（牙林东线）': '伊加铁路',
    '朝乌铁路(牙林西线)': '朝乌铁路', '朝乌铁路（牙林西线）': '朝乌铁路',
    '朝乌铁路(终点)': '朝乌铁路', '朝乌铁路（终点）': '朝乌铁路',
    '伊敏铁路(终点': '伊敏铁路', '接伊阿线)': '伊敏铁路',
    '嫩林铁路(富西线)': '嫩林铁路', '嫩林铁路（富西线）': '嫩林铁路',
    '博林铁路(终点)': '博林铁路', '博林铁路（终点）': '博林铁路',
    '叶赤铁路(终点)': '叶赤铁路', '叶赤铁路（终点）': '叶赤铁路',
    '通霍铁路(终点)': '通霍铁路', '通霍铁路（终点）': '通霍铁路',
    '甘库铁路(终点)': '甘库铁路', '甘库铁路（终点）': '甘库铁路',
    '长白乌铁路': '长白铁路',
    '赤大白铁路(锦华铁路赤大段)': '赤大白铁路', '赤大白铁路（锦华铁路赤大段）': '赤大白铁路',
    '锡多铁路(锡桑线)': '锡多铁路', '锡多铁路（锡桑线）': '锡多铁路',
}
def norm_lines(raw):
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
    s = (raw or '').strip()
    prefix = '内蒙古自治区'
    if s.startswith(prefix):
        prov = '内蒙古'; rest = s[len(prefix):]
    elif s.startswith('内蒙古'):
        prov = '内蒙古'; rest = s[len('内蒙古'):]
    else:
        prov = None; rest = s
    m = re.match(r'^([\u4e00-\u9fff]+?(?:市|盟|旗))', rest)
    pref = m.group(1) if m else rest
    after = rest[len(pref):] if pref in rest else ''
    m2 = re.match(r'[\u4e00-\u9fff]*(?:自治旗|自治县|旗|区|县|市)', after)
    county = m2.group(0) if m2 else pref
    return prov, '内蒙古' + pref, ('内蒙古' + county)

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
excel_rows = []
excluded = []
for r in data:
    if r[0] is None:
        continue
    if r[1] is None:
        excluded.append(norm_sta(r[0]))
        continue
    stas = norm_sta(r[0])
    if not stas:
        continue
    lines = norm_lines(r[1])
    if not lines:
        continue
    prev = norm_sta(r[4]); nxt = norm_sta(r[5])
    city = (r[3] or '').strip()
    seq = (r[2] or '').strip()
    for line in lines:
        excel_rows.append(dict(line=line, sta=stas, prev=prev, nxt=nxt, city=city, seq=seq))

META = {}
for x in excel_rows:
    if x['sta'] not in META:
        META[x['sta']] = parse_city(x['city'])

print('excel 办客行（展开后）:', len(excel_rows))
print('排除站:', excluded)

# ---------- MERGE CONFIG ----------
REBUILD = {
    # 滨洲铁路补全内蒙古东段 6 站 + 顺序修正（满洲里→哈尔滨）
    '滨洲铁路': ['满洲里站', '扎赉诺尔西站', '嵯岗站', '海拉尔站', '大雁站', '牙克石站', '乌奴耳站',
              '博克图站', '巴林站', '南木站', '哈拉苏站', '扎兰屯站', '成吉思汗站', '碾子山站',
              '龙江站', '富拉尔基站', '昂昂溪站', '杜尔伯特站', '大庆东站', '安达站', '宋站',
              '尚家站', '肇东站', '对青山站', '哈尔滨站'],
    # 包兰铁路补内蒙古段 9 站 + 宁夏段顺序修正（兰州→包头）
    '包兰铁路': ['兰州站', '邵家堂站', '水源站', '红砂岘站', '白银西站', '朱家窑站', '丰水村站',
              '皋兰站', '长城站', '景泰站', '营盘水站', '干塘站', '中卫站', '沙坡头站', '兴泉堡站',
              '红岘台站', '中宁站', '青铜峡站', '大坝站', '黄羊滩站', '银川站', '暖泉站', '惠农站',
              '乌海西站', '乌海站', '碱柜站', '磴口站', '巴彦高勒站', '刘召站', '西小召站',
              '乌拉山西站', '包头站'],
    # 通霍铁路补全 3 站 + 顺序修正（霍林郭勒归一霍林河）
    '通霍铁路': ['通辽站', '扎鲁特站', '白音胡硕站', '吐列毛杜站', '西哲里木站', '珠斯花站', '霍林河站'],
}
for line, seq in REBUILD.items():
    old = set(R.LINE_ORDER.get(line, []))
    new = set(seq)
    lost = old - new
    assert not lost, f'{line} REBUILD lost stations: {lost}'
    print(f'{line} REBUILD: {len(old)}->{len(seq)} 站，既有站全保留')

SPLICE = [
    ('京包铁路', '新安庄站', 'after',
     ['土贵乌拉站', '集宁南站', '卓资山站', '旗下营站', '呼和浩特站', '察素齐站']),
    ('京包铁路', '萨拉齐站', 'after', ['包头东站']),
    ('集通铁路', '正镶白旗站', 'before', ['商都站', '化德站']),
    ('集通铁路', '正镶白旗站', 'after', ['桑根达来站', '大板站']),
    ('集通铁路', '林西站', 'after', ['林东站', '查布嘎站', '开鲁站', '通辽站']),
    ('干武铁路', '干塘站', 'before', ['岳家井站']),
    ('平汝铁路', '大磴沟站', 'after', ['呼鲁斯太站']),
    ('平齐铁路', '茂林站', 'after', ['保康站']),
    ('大郑铁路', '甘旗卡站', 'after', ['大林站']),
    ('通让铁路', '太平川站', 'before', ['通辽站', '宝龙山站']),
    ('白阿铁路', '镇西站', 'after', ['葛根庙站', '乌兰浩特站']),
    ('白阿铁路', '大石寨站', 'after', ['德伯斯站', '索伦站']),
    ('白阿铁路', '明水河站', 'after', ['五叉沟站', '白狼站', '阿尔山站']),
    ('长白铁路', '白城站', 'after', ['乌兰浩特站']),
    ('京通铁路', '纪家沟站', 'after',
     ['赤峰站', '赤峰南站', '四道湾站', '敖汉站', '新窝铺站', '舍力虎站', '奈曼站',
      '白音他拉站', '黄花筒站', '八仙筒站', '东明村站', '治安站', '东来站', '通辽站']),
    ('嫩林铁路', '加格达奇站', 'before', ['红彦站', '大杨树站']),
    ('锡乌铁路', '锡林浩特站', 'after', ['西乌旗站', '白音华南站']),
    ('包西铁路', '神木站', 'before', ['包头站', '达拉特西站', '东胜西站', '鄂尔多斯站']),
]

NEW_LINES = {
    '集二铁路': ['集宁南站', '白音察干站', '土牧尔台站', '朱日和站', '赛汗塔拉站'],
    '锡多铁路': ['锡林浩特站', '桑根达来站'],
    '呼准鄂铁路': ['呼和浩特东站', '托克托东站', '准格尔站', '东胜东站', '鄂尔多斯站'],
    '包白铁路': ['包头站', '昆都仑召站', '白云鄂博站'],
    '叶赤铁路': ['赤峰南站', '平庄北站', '平庄南站', '乃林站', '天义站'],
    '赤大白铁路': ['赤峰南站', '乌丹站', '大板站'],
    '甘库铁路': ['甘旗卡站', '库伦站'],
    '牙林铁路': ['牙克石站', '乌尔旗汗站', '库都尔站', '图里河站', '伊图里河站', '根河站',
              '金河站', '阿龙山站', '满归站'],
    '伊加铁路': ['伊图里河站', '喀喇其站', '克一河站', '甘河站', '吉文站', '阿里河站', '加格达奇站'],
    '朝乌铁路': ['伊图里河站', '得耳布尔站', '莫尔道嘎站'],
    '伊敏铁路': ['海拉尔站', '伊敏站'],
    '博林铁路': ['博克图站', '新绰源站', '塔尔气站'],
    '临哈铁路': ['巴彦淖尔站', '额济纳站'],
    '新上铁路': ['鄂尔多斯站', '乌审旗站'],
    '锡二铁路': ['锡林浩特站', '阿巴嘎旗站', '苏尼特左旗站'],
}

SYN_MAP = {
    '__SYN__伊阿铁路__阿尔山北站__阿尔山站': ['阿尔山北站', '阿尔山站'],
}

LNA_ADD = {
    '京包铁路(兼集二/集通/张集)': ['京包铁路'], '京包铁路(旧线)': ['京包铁路'],
    '京包铁路(兼京包客专)': ['京包铁路'], '京包铁路(兼包兰/包白)': ['京包铁路'],
    '京包客运专线(张呼段)': ['京包客运专线'],
    '集通铁路(交会赤大白铁路)': ['集通铁路'],
    '呼准鄂铁路(终点)': ['呼准鄂铁路'],
    '包白铁路(终点)': ['包白铁路'],
    '新上铁路(新陶铁路)': ['新上铁路'],
    '临哈铁路(临策段+额哈段交汇)': ['临哈铁路'],
    '锡乌铁路(起点)': ['锡乌铁路'], '锡乌铁路(终点)': ['锡乌铁路'],
    '白阿铁路(终点)': ['白阿铁路'],
    '伊阿铁路(两伊铁路)(终点)': ['伊阿铁路'],
    '滨洲铁路(博林线起点)': ['滨洲铁路'], '滨洲铁路(牙林线接轨)': ['滨洲铁路'],
    '滨洲铁路(伊敏线起点)': ['滨洲铁路'], '滨洲铁路(终点)': ['滨洲铁路'],
    '牙林铁路(起点)': ['牙林铁路'], '牙林铁路(终点)': ['牙林铁路'],
    '伊加铁路(起点)': ['伊加铁路'], '伊加铁路(牙林东线)': ['伊加铁路'],
    '朝乌铁路(牙林西线)': ['朝乌铁路'], '朝乌铁路(终点)': ['朝乌铁路'],
    '嫩林铁路(富西线)': ['嫩林铁路'],
    '博林铁路(终点)': ['博林铁路'],
    '叶赤铁路(终点)': ['叶赤铁路'],
    '通霍铁路(终点)': ['通霍铁路'],
    '甘库铁路(终点)': ['甘库铁路'],
    '长白乌铁路': ['长白铁路'],
    '赤大白铁路(锦华铁路赤大段)': ['赤大白铁路'],
    '锡多铁路(锡桑线)': ['锡多铁路'],
    '乌吉线': ['乌吉线'],
    '伊阿铁路': ['伊阿铁路'],
}

# ---------- apply REBUILD / SPLICE / NEW / SYN ----------
for line, seq in REBUILD.items():
    LO[line] = list(seq)

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

for line, seq in NEW_LINES.items():
    assert line not in LO, f'NEW_LINES {line} already exists!'
    LO[line] = list(seq)

for key, seq in SYN_MAP.items():
    assert key not in LO, f'SYN {key} already exists!'
    LO[key] = list(seq)

LINES_OF = collections.defaultdict(set)
for line, seq in LO.items():
    for s in seq:
        LINES_OF[s].add(line)

# ---------- STATION_INFO ----------
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

_splice_pairs = [(sp[0], sp[3]) for sp in SPLICE]
for line, seq in (list(NEW_LINES.items()) + list(SYN_MAP.items())
                  + list(REBUILD.items()) + _splice_pairs):
    for s in seq:
        if s in SI:
            cur = set(SI[s].get('lines', [])) | {line}
            SI[s] = dict(SI[s]); SI[s]['lines'] = sorted(cur)

# ---------- CTS / PTS ----------
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
    b = k.replace('内蒙古', '')
    b = re.sub(r'(市|区|县|州|盟|旗|自治县|自治旗)$', '', b)
    return b

for key in list(CTS.keys()):
    b = bare(key)
    if b and b not in CAL:
        CAL[b] = key
    CAL[key] = key
    k2 = key.replace('内蒙古', '', 1)
    if k2 != key and k2 not in CAL:
        CAL[k2] = key   # 去前缀全名键（额济纳旗/苏尼特右旗 等）

# ---------- LINE_NAME_ALIAS ----------
for k, v in LNA_ADD.items():
    if k not in LNA:
        LNA[k] = v

# ---------- GRAPH rebuild ----------
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

# ---------- regenerate ----------
with open(SRC, encoding='utf-8') as f:
    lines_all = f.readlines()
hi = None
for i, l in enumerate(lines_all):
    if '_ALL_STATIONS' in l or 'def _norm' in l or 'def resolve_location' in l:
        hi = i; break
if hi is None:
    raise SystemExit('tail marker not found')
tail = ''.join(lines_all[hi:])
tail = tail.replace('LINE_NAME_ALIAS = {}\n', '', 1)

META_DICT = dict(R.META)
META_DICT['version'] = 'v2.23'
NOTE = ('v2.23 内蒙古自治区客运站点合并：115 办客站（净增 98；17 库内既有）；0 排除站；'
        'REBUILD 3（滨洲铁路 19→25 站补东段 6 站、包兰铁路 23→32 站补内蒙古段 9 站、通霍铁路补全 7 站'
        '含霍林郭勒→霍林河归一）；SPLICE 13 条（京包+7/集通+7/干武+1/平汝+1/平齐+1/大郑+1/通让+2/白阿+8/'
        '长白+1/京通+14/嫩林+2/锡乌+2/包西+4）；NEW_LINES 15 条（集二/锡多/呼准鄂/包白/叶赤/赤大白/甘库/'
        '牙林/伊加/朝乌/伊敏/博林/临哈/新上/锡二）；SYN 1 条（阿尔山北↔阿尔山）；城市键沿用「内蒙古+」'
        '格式；仅增量，未删任何既有站/线。')
ADD_SRC = '内蒙古自治区客运站点总表.xlsx'
if ADD_SRC not in META_DICT.get('sources', []):
    META_DICT['sources'] = META_DICT.get('sources', []) + [ADD_SRC]
META_DICT['note'] = NOTE

def jd(d):
    return json.dumps(d, ensure_ascii=False, indent=0)

header = "# 12306 学生票合规判定 Agent — 铁路数据层（自动合并生成，v2.23）\n"
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

print('\n=== SUMMARY ===')
print('LINE_ORDER lines:', len(LO))
print('STATION_INFO stations:', len(SI))
print('CITY_TO_STATIONS keys:', len(CTS))
print('CITY_ALIAS keys:', len(CAL))
print('LINE_NAME_ALIAS keys:', len(LNA))
print('GRAPH nodes:', len(GRAPH))
print('new passenger stations added:', new_sta_count)
print('内蒙古 PTS:', len(PTS.get('内蒙古', [])))
missing = 0
for line, seq in LO.items():
    for s in seq:
        if s not in SI:
            missing += 1
            print('  MISSING SI:', line, s)
print('LINE_ORDER refs missing from STATION_INFO:', missing)
excel_stas = {x['sta'] for x in excel_rows}
not_in_lo = [s for s in excel_stas if s not in LINES_OF]
print('Excel 办客站不在任何线路:', not_in_lo)
for marker in ('GRAPH =', 'CITY_ALIAS =', 'PROVINCE_TO_STATIONS =', 'CITY_TO_STATIONS =',
               'STATION_INFO =', 'LINE_ORDER =', 'LINE_NAME_ALIAS ='):
    print(marker, 'count=', new_py.count(marker))

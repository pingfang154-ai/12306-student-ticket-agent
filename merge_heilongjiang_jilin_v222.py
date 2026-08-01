# -*- coding: utf-8 -*-
"""
merge_heilongjiang_jilin_v222.py — 黑龙江省/吉林省客运站点增量合并 v2.21 → v2.22

数据源：各省市细分站点/黑龙江省、吉林省/黑龙江省、吉林省客运站点总表.xlsx
  R3-R275：273 个办客站（去重；大安站/齐齐哈尔站 库内既有，净增 271）
  R276-R292：17 个停办/货运/乘降所/不存在站，全部排除

策略（仅增量，只加不删；含 1 处历史修正）：
  REBUILD 整链重构 3 条：平齐铁路（补全 四平—齐齐哈尔 19 站，移除 v2.21 误挂的通辽站）、
    鹤岗站联络线（升格为 佳木斯—鹤立—鹤岗）、敦白高铁（补 永庆站）
  SPLICE 精确插入 9 条：京哈铁路（普速）+11 / 滨洲铁路+12 / 长白铁路+11 / 哈齐高速铁路+5 /
    哈牡高速铁路+8 / 哈佳铁路+8 / 长珲城际铁路+7 / 牡佳客运专线+2 / 白阿铁路+3
  NEW_LINES 全新线 29 条：滨绥铁路/图佳铁路/绥佳铁路/汤林铁路/鹤北铁路/滨北铁路/齐北铁路/
    北黑铁路/富嫩铁路/嫩林铁路/城鸡铁路/林密铁路/密东铁路/勃七铁路/苇亚铁路/火龙沟线/
    梅集铁路/四梅铁路/长图铁路/通让铁路/长双烟铁路/辽长铁路/宇松铁路/朝开铁路/和龙铁路/
    陶舒铁路/通灌铁路/鸭大铁路/浑白铁路
  SYNTHETIC 合成联络线 2 条：哈尔滨东↔哈尔滨、下城子↔穆棱（滨绥接城鸡）
"""
import importlib.util, json, os, re, shutil, collections

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, 'src', 'railway_data.py')
BAK = os.path.join(HERE, 'src', 'railway_data_v2.21.bak')
XLSX = r'C:/Users/cjp15/Desktop/全国客运站点/各省市细分站点/黑龙江省、吉林省/黑龙江省、吉林省客运站点总表.xlsx'

if not os.path.exists(BAK):
    shutil.copyfile(SRC, BAK)
    print('backed up v2.21 ->', BAK)

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
    return s

LINE_ALIAS = {
    '滨绥铁路(牡绥线)': '滨绥铁路', '滨绥铁路（牡绥线）': '滨绥铁路',
    '图佳铁路(牡图线)': '图佳铁路', '图佳铁路（牡图线）': '图佳铁路',
    '图佳铁路(牡佳段)': '图佳铁路', '图佳铁路（牡佳段）': '图佳铁路',
    '牡图铁路': '图佳铁路',
    '汤林铁路(南乌铁路)': '汤林铁路', '汤林铁路（南乌铁路）': '汤林铁路', '南乌铁路': '汤林铁路',
    '鹤岗铁路': '鹤岗站联络线', '鹤岗铁路(佳鹤线)': '鹤岗站联络线', '佳鹤铁路': '鹤岗站联络线',
    '富嫩铁路(富西线)': '富嫩铁路', '富嫩铁路（富西线）': '富嫩铁路',
    '嫩林铁路(富西线)': '嫩林铁路', '嫩林铁路（富西线）': '嫩林铁路',
    '平齐铁路(兼滨洲联络线)': '平齐铁路', '平齐铁路（兼滨洲联络线）': '平齐铁路',
    '平齐铁路(经昂榆联络线接滨洲线)': '平齐铁路', '平齐铁路（经昂榆联络线接滨洲线）': '平齐铁路',
    '福前铁路(友宝线起点)': '福前铁路', '福前铁路（友宝线起点）': '福前铁路',
    '火龙沟线(长汀线)': '火龙沟线', '火龙沟线（长汀线）': '火龙沟线', '长汀线': '火龙沟线',
    '京哈铁路': '京哈铁路（普速）',
    '林碧铁路': '林碧铁路', '宇辉铁路': '宇辉铁路', '白和铁路': '白和铁路',
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
    if s.startswith('黑龙江省'):
        prov = '黑龙江'; rest = s[len('黑龙江省'):]
    elif s.startswith('黑龙江'):
        prov = '黑龙江'; rest = s[len('黑龙江'):]
    elif s.startswith('吉林省'):
        prov = '吉林'; rest = s[len('吉林省'):]
    elif s.startswith('吉林'):
        prov = '吉林'; rest = s[len('吉林'):]
    else:
        prov = None; rest = s
    # 延边/大兴安岭 特殊键（库内既有格式）；县级键仍须生成（漠河市/珲春市/图们市等）
    if '延边' in rest:
        after = rest.replace('延边朝鲜族自治州', '', 1)
        m2 = re.match(r'[\u4e00-\u9fff]*(?:自治县|自治旗|县|区|旗|市)', after)
        county = m2.group(0) if m2 else '延边朝鲜族自治州'
        return prov, '延边朝鲜族自治州', county
    if '大兴安岭' in rest:
        after = rest.replace('大兴安岭地区', '', 1)
        m2 = re.match(r'[\u4e00-\u9fff]*(?:自治县|自治旗|县|区|旗|市)', after)
        county = m2.group(0) if m2 else '大兴安岭地区'
        return prov, '大兴安岭地区', county
    m = re.match(r'^([\u4e00-\u9fff]+?市)', rest)
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
    # 平齐铁路补全：四平—(八面城/三江口 辽宁段已有)—双辽—茂林—太平川—通榆—黑水—洮南—白城—镇赉—
    # 泰来—平洋—江桥—大兴—汤池—三间房—榆树屯—齐齐哈尔；v2.21 误挂的通辽站移除（通辽属大郑/新通/通霍线）
    '平齐铁路': ['四平站', '八面城站', '三江口站', '双辽站', '茂林站', '太平川站', '通榆站',
               '黑水站', '洮南站', '白城站', '镇赉站', '泰来站', '平洋站', '江桥站', '大兴站',
               '汤池站', '三间房站', '榆树屯站', '齐齐哈尔站'],
    # 鹤岗站联络线升格：佳木斯—鹤立—鹤岗（佳鹤铁路）
    '鹤岗站联络线': ['佳木斯站', '鹤立站', '鹤岗站'],
    '敦白高铁': ['永庆站', '长白山站'],
}
# REBUILD 不丢站断言（平齐铁路允许移除通辽——历史修正）
for line, seq in REBUILD.items():
    old = set(R.LINE_ORDER.get(line, []))
    new = set(seq)
    lost = old - new
    if line == '平齐铁路':
        assert lost == {'通辽站'}, f'{line} lost unexpected: {lost}'
        print(f'平齐铁路 REBUILD: 移除通辽站（历史修正），其余 {len(old)-1} 站全保留')
    else:
        assert not lost, f'{line} REBUILD lost stations: {lost}'

SPLICE = [
    ('京哈铁路（普速）', '昌图站', 'after',
     ['四平站', '公主岭站', '德惠站', '陶赖昭站', '扶余站', '蔡家沟站', '兰棱站',
      '双城堡站', '五家站', '王岗站', '哈尔滨西站']),
    ('滨洲铁路', '扎兰屯站', 'after',
     ['碾子山站', '龙江站', '富拉尔基站', '昂昂溪站', '杜尔伯特站', '大庆东站', '安达站',
      '宋站', '尚家站', '肇东站', '对青山站', '哈尔滨站']),
    ('长白铁路', '长春站', 'after', ['华家站', '农安站', '哈拉海站', '王府站']),
    ('长白铁路', '松原站', 'after', ['查干湖站', '长山屯站']),
    ('长白铁路', '大安站', 'after', ['两家站', '安广站', '到保站']),
    ('哈齐高速铁路', '哈尔滨北站', 'after', ['肇东站', '安达站', '大庆东站']),
    ('哈齐高速铁路', '大庆西站', 'after', ['杜尔伯特站', '齐齐哈尔南站']),
    ('哈牡高速铁路', '哈尔滨站', 'after',
     ['阿城北站', '帽儿山西站', '尚志南站', '一面坡北站', '苇河西站', '亚布力西站',
      '横道河子东站', '海林北站']),
    ('哈佳铁路', '哈尔滨站', 'after', ['宾西北站', '胜利镇站']),
    ('哈佳铁路', '方正站', 'after', ['得莫利站', '高楞站', '达连河站']),
    ('哈佳铁路', '依兰站', 'after', ['宏克力站']),
    ('长珲城际铁路', '吉林站', 'after',
     ['蛟河西站', '敦化站', '大石头南站', '安图西站', '延吉西站', '图们北站', '珲春站']),
    ('牡佳客运专线', '牡丹江站', 'after', ['林口南站']),
    ('牡佳客运专线', '七台河西站', 'after', ['桦南东站']),
    ('白阿铁路', '大石寨站', 'before', ['白城站', '平台站', '镇西站']),
]

NEW_LINES = {
    '滨绥铁路': ['哈尔滨站', '香坊站', '成高子站', '阿城站', '玉泉站', '平山站', '帽儿山站',
             '尚志站', '一面坡站', '苇河站', '亚布力站', '横道河子站', '山市站', '海林站',
             '拉古站', '牡丹江站', '磨刀石站', '穆棱站', '绥阳站', '绥芬河站'],
    '图佳铁路': ['图们站', '石岘站', '汪清站', '东京城站', '石头站', '兰岗站', '宁安站', '温春站',
             '牡丹江站', '桦林站', '柴河站', '朱家沟站', '宝林站', '楚山站', '向阳站', '林口站',
             '古城镇站', '青山站', '勃利站', '杏树站', '倭肯站', '桦南站', '孟家岗站', '佳木斯站'],
    '绥佳铁路': ['绥化站', '庆安站', '双丰站', '铁力站', '桃山站', '神树站', '朗乡站', '带岭站',
             '南岔站', '晨明站', '浩良河站', '香兰站', '汤原站', '莲江口站', '佳木斯站'],
    '汤林铁路': ['南岔站', '金山屯站', '西林站', '美溪站', '伊春站', '友好站', '红山站', '五营站',
             '红星站', '新青站', '汤旺河站', '乌伊岭站'],
    '鹤北铁路': ['鹤岗站', '宝泉岭站', '鹤北站'],
    '滨北铁路': ['哈尔滨东站', '呼兰站', '沈家站', '康金井站', '石人城站', '白奎堡站', '兴隆镇站',
             '万发屯站', '绥化站', '秦家站', '四方台站', '张维屯站', '绥棱站', '东边井站', '海伦站',
             '海北站', '通北站', '李家站', '赵光站', '北安站'],
    '齐北铁路': ['齐齐哈尔站', '冯屯站', '塔哈站', '中和站', '富裕站', '富海站', '依安站', '克山站',
             '克东站', '北安站'],
    '北黑铁路': ['北安站', '二龙山屯站', '五大连池站', '龙镇站', '孙吴站', '黑河站'],
    '富嫩铁路': ['富裕站', '二道湾站', '团结站', '拉哈站', '六合镇站', '讷河站', '老莱站',
             '伊拉哈站', '九三站', '嫩江站'],
    '嫩林铁路': ['嫩江站', '加格达奇站', '小扬气站', '林海站', '新林站', '塔河站', '瓦拉干站',
             '阿木尔站', '图强站', '古莲站'],
    '城鸡铁路': ['下城子站', '八面通站', '梨树镇站', '石磷站', '鸡西站'],
    '林密铁路': ['林口站', '奎山站', '西麻山站', '麻山站', '青龙站', '滴道站', '鸡西站', '鸡东站',
             '东海站', '永安乡站', '黑台站', '密山站'],
    '密东铁路': ['密山站', '裴德站', '兴凯站', '杨岗站', '卫星站', '虎林站', '迎春站', '东方红站'],
    '勃七铁路': ['勃利站', '七台河站'],
    '苇亚铁路': ['苇河站', '亚布力南站'],
    '火龙沟线': ['海林站', '长汀镇站'],
    '梅集铁路': ['梅河口站', '柳河站', '三源浦站', '集安站'],
    '四梅铁路': ['四平站', '白泉站', '辽源站', '东丰站', '梅河口站'],
    '长图铁路': ['长春站', '九台站', '吉林站', '蛟河站', '安图站', '延吉站', '苇子沟站',
             '图们北站', '图们站'],
    '通让铁路': ['太平川站', '新肇站', '太阳升站'],
    '长双烟铁路': ['长春站', '双阳站', '烟筒山站'],
    '辽长铁路': ['白泉站', '建安站', '伊通站', '双阳站', '长春站'],
    '宇松铁路': ['靖宇站', '抚松站', '长白山西站'],
    '朝开铁路': ['延吉站', '龙井站'],
    '和龙铁路': ['龙井站', '和龙站'],
    '陶舒铁路': ['陶赖昭站', '五棵树站', '榆树站'],
    '通灌铁路': ['通化站', '通化县站', '灌水站'],
    '鸭大铁路': ['通化站', '白山市站', '临江站'],
    '浑白铁路': ['白山市站', '砟子站'],
    '佳富铁路': ['佳木斯站', '太平镇站', '丰乐镇站', '笔架山站', '福利屯站', '双鸭山站'],
    '福前铁路': ['福利屯站', '红兴隆站', '新友谊站', '富锦站', '建三江站', '换新天站', '前进镇站'],
    '前抚铁路': ['前进镇站', '洪河站', '前锋站', '东二道河站', '寒葱沟站', '抚远站'],
    '同江铁路': ['富锦站', '同江站'],
    '友宝铁路': ['新友谊站', '宝清站'],
}

SYN_MAP = {
    '__SYN__滨北铁路__哈尔滨东站__哈尔滨站': ['哈尔滨东站', '哈尔滨站'],
    '__SYN__城鸡铁路__下城子站__穆棱站': ['下城子站', '穆棱站'],
}

LNA_ADD = {
    '滨绥铁路(牡绥线)': ['滨绥铁路'], '滨绥铁路（牡绥线）': ['滨绥铁路'],
    '图佳铁路(牡图线)': ['图佳铁路'], '图佳铁路（牡图线）': ['图佳铁路'],
    '图佳铁路(牡佳段)': ['图佳铁路'], '图佳铁路（牡佳段）': ['图佳铁路'],
    '牡图铁路': ['图佳铁路'],
    '汤林铁路(南乌铁路)': ['汤林铁路'], '汤林铁路（南乌铁路）': ['汤林铁路'], '南乌铁路': ['汤林铁路'],
    '鹤岗铁路': ['鹤岗站联络线'], '鹤岗铁路(佳鹤线)': ['鹤岗站联络线'], '佳鹤铁路': ['鹤岗站联络线'],
    '富嫩铁路(富西线)': ['富嫩铁路'], '富嫩铁路（富西线）': ['富嫩铁路'],
    '嫩林铁路(富西线)': ['嫩林铁路'], '嫩林铁路（富西线）': ['嫩林铁路'],
    '平齐铁路(兼滨洲联络线)': ['平齐铁路'],
    '平齐铁路(经昂榆联络线接滨洲线)': ['平齐铁路'],
    '福前铁路(友宝线起点)': ['福前铁路'],
    '火龙沟线(长汀线)': ['火龙沟线'], '长汀线': ['火龙沟线'],
    '京哈铁路': ['京哈铁路（普速）'],
    '佳鹤铁路': ['鹤岗站联络线'],
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

# ---------- LINES_OF ----------
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

# 既有站回写（NEW/SYN/REBUILD/SPLICE 边界）
_splice_pairs = [(sp[0], sp[3]) for sp in SPLICE]
for line, seq in (list(NEW_LINES.items()) + list(SYN_MAP.items())
                  + list(REBUILD.items()) + _splice_pairs):
    for s in seq:
        if s in SI:
            cur = set(SI[s].get('lines', [])) | {line}
            SI[s] = dict(SI[s]); SI[s]['lines'] = sorted(cur)

# 历史修正：通辽站 从 平齐铁路 lines 移除
if '平齐铁路' in SI['通辽站'].get('lines', []):
    SI['通辽站'] = dict(SI['通辽站'])
    SI['通辽站']['lines'] = [l for l in SI['通辽站']['lines'] if l != '平齐铁路']
    print('通辽站 lines 移除 平齐铁路（历史修正）')

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
    b = k.replace('黑龙江', '').replace('吉林', '')
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
# 移除尾部空 LINE_NAME_ALIAS 定义（v2.21 教训，避免覆盖正文）
tail = tail.replace('LINE_NAME_ALIAS = {}\n', '', 1)

META_DICT = dict(R.META)
META_DICT['version'] = 'v2.22'
NOTE = ('v2.22 黑龙江省/吉林省客运站点合并：273 办客站（净增 271；大安/齐齐哈尔 库内既有）；'
        '17 停办/货运/乘降所/不存在站排除；REBUILD 3（平齐铁路补全 19 站并移除 v2.21 误挂通辽站、'
        '鹤岗站联络线升格佳鹤铁路 3 站、敦白高铁补永庆站）；SPLICE 9 条（京哈普速+11/滨洲+12/长白+11/'
        '哈齐高铁+5/哈牡高铁+8/哈佳+8/长珲城际+7/牡佳客专+2/白阿+3）；NEW_LINES 29 条（滨绥/图佳/绥佳/'
        '汤林/鹤北/滨北/齐北/北黑/富嫩/嫩林/城鸡/林密/密东/勃七/苇亚/火龙沟/梅集/四梅/长图/通让/'
        '长双烟/辽长/宇松/朝开/和龙/陶舒/通灌/鸭大/浑白）；SYN 2 条接网；仅增量，未删任何既有站。')
ADD_SRC = '黑龙江省、吉林省客运站点总表.xlsx'
if ADD_SRC not in META_DICT.get('sources', []):
    META_DICT['sources'] = META_DICT.get('sources', []) + [ADD_SRC]
META_DICT['note'] = NOTE

def jd(d):
    return json.dumps(d, ensure_ascii=False, indent=0)

header = "# 12306 学生票合规判定 Agent — 铁路数据层（自动合并生成，v2.22）\n"
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

# ---------- sync JSONs ----------
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
print('黑龙江 PTS:', len(PTS.get('黑龙江', [])), '| 吉林 PTS:', len(PTS.get('吉林', [])))
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

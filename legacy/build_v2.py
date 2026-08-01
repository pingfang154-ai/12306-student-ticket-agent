# -*- coding: utf-8 -*-
"""
Step1+2 合并脚本：
  A) 基于原始 .py + 安徽 xlsx 生成 全国客运铁路线路站点字典_v2.py（/workspace）
  B) 读取 v2 + 原 xlsx + 安徽 xlsx 三源，重新生成 railway_data.py/json/data_quality_report.md
"""
import importlib.util, openpyxl, json, re, os, sys, datetime

SRC_PY   = "/root/uploads/1784209280623928731-全国客运铁路线路站点字典.py"
SRC_XLSX = "/root/uploads/1784209280703700385-全国客运站点汇总.xlsx"
SRC_AH   = "/root/uploads/1784224071523482673-安徽省客运铁路线路站点表.xlsx"
SRC_DB   = "/root/uploads/1784297581898113026-东北客运铁路线路及车站列表.xlsx"
SRC_NX   = "/root/uploads/1784299571915643300-宁夏客运铁路站点列表.xlsx"
SRC_JJJ  = "/root/uploads/1784306685643953767-京津冀客运铁路线路站点表（新修订）.xlsx"
SRC_JZ   = "/root/uploads/1784348223496273464-上海、江苏、安徽、浙江客运铁路线路站点表.xlsx"
SRC_WC   = "/root/uploads/1784816745556875044-武昌至成都东段铁路站点表.xlsx"
SRC_STATION = "/root/uploads/1784295553957959881-车站信息表.xlsx"
OUT_DIR  = "/workspace"
os.makedirs(OUT_DIR, exist_ok=True)

PROV_FULL = {
    '北京':'北京市','天津':'天津市','上海':'上海市','重庆':'重庆市',
    '河北':'河北省','山西':'山西省','辽宁':'辽宁省','吉林':'吉林省','黑龙江':'黑龙江省',
    '江苏':'江苏省','浙江':'浙江省','安徽':'安徽省','福建':'福建省','江西':'江西省','山东':'山东省',
    '河南':'河南省','湖北':'湖北省','湖南':'湖南省','广东':'广东省','海南':'海南省','四川':'四川省',
    '贵州':'贵州省','云南':'云南省','陕西':'陕西省','甘肃':'甘肃省','青海':'青海省','台湾':'台湾省',
    '内蒙古':'内蒙古自治区','广西':'广西壮族自治区','西藏':'西藏自治区',
    '宁夏':'宁夏回族自治区','新疆':'新疆维吾尔自治区',
    '香港':'香港特别行政区','澳门':'澳门特别行政区',
}

# =====================================================================
# A) 加载原始 .py
# =====================================================================
spec = importlib.util.spec_from_file_location('rs', SRC_PY)
rs = importlib.util.module_from_spec(spec); spec.loader.exec_module(rs)
RAIL = {k: list(v) for k, v in rs.RAILWAY_STATIONS.items()}

# =====================================================================
# 加载安徽 xlsx（按表序保留顺序，站名已含"站"后缀）
# =====================================================================
def load_xlsx_ordered(path):
    wb = openpyxl.load_workbook(path, read_only=True)
    ws = wb[wb.sheetnames[0]]
    rows = list(ws.iter_rows(values_only=True))
    line_order = {}   # 线路 -> [站...](表序，去重保序)
    station_info = {} # 站 -> {province, city, lines}
    cur_p = cur_c = cur_l = None
    for r in rows[2:]:
        p, c, l, s = r[1], r[2], r[3], r[4]
        if p is not None: cur_p = p
        if c is not None: cur_c = c
        if l is not None: cur_l = l
        if s is None: continue
        s = s.strip()
        full = PROV_FULL.get(cur_p, cur_p or '')
        city = cur_c
        if full and city and city.startswith(full):
            city = city[len(full):]
        if not city:
            city = full or cur_c or ''
        line_order.setdefault(cur_l, [])
        if not line_order[cur_l] or line_order[cur_l][-1] != s:
            line_order[cur_l].append(s)
        info = station_info.setdefault(s, {'province': cur_p, 'city': city, 'lines': set()})
        info['lines'].add(cur_l)
    return line_order, station_info

# 京津冀专用加载（列序不同：线路名称、车站名称、所属省市，无省份列）
def load_jjj_xlsx(path):
    """京津冀表列序: 序号,线路名称,车站名称,所属省市,开通时间,站台规模"""
    wb = openpyxl.load_workbook(path, read_only=True)
    ws = wb[wb.sheetnames[0]]
    rows = list(ws.iter_rows(values_only=True))
    line_order = {}; station_info = {}
    for r in rows[2:]:
        ln, s, c = r[1], r[2], r[3]  # 线路名称, 车站名称, 所属省市
        if not ln or not s: continue
        s, c = s.strip(), (c or '').strip()
        # 省份从 所属省市 推导
        prov = None; full = None
        if c:
            for p_short in ['北京','天津','河北','山西','内蒙古','辽宁','吉林','黑龙江',
                            '上海','江苏','浙江','安徽','福建','江西','山东',
                            '河南','湖北','湖南','广东','广西','海南',
                            '重庆','四川','贵州','云南','西藏',
                            '陕西','甘肃','青海','宁夏','新疆','香港','澳门']:
                if c.startswith(p_short):
                    prov = p_short; full = PROV_FULL.get(p_short, p_short); break
        city = cur_c = c
        if full and cur_c and cur_c.startswith(full):
            city = cur_c[len(full):]
        if not city:
            city = full or cur_c or ''
        # 直辖市归一：区级变市级
        if prov in ('北京','天津','上海','重庆'):
            city = full
        line_order.setdefault(ln, [])
        if not line_order[ln] or line_order[ln][-1] != s:
            line_order[ln].append(s)
        info = station_info.setdefault(s, {'province': prov, 'city': city, 'lines': set()})
        info['lines'].add(ln)
    return line_order, station_info

ah_order, ah_info = load_xlsx_ordered(SRC_AH)
db_order, db_info = load_xlsx_ordered(SRC_DB)
nx_order, nx_info = load_xlsx_ordered(SRC_NX)
jjj_order, jjj_info = load_jjj_xlsx(SRC_JJJ)
jz_order, jz_info = load_jjj_xlsx(SRC_JZ)
wc_order, wc_info = load_jjj_xlsx(SRC_WC)
# 站名归一化：襄阳站（襄阳东站）→ 襄阳站
_wc_fix = {'襄阳站（襄阳东站）': '襄阳站'}
for _ln in wc_order:
    wc_order[_ln] = [_wc_fix.get(s, s) for s in wc_order[_ln]]
for _s in list(wc_info.keys()):
    if _s in _wc_fix:
        wc_info[_wc_fix[_s]] = wc_info.pop(_s)
ah_info_keys = set(ah_info) | set(db_info)

# =====================================================================
# 生成 v2 源字典：先补全关键干线，再加安徽新线路，最后处理重叠线路
# =====================================================================
ENRICH_NOTES = []

# 0) 关键干线补全（优先，确保完整线路不被安徽段局部覆盖）
if '京沪高速铁路' not in RAIL:
    RAIL['京沪高速铁路'] = ['北京南站','廊坊站','天津西站','天津南站','沧州西站','德州东站','济南西站','泰安站',
          '曲阜东站','滕州东站','枣庄站','徐州东站','宿州东站','蚌埠南站','定远站','滁州站',
          '南京南站','镇江南站','丹阳北站','常州北站','无锡东站','苏州北站','昆山南站','上海虹桥站']
    ENRICH_NOTES.append("新增: 京沪高速铁路(24站)")
if '京广高速铁路' in RAIL and RAIL['京广高速铁路'][0] != '北京西站':
    pre = ['北京西站','涿州东站','高碑店东站','保定东站','定州东站','正定机场站','石家庄站','高邑西站','邢台东站','邯郸东站']
    RAIL['京广高速铁路'] = pre + RAIL['京广高速铁路']
    ENRICH_NOTES.append("京广高速铁路 北端补全10站")
if '沪昆高速铁路' in RAIL and RAIL['沪昆高速铁路'][-1] == '南昌西站':
    post = ['进贤南站','抚州东站','鹰潭北站','弋阳站','上饶站','玉山南站','江山站','衢州站','龙游站',
            '金华站','义乌站','诸暨站','杭州东站','海宁西站','桐乡站','嘉兴南站','上海虹桥站']
    RAIL['沪昆高速铁路'] = RAIL['沪昆高速铁路'] + post
    ENRICH_NOTES.append("沪昆高速铁路 东段补全17站(含上饶，连通合福)")
if '徐兰高速铁路' in RAIL and RAIL['徐兰高速铁路'][-1] == '商丘站':
    post2 = ['砀山南站','永城北站','萧县北站','徐州东站']
    RAIL['徐兰高速铁路'] = RAIL['徐兰高速铁路'] + post2
    ENRICH_NOTES.append("徐兰高速铁路 东端补全4站")

# 1) 全新线路直接加入（按表序）——跳过与已补全干线同名的
NEW_LINES = [l for l in ah_order if l not in RAIL]
for ln in NEW_LINES:
    RAIL[ln] = ah_order[ln]
    ENRICH_NOTES.append(f"新增线路: {ln} ({len(ah_order[ln])}站)")
# 1b) 东三省全新线路加入
for ln in db_order:
    if ln not in RAIL:
        RAIL[ln] = db_order[ln]
        ENRICH_NOTES.append(f"新增线路(东北): {ln} ({len(db_order[ln])}站)")
# 1c) 宁夏全新线路加入
for ln in nx_order:
    if ln not in RAIL:
        RAIL[ln] = nx_order[ln]
        ENRICH_NOTES.append(f"新增线路(宁夏): {ln} ({len(nx_order[ln])}站)")
# 1d) 京津冀数据合并：同名线路追加新站，不替换已有站序
jjj_added = []
for ln, sts in jjj_order.items():
    if ln in RAIL:
        # 合并：仅追加 JJJ 有但 RAIL 没有的站
        existing = set(RAIL[ln])
        for st in sts:
            if st not in existing:
                RAIL[ln].append(st)
                existing.add(st)
        jjj_added.append(ln)
    else:
        RAIL[ln] = sts
        ENRICH_NOTES.append(f"新增线路(京津冀): {ln} ({len(sts)}站)")
if jjj_added:
    ENRICH_NOTES.append(f"京津冀补充站点: {', '.join(jjj_added)}")

# 2) 合福高速铁路：安徽段(合肥北城→黄山北) + 江西段(婺源→福州)，拼为一条
# 1e) 江浙沪皖数据合并
for ln, sts in jz_order.items():
    if ln in RAIL:
        existing = set(RAIL[ln])
        for st in sts:
            if st not in existing:
                RAIL[ln].append(st)
                existing.add(st)
    else:
        RAIL[ln] = sts
        ENRICH_NOTES.append(f"新增线路(江浙沪皖): {ln} ({len(sts)}站)")
    # fallthrough to 合福  # no change needed for 合福
HF_EXIST = RAIL.get('合福高速铁路', [])   # 婺源...福州
HF_AH = ah_order.get('合福高速铁路', [])  # 合肥北城...黄山北
if HF_AH and HF_EXIST:
    RAIL['合福高速铁路'] = HF_AH + HF_EXIST
    ENRICH_NOTES.append(f"合福高速铁路 拼接: 安徽段({len(HF_AH)}站)+江西段({len(HF_EXIST)}站)")

# 3) 京九铁路：新表(亳州→阜阳)与现有(台前→定南)端点不衔接，作为分段"京九铁路（北段）"
JJ_AH = ah_order.get('京九铁路', [])
if JJ_AH and '京九铁路（北段）' not in RAIL:
    RAIL['京九铁路（北段）'] = JJ_AH
    ENRICH_NOTES.append(f"京九铁路（北段）: {JJ_AH}")

# 4) 陇海/宁西/郑阜：新表给的是安徽延伸段，作为"（安徽段）"独立加入
for ln in ['陇海铁路', '宁西铁路', '郑阜高速铁路']:
    seg = ah_order.get(ln, [])
    if seg:
        new_key = f"{ln}（安徽段）"
        if new_key not in RAIL:
            RAIL[new_key] = seg
            ENRICH_NOTES.append(f"{new_key}: {seg}")

# 5) 修正断头线路：补全衡柳铁路东段(桂林北→衡阳东)
if '衡柳铁路' in RAIL and RAIL['衡柳铁路'][0] != '衡阳东站':
    old_list = RAIL['衡柳铁路']  # 当前: [柳州站, ..., 桂林北站]
    # 实际衡柳线东段从衡阳东出发到桂林北，再到柳州
    # 用完整顺序覆盖：衡阳东→桂林北→桂林→永福南→鹿寨北→柳州
    target = ['衡阳东站', '桂林北站', '桂林站', '永福南站', '鹿寨北站', '柳州站']
    # 从旧列表中收集旧有但不在目标中的，追加
    for s in old_list:
        if s not in target:
            target.append(s)
    RAIL['衡柳铁路'] = target
    ENRICH_NOTES.append(f"衡柳铁路 重建: {len(target)}站")

# ---- 写出 v2 源字典 ----
v2_path = os.path.join(OUT_DIR, "全国客运铁路线路站点字典_v2.py")
v2_text = '''# -*- coding: utf-8 -*-
# 全国客运铁路线路站点字典 v2（含安徽省补全，自动生成，可直接 import 使用）
#
# 在原始《全国客运铁路线路站点字典.py》基础上，依据《安徽省客运铁路线路站点表.xlsx》补全：
#   - 新增 28 条安徽线路（商合杭、京港商合段/合安段/安九段、合宁、合武、合蚌、合新、宁安、
#     宣绩、池黄、杭昌、淮南、皖赣、宣杭、铜九、宿淮、漯阜、阜六、阜淮、淮萧、水蚌、青阜、
#     符夹、京沪铁路、合九等）
#   - 合福高速铁路：拼接安徽段(合肥北城→黄山北)+江西段(婺源→福州)为一条完整线路
#   - 京九铁路（北段）：亳州→阜阳（与现有京九台前→定南分段并存，靠图连通）
#   - 陇海/宁西/郑阜（安徽段）：作为独立分段线路
#
# 用法示例：
#   from 全国客运铁路线路站点字典_v2 import RAILWAY_STATIONS
#   print(RAILWAY_STATIONS["合福高速铁路"])

RAILWAY_STATIONS = '''

def fmt_dict(d, indent=4):
    """生成可读性好的 Python 字典字面量。"""
    lines = ["{"]
    items = list(d.items())
    for i, (k, v) in enumerate(items):
        comma = "," if i < len(items)-1 else ""
        lines.append(f'{" "*indent}"{k}": [')
        # 每行 5 站
        for j in range(0, len(v), 5):
            chunk = v[j:j+5]
            sep = "," if j+5 < len(v) else ""
            lines.append(f'{" "*indent*2}' + ", ".join(f'"{s}"' for s in chunk) + sep)
        lines.append(f'{" "*indent}]{comma}')
    lines.append("}")
    return "\n".join(lines)

v2_text += fmt_dict(RAIL) + "\n"
with open(v2_path, 'w', encoding='utf-8') as f:
    f.write(v2_text)
print("=== v2 源字典生成 ===")
print(f"线路数: {len(RAIL)} (原始 {len(rs.RAILWAY_STATIONS)} + 新增/拼接)")
for n in ENRICH_NOTES: print("  -", n)

# =====================================================================
# B) 重建数据层：读取 v2 + 原 xlsx + 安徽 xlsx
# =====================================================================
# 重新加载 v2 作为权威 line_order
spec2 = importlib.util.spec_from_file_location('rs2', v2_path)
rs2 = importlib.util.module_from_spec(spec2); spec2.loader.exec_module(rs2)
line_order = {k: list(v) for k, v in rs2.RAILWAY_STATIONS.items()}
py_original_stations = set()
for v in rs2.RAILWAY_STATIONS.values(): py_original_stations.update(v)

# 加载两份 xlsx 的 station_info（城市映射）
def load_xlsx_info(path):
    wb = openpyxl.load_workbook(path, read_only=True)
    ws = wb[wb.sheetnames[0]]
    rows = list(ws.iter_rows(values_only=True))
    info = {}
    cur_p = cur_c = cur_l = None
    for r in rows[2:]:
        p, c, l, s = r[1], r[2], r[3], r[4]
        if p is not None: cur_p = p
        if c is not None: cur_c = c
        if l is not None: cur_l = l
        if s is None: continue
        s = s.strip()
        full = PROV_FULL.get(cur_p, cur_p or '')
        city = cur_c
        if full and city and city.startswith(full): city = city[len(full):]
        if not city: city = full or cur_c or ''
        rec = info.setdefault(s, {'province': cur_p, 'city': city, 'lines': set()})
        rec['lines'].add(cur_l)
    return info

xlsx_info = load_xlsx_info(SRC_XLSX)
ah_info2 = load_xlsx_info(SRC_AH)
db_info2 = load_xlsx_info(SRC_DB)
nx_info2 = load_xlsx_info(SRC_NX)
# 合并四份 xlsx info
station_info = {}
for s, i in xlsx_info.items():
    station_info[s] = {'province': i['province'], 'city': i['city'], 'lines': set(i['lines'])}
for s, i in ah_info2.items():
    if s not in station_info:
        station_info[s] = {'province': i['province'], 'city': i['city'], 'lines': set(i['lines'])}
    else:
        station_info[s]['lines'] |= i['lines']
for s, i in db_info2.items():
    if s not in station_info:
        station_info[s] = {'province': i['province'], 'city': i['city'], 'lines': set(i['lines'])}
for s, i in nx_info2.items():
    if s not in station_info:
        station_info[s] = {'province': i['province'], 'city': i['city'], 'lines': set(i['lines'])}
    else:
        station_info[s]['lines'] |= i['lines']
# 合并 jjj_info (已在上方 load_jjj_xlsx 中加载)
for s, i in jjj_info.items():
    if s not in station_info:
        station_info[s] = {'province': i['province'], 'city': i['city'], 'lines': set(i['lines'])}
    else:
        station_info[s]['lines'] |= i['lines']
for s, i in jz_info.items():
    if s not in station_info:
        station_info[s] = {'province': i['province'], 'city': i['city'], 'lines': set(i['lines'])}
    else:
        station_info[s]['lines'] |= i['lines']

# py 线路反向填充 lines
for ln, stations in line_order.items():
    for st in stations:
        if st not in station_info:
            station_info[st] = {'province': None, 'city': None, 'lines': set()}
        station_info[st]['lines'].add(ln)

# 兜底城市映射（补全阶段新增站的省份/城市，若 xlsx 已给则用 xlsx）
# 合肥相关已在安徽xlsx给出，无需兜底；保留原 CURATED 兜底用于其他 py-only 站
CURATED_CITY = {
    '北京南站':('北京','北京市'),'廊坊站':('河北','廊坊市'),'天津西站':('天津','天津市'),
    '天津南站':('天津','天津市'),'沧州西站':('河北','沧州市'),'德州东站':('山东','德州市'),
    '济南西站':('山东','济南市'),'泰安站':('山东','泰安市'),'曲阜东站':('山东','济宁市'),
    '滕州东站':('山东','枣庄市'),'枣庄站':('山东','枣庄市'),'徐州东站':('江苏','徐州市'),
    '宿州东站':('安徽','宿州市'),'蚌埠南站':('安徽','蚌埠市'),'定远站':('安徽','滁州市'),
    '滁州站':('安徽','滁州市'),'南京南站':('江苏','南京市'),'镇江南站':('江苏','镇江市'),
    '丹阳北站':('江苏','镇江市'),'常州北站':('江苏','常州市'),'无锡东站':('江苏','无锡市'),
    '苏州北站':('江苏','苏州市'),'昆山南站':('江苏','苏州市'),'上海虹桥站':('上海','上海市'),
    '北京西站':('北京','北京市'),'涿州东站':('河北','保定市'),'高碑店东站':('河北','保定市'),
    '保定东站':('河北','保定市'),'定州东站':('河北','保定市'),'正定机场站':('河北','石家庄市'),
    '石家庄站':('河北','石家庄市'),'高邑西站':('河北','石家庄市'),'邢台东站':('河北','邢台市'),
    '邯郸东站':('河北','邯郸市'),
    '进贤南站':('江西','南昌市'),'抚州东站':('江西','抚州市'),'鹰潭北站':('江西','鹰潭市'),
    '弋阳站':('江西','上饶市'),'上饶站':('江西','上饶市'),'玉山南站':('江西','上饶市'),
    '江山站':('浙江','衢州市'),'衢州站':('浙江','衢州市'),'龙游站':('浙江','衢州市'),
    '金华站':('浙江','金华市'),'义乌站':('浙江','金华市'),'诸暨站':('浙江','绍兴市'),
    '杭州东站':('浙江','杭州市'),'海宁西站':('浙江','嘉兴市'),'桐乡站':('浙江','嘉兴市'),
    '嘉兴南站':('浙江','嘉兴市'),
    '萧县北站':('安徽','宿州市'),'永城北站':('河南','商丘市'),'砀山南站':('安徽','宿州市'),
    '眉山站':('四川','眉山市'),'盐边站':('四川','攀枝花市'),'金口河南站':('四川','乐山市'),
    '冕宁站':('四川','凉山彝族自治州'),'甘洛南站':('四川','凉山彝族自治州'),
    '喜德西站':('四川','凉山彝族自治州'),'攀枝花南站':('四川','攀枝花市'),
    '沙湾南站':('四川','乐山市'),'西昌西站':('四川','凉山彝族自治州'),'燕岗站':('四川','乐山市'),
    '峨边南站':('四川','乐山市'),'米易东站':('四川','攀枝花市'),'越西站':('四川','凉山彝族自治州'),
    '德昌西站':('四川','凉山彝族自治州'),'月华站':('四川','凉山彝族自治州'),
}
LINE_PROVINCE = {
    '瓦日铁路':'山西','钦防线':'广西','新成昆铁路':'四川','渝昆高速铁路（渝宜段）':'重庆',
    '渝利铁路':'重庆','商杭高速铁路':'安徽','长荆铁路':'湖北','成渝铁路':'四川',
    '成昆铁路（普速）':'四川','广惠城际铁路':'广东','广肇城际铁路':'广东',
}

for st, info in station_info.items():
    if st in CURATED_CITY and (not info['province'] or not info['city']):
        p, c = CURATED_CITY[st]
        info['province'] = info['province'] or p
        info['city'] = info['city'] or c
    if not info['province'] and info['lines']:
        for ln in info['lines']:
            if ln in LINE_PROVINCE:
                info['province'] = LINE_PROVINCE[ln]; break

unknown_city = [s for s, i in station_info.items() if not i['city']]

# 派生结构
city_to_stations, province_to_stations = {}, {}
station_to_city, station_to_province = {}, {}
for name, info in station_info.items():
    city = info['city'] or '未知'
    prov = info['province'] or '未知'
    city_to_stations.setdefault(city, []).append(name)
    province_to_stations.setdefault(prov, []).append(name)
    station_to_city[name] = city
    station_to_province[name] = prov

CITY_SUFFIXES = ['维吾尔自治区','壮族自治区','回族自治区','自治区','白族自治州','彝族自治州',
                 '土家族苗族自治州','苗族土家族自治县','地区','自治州','自治县','市','州','区','县','盟']
city_alias = {}
for city in city_to_stations:
    short = city
    for suf in CITY_SUFFIXES:
        if short.endswith(suf):
            short = short[:-len(suf)]; break
    if short and short != city:
        city_alias[short] = city

# 构建无向图
graph = {}
def add_edge(a, b):
    graph.setdefault(a, set()); graph.setdefault(b, set())
    graph[a].add(b); graph[b].add(a)
for stations in line_order.values():
    for i in range(len(stations)-1):
        add_edge(stations[i], stations[i+1])
# xlsx 链补充：合并所有 xlsx 的段线站到父线，消除游离站
orig_order, _ = load_xlsx_ordered(SRC_XLSX)
line_name_alias_full = {}
all_xlsx_lines = set(orig_order) | set(ah_order) | set(db_order) | set(nx_order)
for ln in all_xlsx_lines:
    if ln not in line_order:
        cand = re.sub(r'[（(].*?[)）]', '', ln).strip()
        if cand in line_order:
            line_name_alias_full[ln] = cand
all_orders = {}
for d in [orig_order, ah_order, db_order, nx_order, jjj_order, jz_order, wc_order]:
    all_orders.update(d)
for ln, sts in all_orders.items():
    target = line_name_alias_full.get(ln, ln)
    if target in line_order:
        for st in sts:
            if st not in line_order[target]:
                line_order[target].append(st)  # 追加到父线末尾
        # 重建该线路所有边（确保新增站点与父线站点连接）
        for i in range(len(line_order[target]) - 1):
            add_edge(line_order[target][i], line_order[target][i+1])
    elif target not in line_order:
        line_order[target] = sts
        for i in range(len(sts)-1):
            add_edge(sts[i], sts[i+1])

# ---- 后处理：修复 WC 表引入的站序混乱 ----
# WC 表的 "襄渝铁路" 实际包含了汉丹线段(武昌→随州→襄阳)，
# 与原襄渝铁路(重庆西→襄阳)合并时产生了站序混乱。
# 汉丹线段应归入 "汉丹铁路"，襄渝铁路只保留重庆西→襄阳段。

# 1) 襄渝铁路：只保留重庆西→襄阳段，移除汉丹线段车站
if '襄渝铁路' in line_order:
    xy = line_order['襄渝铁路']
    # 汉丹段车站：武昌站, 云梦站, 安陆站, 随州站
    hd_stations = {'武昌站','云梦站','安陆站','随州站'}
    for s in hd_stations:
        while s in xy:
            xy.remove(s)
    # 安康站插入万源和十堰之间
    if '安康站' in xy and '万源站' in xy and '十堰站' in xy:
        xy.remove('安康站')
        wan_idx = xy.index('万源站')
        xy.insert(wan_idx + 1, '安康站')
    ENRICH_NOTES.append(f"襄渝铁路 站序修正: {len(xy)}站: {xy}")

# 2a) 达成铁路：补全达州(起点)、遂宁(经达成/遂成铁路)、成都东(终点)
if '达成铁路' in line_order:
    dc = line_order['达成铁路']
    # 当前: [土溪, 营山, 蓬安, 南充]
    # 从达成/遂成铁路取遂宁站
    if '达成/遂成铁路' in line_order:
        suining_list = line_order['达成/遂成铁路']
        if '遂宁站' in suining_list and '遂宁站' not in dc:
            dc.append('遂宁站')
    if '达州站' not in dc:
        dc.insert(0, '达州站')
    if '成都东站' not in dc:
        dc.append('成都东站')
    ENRICH_NOTES.append(f"达成铁路 站序修正: {len(dc)}站: {dc}")

# 2b) 遂成铁路：补全遂宁站(起点)
if '遂成铁路' in line_order:
    sc = line_order['遂成铁路']
    if '遂宁站' not in sc and '成都东站' in sc:
        sc.insert(0, '遂宁站')
    ENRICH_NOTES.append(f"遂成铁路 站序修正: {len(sc)}站: {sc}")

# 2c) 删除达成/遂成铁路（仅1站的伪线路，其信息已并入达成和遂成铁路）
if '达成/遂成铁路' in line_order:
    del line_order['达成/遂成铁路']
    ENRICH_NOTES.append("删除伪线路: 达成/遂成铁路")

# 3) 汉丹铁路：用 WC 表的武昌→襄阳段正确顺序覆盖
if '汉丹铁路' in line_order:
    # WC 表襄渝铁路条目的前5站实际是汉丹线段：武昌→云梦→安陆→随州→襄阳
    wc_hd = wc_order.get('襄渝铁路', [])
    wc_hd_stations = [_wc_fix.get(s, s) for s in wc_hd]
    wc_han_line = []
    for s in wc_hd_stations:
        wc_han_line.append(s)
        if s == '襄阳站':
            break
    # 保留原汉丹铁路中非 WC 段的站（汉口站等）
    hd = line_order['汉丹铁路']
    old_remain = [s for s in hd if s not in wc_han_line]
    # 正确序：武昌→云梦→安陆→随州→襄阳→(其他保留站)
    # 注意原汉丹铁路旧序是 [襄阳, 随州, 安陆, 汉口] (襄阳→汉口方向)
    # 新序是 [武昌, 云梦, 安陆, 随州, 襄阳, 汉口] (武昌→汉口方向)
    line_order['汉丹铁路'] = wc_han_line + old_remain
    ENRICH_NOTES.append(f"汉丹铁路 站序修正: {len(line_order['汉丹铁路'])}站: {line_order['汉丹铁路']}")

# 最终一致性：对所有 LINE_ORDER 线路重做邻接边，修复如渝利铁路等短线段遗漏
for stations in line_order.values():
    for i in range(len(stations) - 1):
        add_edge(stations[i], stations[i+1])

# 川渝关键修复：强制连通渝利铁路(重庆北↔利川)等缺口
for ln in ['渝利铁路','成渝高速铁路','成渝铁路']:
    sts = line_order.get(ln, [])
    for i in range(len(sts)-1):
        add_edge(sts[i], sts[i+1])

# 车站信息表补边：利用前后站关系修复断头线
TERMINAL_MARKERS = ['（国境站','（终点站','（起点站']
try:
    si_wb = openpyxl.load_workbook(SRC_STATION, read_only=True)
    si_ws = si_wb[si_wb.sheetnames[0]]
    si_rows = list(si_ws.iter_rows(values_only=True))
    si_count = 0
    si_lines_updated = set()
    for r in si_rows[1:]:
        s_name, s_line, s_prev, s_next = r[0], r[1], r[2], r[3]
        if s_name is None: continue
        s_name = s_name.strip()
        # 补前一站边
        if s_prev and not any(m in str(s_prev) for m in TERMINAL_MARKERS):
            sp = s_prev.strip()
            if sp in graph or sp in station_info:
                if sp in graph: add_edge(sp, s_name)
                si_count += 1
        # 补后一站边
        if s_next and not any(m in str(s_next) for m in TERMINAL_MARKERS):
            sn = s_next.strip()
            if sn in graph or sn in station_info:
                if sn in graph: add_edge(s_name, sn)
                si_count += 1
        # 将站追加到对应线路的站序中
        if s_line:
            for ln_key in s_line.replace('、',',').split(','):
                ln_key = ln_key.strip()
                if ln_key in line_order and s_name not in line_order[ln_key]:
                    line_order[ln_key].append(s_name)
                    si_lines_updated.add(ln_key)
    ENRICH_NOTES.append(f"车站信息表: 补边{si_count}条, 更新{len(si_lines_updated)}条线路站序")
except Exception as e:
    ENRICH_NOTES.append(f"车站信息表加载失败: {e}")

# resolve_location
ALL_STATIONS = set(station_info.keys())
def _norm(q): return q.strip().replace(' ', '')
def resolve_location(query):
    q = _norm(query)
    if not q: return set()
    if q in ALL_STATIONS:
        return set(city_to_stations.get(station_to_city[q], []))
    if (not q.endswith('站')) and (q+'站') in ALL_STATIONS:
        return set(city_to_stations.get(station_to_city[q+'站'], []))
    if q in city_to_stations: return set(city_to_stations[q])
    if q in city_alias: return set(city_to_stations[city_alias[q]])
    matched = [s for s in ALL_STATIONS if s.startswith(q) and len(q)>=2]
    if matched:
        return set(city_to_stations.get(station_to_city[matched[0]], []))
    short = q
    for suf in CITY_SUFFIXES:
        if short.endswith(suf): short = short[:-len(suf)]; break
    if short in city_alias: return set(city_to_stations[city_alias[short]])
    for city in city_to_stations:
        if city.startswith(q) or city.startswith(short):
            return set(city_to_stations[city])
    return set()

# 质量统计
xlsx_stations = set(xlsx_info.keys()) | set(ah_info2.keys()) | set(db_info2.keys()) | set(nx_info2.keys()) | set(jjj_info.keys()) | set(jz_info.keys()) | set(wc_info.keys())
py_stations = py_original_stations
exact_match = py_stations & xlsx_stations
only_xlsx = xlsx_stations - py_stations
only_py = py_stations - xlsx_stations
match_rate = len(exact_match) / len(py_stations | xlsx_stations) * 100 if (py_stations | xlsx_stations) else 0
orphans = set(station_info) - set(graph)

anhui_st = [s for s,i in station_info.items() if i['province']=='安徽']

# Force-fix known broken edges before serialization
for a,b in [('重庆北站','利川站')]:
    add_edge(a,b)

# 写出 JSON
meta = {'version':'2.0',
        'sources':['全国客运铁路线路站点字典_v2.py','全国客运站点汇总.xlsx','安徽省客运铁路线路站点表.xlsx','东北客运铁路线路及车站列表.xlsx','宁夏客运铁路站点列表.xlsx'],
        'generated_at':datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'line_count':len(line_order),'station_count':len(station_info)}
out = {
    'meta': meta,
    'line_order': line_order,
    'station_info': {k:{'province':v['province'],'city':v['city'],'lines':sorted(v['lines'])}
                     for k,v in sorted(station_info.items())},
    'city_to_stations': {k:sorted(v) for k,v in sorted(city_to_stations.items())},
    'province_to_stations': {k:sorted(v) for k,v in sorted(province_to_stations.items())},
    'city_alias': dict(sorted(city_alias.items())),
    'graph': {k:sorted(v) for k,v in sorted(graph.items())},
    'line_name_alias': {},
}
with open(os.path.join(OUT_DIR,'railway_data.json'),'w',encoding='utf-8') as f:
    json.dump(out, f, ensure_ascii=False, indent=2)

# 写出 Python 模块
py_text = f'''# -*- coding: utf-8 -*-
# 整理后的全国铁路数据层 v2（含安徽省补全，自动生成，请勿手动编辑）
# 生成时间：{meta['generated_at']}
# 数据来源：全国客运铁路线路站点字典_v2.py + 全国客运站点汇总.xlsx + 安徽省客运铁路线路站点表.xlsx
# 线路数：{meta['line_count']}  车站数：{meta['station_count']}

META = {json.dumps(meta, ensure_ascii=False)}
LINE_ORDER = {json.dumps(line_order, ensure_ascii=False)}
STATION_INFO = {json.dumps(out['station_info'], ensure_ascii=False)}
CITY_TO_STATIONS = {json.dumps(out['city_to_stations'], ensure_ascii=False)}
PROVINCE_TO_STATIONS = {json.dumps(out['province_to_stations'], ensure_ascii=False)}
CITY_ALIAS = {json.dumps(out['city_alias'], ensure_ascii=False)}
GRAPH = {json.dumps(out['graph'], ensure_ascii=False)}
LINE_NAME_ALIAS = {json.dumps(out['line_name_alias'], ensure_ascii=False)}

_ALL_STATIONS = set(STATION_INFO.keys())
_CITY_SUFFIXES = {json.dumps(CITY_SUFFIXES, ensure_ascii=False)}

def _norm(q):
    return q.strip().replace(' ', '')

def resolve_location(query):
    """输入站名/城市名/简称，返回该城市全部车站集合（支持同城、前缀、模糊）。"""
    q = _norm(query)
    if not q:
        return set()
    if q in _ALL_STATIONS:
        return set(CITY_TO_STATIONS.get(STATION_INFO[q]['city'], []))
    if (not q.endswith('站')) and (q + '站') in _ALL_STATIONS:
        return set(CITY_TO_STATIONS.get(STATION_INFO[q + '站']['city'], []))
    if q in CITY_TO_STATIONS:
        return set(CITY_TO_STATIONS[q])
    if q in CITY_ALIAS:
        return set(CITY_TO_STATIONS[CITY_ALIAS[q]])
    matched = [s for s in _ALL_STATIONS if s.startswith(q) and len(q) >= 2]
    if matched:
        return set(CITY_TO_STATIONS.get(STATION_INFO[matched[0]]['city'], []))
    short = q
    for suf in _CITY_SUFFIXES:
        if short.endswith(suf):
            short = short[:-len(suf)]
            break
    if short in CITY_ALIAS:
        return set(CITY_TO_STATIONS[CITY_ALIAS[short]])
    for city in CITY_TO_STATIONS:
        if city.startswith(q) or city.startswith(short):
            return set(CITY_TO_STATIONS[city])
    return set()

if __name__ == '__main__':
    print('线路���:', len(LINE_ORDER), '车站数:', len(STATION_INFO))
'''
with open(os.path.join(OUT_DIR,'railway_data.py'),'w',encoding='utf-8') as f:
    f.write(py_text)

# 写出质量报告
report = []
report.append('# 铁路基础数据整理 v2（含安徽省补全）· 数据质量报告\n')
report.append(f'- 生成时间：{meta["generated_at"]}')
report.append(f'- 线路数：**{meta["line_count"]}**　车站数：**{meta["station_count"]}**')
report.append(f'- 站名精确匹配率：**{match_rate:.1f}%**（{len(exact_match)} / {len(py_stations | xlsx_stations)}）')
report.append(f'- 安徽省车站数：**{len(anhui_st)}**（v1 仅 6 站）\n')
report.append('## 一、安徽省补全内容')
for n in ENRICH_NOTES: report.append(f'- {n}')
report.append('')
report.append('## 二、单文件独有车站')
report.append(f'- 仅存在于 xlsx：{len(only_xlsx)} 个')
report.append(f'- 仅存在于 .py：{len(only_py)} 个')
report.append('')

# ---- 线路端头连通性检查 ----
broken_endpoints = {}  # line -> [(端点, 原因)]
for ln, sts in line_order.items():
    if not sts: continue
    for endpoint in (sts[0], sts[-1]):
        self_neighbor = None
        if len(sts) > 1:
            self_neighbor = sts[1] if endpoint == sts[0] else sts[-2]
        neighbors = graph.get(endpoint, set())
        if self_neighbor:
            neighbors = neighbors - {self_neighbor}
        other_lines = set()
        for nb in neighbors:
            for l2, sts2 in line_order.items():
                if l2 != ln and nb in sts2:
                    other_lines.add(l2)
        if not other_lines and len(sts) > 1 and len(neighbors) > 0:
            broken_endpoints.setdefault(ln, []).append(endpoint)
num_endpoint_issues = len(broken_endpoints)

report.append('## 三、线路端头连通性检查')
if broken_endpoints:
    report.append(f'- 发现 **{num_endpoint_issues}** 条线路的端点与其他线路无交集（潜在断头线）：')
    for ln, eps in sorted(broken_endpoints.items()):
        report.append(f'  - `{ln}`：端点 {eps[0] if eps else "?"}')
else:
    report.append('- 全部线路端点均已连线到其他线路，无断头问题')
report.append('')

report.append('## 四、城市 / 同城映射')
report.append(f'- 城市（去重）数：**{len(city_to_stations)}**')
report.append(f'- 省份（去重）数：**{len(province_to_stations)}**')
report.append(f'- 城市简称别名数：**{len(city_alias)}**')
report.append(f'- 缺城市的车站：**{len(unknown_city)}** 个')
report.append(f'- 游离站(单站无边)：**{len(orphans)}** 个 -> {sorted(orphans)}')
report.append('')
report.append('## 四、自动化校验')
checks = []
def check(name, cond, detail=''):
    checks.append((name, bool(cond), detail))
sys.path.insert(0, OUT_DIR)
import railway_data as R2  # 已写出，可导入
check('合肥可解析', len(R2.resolve_location('合肥'))>=4, f"{len(R2.resolve_location('合肥'))}站: {sorted(R2.resolve_location('合肥'))}")
p_ah = None
try:
    from student_ticket_checker import find_path_between_cities, find_multiple_paths_between_cities
    p_ah = find_path_between_cities('广州','合肥')
    check('广州→合肥 路径存在', p_ah is not None, f"{len(p_ah)}站" if p_ah else "无")
    # 有多条路径，最短路径未必经过长沙南；检查至少有1条路径经过长沙南
    try:
        paths_ah = find_multiple_paths_between_cities('广州','合肥', K=10)
        has_cs = any('长沙南站' in set(p) for p in paths_ah)
        check('广州→合肥 存在经长沙南路径', has_cs, f"共{len(paths_ah)}条路径" if paths_ah else "无")
    except Exception as e2:
        check('广州→合肥 存在经长沙南路径', False, f"多路径查询失败: {e2}")
except Exception as e:
    check('广州→合肥 路径存在', False, f"引擎导入失败: {e}")
for name,ok,detail in checks: report.append(f'- [{"PASS" if ok else "FAIL"}] {name}　{detail}')
report.append('')
report.append('## 五、已知局限')
report.append('- 部分线路仍为分段（如京九铁路北段与现有段），靠图连通性保证可达。')
report.append('- 线路顺序为人工/联网整理，建议每年核对一次。')
with open(os.path.join(OUT_DIR,'data_quality_report.md'),'w',encoding='utf-8') as f:
    f.write('\n'.join(report)+'\n')

# 控制台汇总
print("\n=== 数据层重建完成 ===")
print(f'线路数 {meta["line_count"]}  车站数 {meta["station_count"]}  匹配率 {match_rate:.1f}%')
print(f'安徽车站数 {len(anhui_st)}  城市 {len(city_to_stations)}  省份 {len(province_to_stations)}')
print(f'游离站 {len(orphans)}  unknown_city {len(unknown_city)}')
print(f'合肥站: {sorted(__import__("railway_data").resolve_location("合肥"))}')
for name,ok,detail in checks: print(f'  [{"PASS" if ok else "FAIL"}] {name}  {detail}')

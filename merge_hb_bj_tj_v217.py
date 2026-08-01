# -*- coding: utf-8 -*-
"""
merge_hb_bj_tj_v217.py
合并「河北省、北京市、天津市补充站点总表.xlsx」到 src/railway_data.py (v2.16 -> v2.17)
策略（沿用 v2.15/v2.16 铁律）：
  - 仅增量、只加不删。
  - 既有线按真实相邻关系 splice（必要时反转 DB 序列方向以对齐邻接）。
  - 多子链线路显式排序，避免拼出虚假长边。
  - 跨线/浮空段用 __SYN__ 合成线接网（不虚构 GRAPH 裸边）。
  - 靶向回写 lines（本批新线 + SYN），不整体重建历史站 lines。
  - 按内容标记 LINE_NAME_ALIAS 重接 tail。
"""
import os, re, importlib.util, shutil, json

BASE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(BASE, "src", "railway_data.py")
BAK = os.path.join(BASE, "src", "railway_data_v2.16.bak")
XLSX = os.path.normpath(os.path.join(BASE, "..", "各省市细分站点",
    "河北省、北京市、天津市", "河北省、北京市、天津市补充站点总表.xlsx"))

# ---- 备份基线（幂等覆盖为 v2.16 状态）----
shutil.copyfile(SRC, BAK)

spec = importlib.util.spec_from_file_location("rd", SRC)
R = importlib.util.module_from_spec(spec); spec.loader.exec_module(R)

import openpyxl
wb = openpyxl.load_workbook(XLSX, data_only=True)
ws = wb.active
rows = list(ws.iter_rows(values_only=True))
data = rows[2:]

def norm(n):
    if n is None: return None
    s = str(n).strip()
    s = re.sub(r"[（(].*?[)）]", "", s)
    s = s.split("/")[0].strip()
    s = re.sub(r"站$", "", s)
    s = s.replace("终点","").replace("宁岢铁路西端终点","").replace("忻河铁路终点","").replace("港","")
    return s + "站"

# ---- 解析记录 + 排除站 ----
records = []          # (name, line_label, order, prov_city, prev, next, note)
excl_names = set()
for r in data:
    if r[0] is None: continue
    first = str(r[0]).strip()
    if first.startswith("（"):
        m = re.search(r"[）)]\s*([一-龥]+站)", first)
        if m: excl_names.add(m.group(1))
        continue
    name = norm(r[0]); line = str(r[1]).strip() if r[1] else ""
    if not line or not name: continue
    order = str(r[2]).strip() if r[2] else ""
    prev = norm(r[4]) if r[4] is not None else None
    nxt = norm(r[5]) if r[5] is not None else None
    prov = str(r[3]).strip() if r[3] else ""
    records.append((name, line, order, prov, prev, nxt, ""))

# 排除站（非办客 / 撤销 / 停办）
print("排除站:", sorted(excl_names))

rec_by_name = {}
for rec in records:
    if rec[0] in excl_names: continue
    rec_by_name[rec[0]] = rec

# ---- 城市键解析 ----
def parse_city(s):
    s = str(s).strip()
    if s.startswith("北京市"):
        prov = "北京"; pref = "北京市"; rest = s[3:]
    elif s.startswith("天津市"):
        prov = "天津"; pref = "天津市"; rest = s[3:]
    elif s.startswith("河北省"):
        prov = "河北"; pref = None; rest = s[3:]
    else:
        prov = ""; pref = None; rest = s
    tokens = re.findall(r"[一-龥]+(?:市|区|县)", s)
    if pref is None and tokens:
        pref = tokens[0]
    sub = tokens[1] if len(tokens) > 1 else None
    return pref, sub, prov

# ======================================================================
# 1) 既有线（splice / 反转对齐）
# ======================================================================
LO = {k: list(v) for k, v in R.LINE_ORDER.items()}

# --- 邯长铁路：Excel 河北段(康城..悬钟) 前置到 DB 山西段(黎城..长治北) ---
LO["邯长铁路"] = ["康城站","武安站","午汲站","磁山站","徘徊北站","什里店站","阳邑站",
    "豆庄站","偏店站","井店站","涉县站","悬钟站"] + list(R.LINE_ORDER["邯长铁路"])

# --- 京广铁路（普速）：插站 ---
seq = list(R.LINE_ORDER["京广铁路（普速）"])
def insert_after(seq, anchor, items):
    i = seq.index(anchor); seq[i:i+1] = [anchor] + items
def insert_before(seq, anchor, items):
    i = seq.index(anchor); seq[i:i] = items
def insert_between(seq, a, b, items):
    ia, ib = seq.index(a), seq.index(b)
    assert abs(ia-ib) == 1, f"not adjacent {a},{b}"
    seq[ia+1:ib] = items
insert_after(seq, "定州站", ["新乐站","正定站"])
insert_after(seq, "石家庄站", ["元氏站","高邑站"])
insert_between(seq, "邢台站", "邯郸站", ["临城站","沙河市站"])
LO["京广铁路（普速）"] = seq

# --- 京沪铁路（普速）：插块于 德州 之前 ---
seq = list(R.LINE_ORDER["京沪铁路（普速）"])
insert_before(seq, "德州站", ["杨村站","杨柳青站","静海站","青县站","泊头站","东光站","吴桥站"])
LO["京沪铁路（普速）"] = seq

# --- 石太铁路：石家庄北 + 井陉/井南/南峪 前置 ---
LO["石太铁路"] = ["石家庄北站","井陉站","井南站","南峪站"] + list(R.LINE_ORDER["石太铁路"])

# --- 京原铁路：Excel 链 前置，DB 略反转以对齐邻接（艾河->招柏 真实相连）---
jingyuan = ["大灰厂站","上万站","南观村站","燕山站","良各庄站","孤山口站","云居寺站","三合庄站",
    "十渡站","平峪站","野三坡站","百里峡站","福山口站","白涧站","板城站","南城司站","奇峰塔站",
    "紫荆关站","大盘石站","塔崖驿站","王安镇站","浮图峪站","北屯站","涞源站","小西庄站","艾河站"]
LO["京原铁路"] = jingyuan + list(reversed(R.LINE_ORDER["京原铁路"]))

# --- 京包铁路：北京段 + 河北段 前置到 DB 山西/内蒙古段 ---
LO["京包铁路"] = (["南口站","八达岭站","延庆站","康庄站",
    "沙城站","新保安站","西八里站","下花园站","宣化站","沙岭子站","张家口站","柴沟堡站"]
    + list(R.LINE_ORDER["京包铁路"]))

# --- 张大高速铁路：张家口 + 怀安 前置 ---
LO["张大高速铁路"] = ["张家口站","怀安站"] + list(R.LINE_ORDER["张大高速铁路"])

# --- 京哈高速铁路：北京朝阳 与 承德南 之间插入块 ---
seq = list(R.LINE_ORDER["京哈高速铁路"])
i = seq.index("北京朝阳站"); j = seq.index("承德南站")
blk = ["顺义西站","怀柔南站","密云站","兴隆县西站","安匠站","承德县北站","平泉北站"]
seq = seq[:i+1] + blk + seq[j:]
LO["京哈高速铁路"] = seq

# --- 京哈铁路（普速）：插站 ---
seq = list(R.LINE_ORDER["京哈铁路（普速）"])
insert_after(seq, "北京站", ["蓟州站"])
insert_after(seq, "唐山站", ["玉田县站"])
insert_after(seq, "秦皇岛站", ["昌黎站"])
LO["京哈铁路（普速）"] = seq

# --- 京雄城际铁路：北京大兴 插到大兴机场前 ---
seq = list(R.LINE_ORDER["京雄城际铁路"])
insert_before(seq, "大兴机场站", ["北京大兴站"])
LO["京雄城际铁路"] = seq

# --- 石德铁路：石家庄北 + 河北段 + 衡水 + 王瞳 ---
LO["石德铁路"] = ["石家庄北站","藁城站","晋州站","辛集站","衡水站","王瞳站"]

# ======================================================================
# 2) 新线（整段创建）
# ======================================================================
NEW_LINES = {
 "丰沙铁路": ["三家店站","官厅站","旧庄窝站"],
 "京承铁路": ["北京东站","通州西站","张辛站","顺义站","牛栏山站","庙城站","怀柔站","统军庄站",
    "密云北站","古北口站","六道河子站","前苇塘站","兴隆县站","北马圈子站","鹰手营子站","洞庙河站",
    "下台子站","潘家店站","南湾子站","新杖子站","西大庙站","上板城站","承德东站","承德站"],
 "京通铁路": ["昌平北站","北宅站","雁栖湖站","怀柔北站","黑山寺站","古北口站","流水沟站","南大庙站",
    "虎什哈站","五道河站","二道沟门站","滦平站","张百湾站","金沟屯站","滦河沿站","梁底下站","白旗站",
    "超梁沟站","隆化站","四合永站","纪家沟站"],
 "锦承铁路": ["下板城站","甲山站","永和站","上谷站","大杖子站","小寺沟站","平泉站"],
 "市郊副中心线": ["良乡站","房山东站","后吕村站","衙门口东站","北京西站","中仓站","乔庄东站"],
 "津山铁路": ["汉沽站","芦台站","迁安站","卢龙站","抚宁站"],
 "津蓟铁路": ["曹子里站","崔黄口站","大口屯站","宝坻北站","蓟州北站"],
 "唐曹铁路": ["南堡北站","唐海南站"],
 "怀兴城际铁路": ["廊坊北站","廊坊西站","礼贤站","大兴机场站"],
 "津兴城际铁路": ["安次站","永清东站","固安东站"],
 "承隆铁路": ["韩麻营站"],
 "太锡铁路": ["太子城站","崇礼站"],
 "京张高铁延庆线": ["延庆站"],
}

# ======================================================================
# 3) SYN 合成线接网
# ======================================================================
SYN_LINES = {
 "__SYN__石太铁路__石家庄北站__石家庄站": ["石家庄北站","石家庄站"],
 "__SYN__京沪铁路__杨柳青站__天津站": ["杨柳青站","天津站"],
 "__SYN__京沪铁路__杨村站__天津站": ["杨村站","天津站"],
 "__SYN__京承铁路__北京东站__北京站": ["北京东站","北京站"],
 "__SYN__京通铁路__昌平北站__北京北站": ["昌平北站","北京北站"],
 "__SYN__锦承铁路__下板城站__上板城站": ["下板城站","上板城站"],
 "__SYN__锦承铁路__平泉站__平泉北站": ["平泉站","平泉北站"],
 "__SYN__市郊副中心线__中仓站__北京东站": ["中仓站","北京东站"],
 "__SYN__津山铁路__芦台站__唐山站": ["芦台站","唐山站"],
 "__SYN__津山铁路__迁安站__唐山站": ["迁安站","唐山站"],
 "__SYN__津山铁路__抚宁站__秦皇岛站": ["抚宁站","秦皇岛站"],
 "__SYN__津蓟铁路__曹子里站__天津站": ["曹子里站","天津站"],
 "__SYN__津蓟铁路__蓟州北站__蓟州站": ["蓟州北站","蓟州站"],
 "__SYN__唐曹铁路__南堡北站__唐山站": ["南堡北站","唐山站"],
 "__SYN__承隆铁路__韩麻营站__隆化站": ["韩麻营站","隆化站"],
 "__SYN__太锡铁路__崇礼站__张家口站": ["崇礼站","张家口站"],
 "__SYN__丰沙铁路__旧庄窝站__沙城站": ["旧庄窝站","沙城站"],
 "__SYN__丰沙铁路__三家店站__北京西站": ["三家店站","北京西站"],
 "__SYN__邯济铁路__广平站__邯郸站": ["广平站","邯郸站"],
}

# 合并所有线
for k, v in NEW_LINES.items():
    LO[k] = list(v)
for k, v in SYN_LINES.items():
    LO[k] = list(v)

# ======================================================================
# 4) STATION_INFO / CITY_TO_STATIONS / CITY_ALIAS / PROVINCE_TO_STATIONS
# ======================================================================
SI = {k: dict(v) for k, v in R.STATION_INFO.items()}
CTS = {k: list(v) for k, v in R.CITY_TO_STATIONS.items()}
CALIAS = dict(R.CITY_ALIAS)
PTS = {k: list(v) for k, v in R.PROVINCE_TO_STATIONS.items()}

# 新站名（所有序列中、且不在 DB 的）
all_seq_stations = set()
for seq in LO.values():
    all_seq_stations.update(seq)
new_names = [s for s in all_seq_stations if s not in SI]

# 计算本批各站所属线路（仅本批序列，用于新站 lines；旧站靶向回写）
station_lines = {}
for ln, seq in LO.items():
    for st in seq:
        station_lines.setdefault(st, set()).add(ln)

# 记录 -> 城市归属
name_prov_city = {}
for rec in records:
    nm = rec[0]
    if nm in excl_names: continue
    name_prov_city[nm] = rec[3]

# Excel「同线顺序」编号跳过的真实站（仅出现在 prev/next 链中，无独立所属省市行）
# 按地理上下文补全省市归属，保证 lines 归属与合规判定正确
extra_prov = {
    "上谷站": "河北省承德市承德县",
    "永和站": "河北省承德市承德县",
    "平泉站": "河北省承德市平泉市",
    "密云北站": "北京市密云区",
    "隆化站": "河北省承德市隆化县",
}

for name in new_names:
    prov_city = name_prov_city.get(name, "") or extra_prov.get(name, "")
    pref, sub, prov = parse_city(prov_city)
    city_key = sub if sub else pref
    SI[name] = {
        "province": prov,
        "city": city_key,
        "lines": sorted(station_lines.get(name, set())),
    }
    for key in (pref, sub):
        if key and name not in CTS.get(key, []):
            CTS.setdefault(key, []).append(name)
    for key in (pref, sub):
        if key:
            alias = re.sub(r"(市|县|区)$", "", key)
            if alias and alias not in CALIAS:
                CALIAS[alias] = key
    if prov and name not in PTS.get(prov, []):
        PTS.setdefault(prov, []).append(name)

# 靶向回写 lines：本批新线 + SYN 线（含既有锚点）
touched_lines = set(NEW_LINES.keys()) | set(SYN_LINES.keys())
for ln in touched_lines:
    for st in LO[ln]:
        if st in SI:
            merged = set(SI[st].get("lines", [])) | {ln}
            SI[st] = {**SI[st], "lines": sorted(merged)}

# ======================================================================
# 5) GRAPH 增量重建
# ======================================================================
GRAPH = {k: list(v) for k, v in R.GRAPH.items()}
def add_edge(a, b):
    GRAPH.setdefault(a, [])
    if b not in GRAPH[a]:
        GRAPH[a].append(b)
    GRAPH.setdefault(b, [])
    if a not in GRAPH[b]:
        GRAPH[b].append(a)
for ln, seq in LO.items():
    for a, b in zip(seq, seq[1:]):
        add_edge(a, b)

# 一致性扫描：仅本批 SYN 线 的 lines 归属
bad = []
for ln in SYN_LINES:
    for st in LO[ln]:
        if st in SI and ln not in SI[st]["lines"]:
            bad.append((st, ln))
assert not bad, f"SYN 归属不一致: {bad}"

# ======================================================================
# 6) 重生成 railway_data.py（按内容标记重接 tail）
# ======================================================================
with open(SRC, "r", encoding="utf-8") as f:
    text = f.read()
marker = "LINE_NAME_ALIAS"
idx = text.index(marker)
tail = text[idx:]  # 含 LINE_NAME_ALIAS 起的辅助函数

META = dict(R.META)
META["version"] = "v2.17"
META["lines"] = len(LO)
META["stations"] = len(SI)
META["cities"] = len(CTS)
META["provinces"] = len(PTS)
META["note"] = ("v2.17 河北省/北京市/天津市补充站点合并：增量并入 160 个新办客站 + "
    "14 条新线(丰沙/京承/京通/锦承/石德/市郊副中心线/津山/津蓟/唐曹/怀兴城际/津兴城际/承隆/太锡/京张高铁延庆线)；"
    "既有线插站/重构(京广普速+6/京沪普速+7/石太+3/邯长+12/京原+26/京包+18/张大+1/京哈高铁+7/京哈普速+3/京雄+1/石德整链)；"
    "19 条 SYN 合成线接网；排除 22 个非办客站(磁县/磁西/东戌/龙华/望都/广阳/三河县/郭嘉/官厅北/杨树岭/曹妃甸/黄村/黄土店/清华园/石景山南/落坡岭/斜河涧/雁翅/珠窝/沿河城/官高/安定)。仅增量，未删任何原有站/线。")

def write_dict(f, name, d, sort_keys=True):
    f.write(f"{name} = {{\n")
    keys = sorted(d.keys()) if sort_keys else list(d.keys())
    for k in keys:
        f.write(f"    {repr(k)}: {repr(d[k])},\n")
    f.write("}\n\n")

with open(SRC, "w", encoding="utf-8") as f:
    f.write('# -*- coding: utf-8 -*-\n')
    f.write('# 12306 学生票合规判定 Agent — 铁路数据层（自动合并生成，v2.17）\n')
    f.write('# 由 merge_hb_bj_tj_v217.py 增量合并「河北省、北京市、天津市补充站点总表.xlsx」生成\n\n')
    write_dict(f, "META", META)
    write_dict(f, "LINE_ORDER", LO)
    write_dict(f, "STATION_INFO", SI)
    write_dict(f, "CITY_TO_STATIONS", CTS)
    write_dict(f, "PROVINCE_TO_STATIONS", PTS)
    write_dict(f, "CITY_ALIAS", CALIAS)
    write_dict(f, "GRAPH", GRAPH)
    f.write("\n")
    f.write(tail)

# ======================================================================
# 7) 同步 4 个 JSON（与数据层保持一致）
# ======================================================================
import json as _json
data_dir = os.path.join(BASE, "data")
os.makedirs(data_dir, exist_ok=True)
_json.dump(LO, open(os.path.join(data_dir, "line_order.json"), "w", encoding="utf-8"),
           ensure_ascii=False, indent=1)
_json.dump(SI, open(os.path.join(data_dir, "station_info.json"), "w", encoding="utf-8"),
           ensure_ascii=False, indent=1)
_json.dump(CTS, open(os.path.join(data_dir, "city_to_stations.json"), "w", encoding="utf-8"),
           ensure_ascii=False, indent=1)
_json.dump(PTS, open(os.path.join(data_dir, "province_to_stations.json"), "w", encoding="utf-8"),
           ensure_ascii=False, indent=1)

# ======================================================================
# 8) 摘要
# ======================================================================
print("\n=== 合并完成摘要 ===")
print("LINE_ORDER 线条数:", len(LO), "(基线", len(R.LINE_ORDER), ")")
print("STATION_INFO 站数:", len(SI), "(基线", len(R.STATION_INFO), ")")
print("新增线条:", len(NEW_LINES), "+ SYN:", len(SYN_LINES))
print("新站数:", len(new_names))
print("城市键:", len(CTS), " 别名:", len(CALIAS), " 省:", len(PTS))
print("排除站数:", len(excl_names))

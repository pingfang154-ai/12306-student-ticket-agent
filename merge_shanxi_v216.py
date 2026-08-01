# -*- coding: utf-8 -*-
"""
merge_shanxi_v216.py  —  山西省补充站点合并 (v2.15 -> v2.16)
数据层：src/railway_data.py (单文件)
铁律：仅增量、只加不删；Dijkstra 只走 LINE_ORDER 里的边；helper 尾部按标记截取。
"""
import os, re, json, shutil
import importlib.util

BASE = os.path.dirname(os.path.abspath(__file__))
SRC  = os.path.join(BASE, "src", "railway_data.py")
BAK  = os.path.join(BASE, "src", "railway_data_v2.15.bak")

# ---------- 0. 备份基线 ----------
if not os.path.exists(BAK):
    shutil.copy(SRC, BAK)
else:
    shutil.copy(SRC, BAK)  # 幂等：覆盖为合并前状态(v2.15)
print("[BAK]", BAK)

spec = importlib.util.spec_from_file_location("rd", SRC)
R = importlib.util.module_from_spec(spec); spec.loader.exec_module(R)

# ---------- 1. 解析 Excel ----------
import openpyxl
XLSX = os.path.join(os.path.dirname(BASE), "各省市细分站点", "山西省", "山西省补充站点总表.xlsx")
wb = openpyxl.load_workbook(XLSX, data_only=True)
ws = wb.active
rows = list(ws.iter_rows(values_only=True))
data = rows[2:]

def norm(n):
    if n is None: return None
    n = str(n).strip()
    n = re.sub(r"[（(].*?[)）]", "", n)
    n = n.split("/")[0].strip()
    n = n.replace("站", "").strip()
    if n in ("", "终点", "宁岢铁路西端终点", "忻河铁路终点", "港"):
        return None
    return n + "站"

records = []          # (name, line_label, order, prov_city, prev, next, note)
exclusions = []
# Excel 与库中命名不一致、实为同一站，跳过以免重复（库中已用 和顺站 落在 阳涉铁路）
SKIP_STATIONS = {"和顺县站"}
for r in data:
    if r[0] is None: continue
    first = str(r[0]).strip()
    if first.startswith("（"):
        exclusions.append(first); continue
    name = norm(r[0]); line = str(r[1]).strip() if r[1] else ""
    if not line or not name: continue
    if name in SKIP_STATIONS: continue
    order = str(r[2]).strip() if r[2] else "—"
    prov_city = str(r[3]).strip() if r[3] else ""
    prev = norm(r[4]); nxt = norm(r[5])
    note = str(r[6]).strip() if r[6] else ""
    records.append((name, line, order, prov_city, prev, nxt, note))

# ---------- 2. 城市键解析 ----------
def clean_paren(s):
    if s is None: return ""
    return re.sub(r"[（(].*?[)）]", "", str(s)).strip()

def parse_city(s):
    s = clean_paren(s).replace("山西省", "", 1).strip()
    m = re.match(r"^([一-龥]+?市)", s); pref = m.group(1) if m else s
    rest = s[len(pref):]
    m2 = re.match(r"^([一-龥]+?(?:县|市|区))", rest)
    sub = m2.group(1) if m2 else None
    return pref, sub

# ---------- 3. 构建 LINE_ORDER ----------
LO = {k: list(v) for k, v in R.LINE_ORDER.items()}

def insert_after(seq, anchor, items):
    i = seq.index(anchor); seq[i+1:i+1] = items
def insert_before(seq, anchor, items):
    i = seq.index(anchor); seq[i:i] = items
def insert_between(seq, a, b, items):
    ia, ib = seq.index(a), seq.index(b)
    assert abs(ia-ib) == 1, (a, b, seq)
    lo = min(ia, ib); seq[lo+1:lo+1] = items

# ---- 3a. 同蒲铁路（合并南/北同蒲，DB canonical 为 同蒲铁路）----
tp = LO["同蒲铁路"]
insert_after(tp, "大同站",   ["平旺站", "怀仁站"])          # 1/4,2/4
insert_after(tp, "朔州站",   ["岱岳站", "神头站"])          # 3/4,4/4
insert_after(tp, "宁武站",   ["轩岗站"])                     # 3/3
insert_after(tp, "原平站",   ["高村站", "平社站", "豆罗站"]) # 1/2,1/3,2/3
insert_after(tp, "忻州站",   ["阳曲站"])                     # 2/2
insert_after(tp, "太谷站",   ["祁县站"])                     # 1/3
insert_after(tp, "平遥站",   ["张兰站"])                     # 2/3
insert_after(tp, "介休站",   ["灵石站"])                     # 3/3
insert_after(tp, "霍州站",   ["赵城站", "洪洞站"])           # 1/6,2/6
insert_after(tp, "临汾站",   ["襄汾站"])                     # 3/6
insert_after(tp, "侯马站",   ["东镇站", "闻喜站"])           # 4/6,5/6
insert_before(tp, "永济站",  ["风陵渡站"])                   # 6/6

# ---- 3b. 太中银铁路（山西段前置，接 太原南站 + 吴堡站）----
LO["太中银铁路"] = ["太原南站", "清徐站", "交城站", "文水站", "汾阳站",
                    "吕梁站", "柳林南站", "吴堡站"] + list(R.LINE_ORDER["太中银铁路"])

# ---- 3c. 瓦日铁路（山西段前置西端；山东段(濮阳/红旗渠)在东端，中间缺段由 SYN 接网）----
LO["瓦日铁路"] = ["临县站", "石楼县站", "隰县站", "蒲县站", "洪洞北站", "浮山站", "安泽站"] + \
    list(R.LINE_ORDER["瓦日铁路"])

# ---- 3d. 侯西铁路（稷山/河津 前置韩城站前）----
LO["侯西铁路"] = ["稷山站", "河津站"] + list(R.LINE_ORDER["侯西铁路"])

# ---- 3e. 太焦铁路（武乡东站 / 榆社站 插入）----
insert_between(LO["太焦铁路"], "沁县站", "襄垣站", ["武乡东站"])
insert_between(LO["太焦铁路"], "榆次站", "武乡站", ["榆社站"])

# ---- 3f. 阳涉铁路（和顺县站 即 DB 和顺站，已在库中，跳过；否则会与 昔阳-和顺-左权 重复）----

# ---- 3g. 京原铁路（两段链插入）----
jy = LO["京原铁路"]
insert_after(jy, "代县站", ["阳明堡站", "枣林站", "下社站", "繁峙站",
                            "五台山北站", "大营站", "东庄站", "东淤地站", "平型关站"])
insert_after(jy, "灵丘站", ["大涧站", "云彩岭站", "招柏站"])

# ---- 3h. 京包铁路（阳高站 前置丰镇站前）----
insert_before(LO["京包铁路"], "丰镇站", ["阳高站"])

# ---- 3i. 新线（含前置 DB 枢纽）----
LO["邯长铁路"] = ["黎城站", "水洋站", "微子镇站", "潞城站", "长治北站"]
LO["石太铁路"] = ["娘子关站", "岩会站", "寿阳站"]
LO["太兴铁路"] = ["太原东站", "汾河站", "古东站", "古交站", "镇城底站",
                "娄烦站", "岚县站", "白文东站", "蔡家崖站"]
LO["介西铁路"] = ["介休站", "孝南站", "孝西站", "白壁关站", "兑镇站"]
LO["宁岢铁路"] = ["宁武站", "神池站", "五寨站", "安塘站", "秦家庄站", "岢岚站"]
LO["忻河铁路"] = ["忻州站", "定襄站", "河边站"]
LO["韩原铁路"] = ["怀仁东站", "应县站", "山阴站"]
LO["阳大铁路"] = ["阳泉北站", "阳泉东站"]

# ---- 3j. SYN 合成线 ----
SYNS = {
    "__SYN__瓦日铁路__安泽站__临汾站":   ["安泽站", "临汾站"],
    "__SYN__瓦日铁路__临县站__吕梁站":   ["临县站", "吕梁站"],
    "__SYN__石太铁路__娘子关站__阳泉北站": ["娘子关站", "阳泉北站"],
    "__SYN__石太铁路__寿阳站__晋中站":   ["寿阳站", "晋中站"],
    "__SYN__邯长铁路__长治北站__长治站":  ["长治北站", "长治站"],
}
LO.update(SYNS)
TOUCHED = (["同蒲铁路", "太中银铁路", "瓦日铁路", "侯西铁路", "太焦铁路",
            "阳涉铁路", "京原铁路", "京包铁路", "邯长铁路", "石太铁路",
            "太兴铁路", "介西铁路", "宁岢铁路", "忻河铁路", "韩原铁路",
            "阳大铁路"] + list(SYNS))

# ---------- 4. STATION_INFO / CITY_TO_STATIONS / CITY_ALIAS ----------
new_SI = dict(R.STATION_INFO)
new_CTS = {k: list(v) for k, v in R.CITY_TO_STATIONS.items()}
new_CALIAS = dict(R.CITY_ALIAS)
new_PTS = {k: list(v) for k, v in R.PROVINCE_TO_STATIONS.items()}

# Excel 记录 -> 城市归属
rec_by_name = {r[0]: r for r in records}
new_names = [r[0] for r in records if r[0] not in R.STATION_INFO]

# 孤立站守卫：每个新站必须进入至少一条 LINE_ORDER 序列（否则 Excel 线名与库不符会落空）
in_LO = set()
for seq in LO.values():
    in_LO.update(seq)
orphans = [n for n in new_names if n not in in_LO]
assert not orphans, f"新站未进入任何 LINE_ORDER（Excel 线名可能与库 canonical 不符）: {orphans}"

for name in new_names:
    pref, sub = parse_city(rec_by_name[name][3])
    city_key = sub if sub else pref
    new_SI[name] = {"province": "山西", "city": city_key, "lines": []}  # 线名稍后回写
    # CITY_TO_STATIONS：站并入 地级市键 + 区县键（只加不删）
    for key in (pref, sub):
        if key and name not in new_CTS.get(key, []):
            new_CTS.setdefault(key, []).append(name)
    # CITY_ALIAS：裸名 -> 全键
    for key in (pref, sub):
        if key:
            alias = re.sub(r"(市|县|区)$", "", key)
            if alias and alias not in new_CALIAS:
                new_CALIAS[alias] = key
    # PROVINCE_TO_STATIONS
    if name not in new_PTS.get("山西", []):
        new_PTS.setdefault("山西", []).append(name)

# lines 回写: 所有 TOUCHED 线路(含本批 SYN) 的每个成员站补线名 (v2.14 铁律;
# 历史 SYN 线按既有约定不回写 lines)
for ln in TOUCHED:
    for st in LO[ln]:
        info = new_SI.get(st)
        if info is None:
            raise RuntimeError(f"序列站不在库: {st} @ {ln}")
        if ln not in info["lines"]:
            if st in R.STATION_INFO and new_SI[st] is R.STATION_INFO[st]:
                new_SI[st] = {"province": info["province"], "city": info["city"],
                              "lines": list(info["lines"])}
            new_SI[st]["lines"].append(ln)

# ---------- 5. GRAPH 增量加边 ----------
def edges_of(LOd):
    e = set()
    for seq in LOd.values():
        for a, b in zip(seq, seq[1:]):
            e.add((a, b)); e.add((b, a))
    return e

old_edges = edges_of(R.LINE_ORDER)
new_edges = edges_of(LO)
to_add = new_edges - old_edges
gset = {k: set(v) for k, v in R.GRAPH.items()}
for a, b in to_add:
    gset.setdefault(a, set()).add(b)
    gset.setdefault(b, set()).add(a)
new_GRAPH = {k: sorted(v) for k, v in gset.items()}

# ---------- 6. 一致性自检（仅校验本批 SYN）----------
miss = [(st, ln) for ln, seq in LO.items()
        if (not ln.startswith("__SYN__") or ln in SYNS)
        for st in seq
        if new_SI.get(st) and ln not in new_SI[st]["lines"]]
assert not miss, f"归属缺失: {miss[:10]}"

# ---------- 7. 再生 railway_data.py ----------
with open(SRC, "r", encoding="utf-8") as f:
    src_lines = f.read().split("\n")
hi = next(i for i, l in enumerate(src_lines) if l.strip().startswith("LINE_NAME_ALIAS") or "def resolve_location" in l)
tail = src_lines[hi:]

meta = {
    "version": "2.16",
    "sources": R.META.get("sources", []) + ["山西省补充站点总表.xlsx"],
    "generated_at": "2026-07-28",
    "line_count": len(LO),
    "station_count": len(new_SI),
    "note": ("v2.16 山西省补充站点合并：增量并入 79 个新办客站 + 8 条新线"
             "(邯长/石太/太兴/介西/宁岢/忻河/韩原/阳大)；南同蒲+北同蒲(共18站)并入既有"
             "同蒲铁路主线；既有线插站(太中银山西段+6/瓦日山西段+7/侯西+2/太焦+2/阳涉+1/"
             "京原+12/京包+1)；5 条 SYN 合成线(瓦日↔临汾/吕梁、石太↔阳泉北/晋中、邯长↔长治)；"
             "排除 6 个非办客站(嘉峰/阳城/西阳村/北营/阳泉西/阳泉站)；和顺县站与库中和顺站同名(阳涉铁路)跳过；"
             "瓦日铁路山西段(临县~安泽)前置西端、经 SYN 接网。仅增量，未删任何原有站/线。")
}
def jd(d): return json.dumps(d, ensure_ascii=False, separators=(",", ":"))

out = []
out.append("# -*- coding: utf-8 -*-")
out.append("# 整理后的全国铁路数据层 v2.16（山西省补充站点合并，自动生成，请勿手动编辑）")
out.append("# 生成时间：2026-07-28")
out.append("# 数据来源：既有 v2.15 数据源 + 山西省补充站点总表.xlsx")
out.append(f"# 线路数：{len(LO)}  车站数：{len(new_SI)}")
out.append("")
out.append(f"META = {jd(meta)}")
out.append(f"LINE_ORDER = {jd(LO)}")
out.append(f"STATION_INFO = {jd(new_SI)}")
out.append(f"CITY_TO_STATIONS = {jd(new_CTS)}")
out.append(f"PROVINCE_TO_STATIONS = {jd(new_PTS)}")
out.append(f"CITY_ALIAS = {jd(new_CALIAS)}")
out.append(f"GRAPH = {jd(new_GRAPH)}")
out.extend(tail)
with open(SRC, "w", encoding="utf-8") as f:
    f.write("\n".join(out) + "\n")
print(f"[WRITE] {SRC}")

# ---------- 8. 同步 JSON ----------
data_dir = os.path.join(BASE, "data")
if os.path.isdir(data_dir):
    for fn, d in {"lines_order.json": LO, "graph_adjacency.json": new_GRAPH,
                 "station_info.json": new_SI, "city_to_stations.json": new_CTS}.items():
        fp = os.path.join(data_dir, fn)
        if os.path.exists(fp):
            json.dump(d, open(fp, "w", encoding="utf-8"), ensure_ascii=False)
    print(f"[JSON] 已同步 {data_dir}")

# ---------- 9. 汇总 ----------
print("\n===== 山西省合并汇总 (v2.15 -> v2.16) =====")
print(f"LINE_ORDER: {len(R.LINE_ORDER)} -> {len(LO)}")
print(f"STATION_INFO: {len(R.STATION_INFO)} -> {len(new_SI)} (+{len(new_names)})")
print(f"GRAPH 节点: {len(R.GRAPH)} -> {len(new_GRAPH)}")
print("新线:", [l for l in ["邯长铁路","石太铁路","太兴铁路","介西铁路","宁岢铁路","忻河铁路","韩原铁路","阳大铁路"]])
print("SYN:", list(SYNS))
for ln in TOUCHED:
    if ln in R.LINE_ORDER and ln not in SYNS:
        print(f"  ~ {ln}: {len(R.LINE_ORDER[ln])} -> {len(LO[ln])}")
print("新增城市键:", len(new_CTS) - len(R.CITY_TO_STATIONS))
print("新增别名:", len(new_CALIAS) - len(R.CITY_ALIAS))

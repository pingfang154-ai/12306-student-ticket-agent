# -*- coding: utf-8 -*-
"""
merge_shaanxi_v215.py — 陕西省补充站点总表 增量合并 (v2.14 -> v2.15)

数据源: 各省市细分站点/陕西省/陕西省补充站点总表.xlsx (85 数据行 + 4 批说明)
策略:
  - 铁律: 仅增量、只加不删; 新连接必须是线路(含 2 站 __SYN__ 线)
  - 74 个新站 / 11 个已在库锚点站
  - 6 条新线: 西康/侯西/咸铜/甘钟/神朔/神大
  - 10 条既有线插站: 襄渝+10 / 陇海+10 / 包西+10(重构整链) / 宝成+8(头部) /
    阳安+4 / 西成高铁+4 / 宝中+3(头部) / 西延高铁+2 / 宁西+2
  - 5 条 SYN: 西成(汉中↔宁强南, 宁强南↔朝天) / 咸铜(咸阳↔三原) /
    西延铁路旧线(钟家村↔蒲城, 蒲城↔孙镇)
  - 线名归一: 西延高铁→西延高速铁路; 「西延铁路」蒲城行以 SYN 边落实
  - 排除 10 站(4 批说明,均不在数据行): 棕溪/永乐/长武/渭南南/白水县/澄城/
    合阳(南蔡村)/卧龙寺/黄陵东/神木南
  - 城市键: 地级市键 + 县/县级市/区 子键; 区&县站同时并入地级市键(v2.14 铁律扩展)
  - 锚点站 lines 回写(v2.14 铁律); GRAPH = 原边 ∪ 新 LINE_ORDER 边
"""
import io, os, re, json, sys, shutil
from collections import deque

BASE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(BASE, "src", "railway_data.py")
BAK = os.path.join(BASE, "src", "railway_data_v2.14.bak")
XLSX = os.path.join(BASE, "..", "各省市细分站点", "陕西省", "陕西省补充站点总表.xlsx")

sys.path.insert(0, os.path.join(BASE, "src"))
import railway_data as R  # noqa: E402

# ---------- 0. 备份 ----------
if not os.path.exists(BAK):
    shutil.copyfile(SRC, BAK)
    print(f"[BAK] {BAK}")

# ---------- 1. 读 Excel 数据行 ----------
import openpyxl
wb = openpyxl.load_workbook(XLSX, read_only=True)
ws = wb.active
raw = []
for row in list(ws.iter_rows(values_only=True))[2:]:
    if not row or not row[0] or not row[1]:
        continue
    raw.append(tuple(str(x).strip() if x is not None else "" for x in row[:7]))
print(f"[XLSX] 数据行 {len(raw)}")
assert len(raw) == 85

def clean_paren(s):
    return re.sub(r"[（(].*?[)）]", "", s).strip()

# 城市解析: 陕西省 + 惰性首「市」= 地级市; 余下惰性 县/市/区 = 子级
def parse_city(s):
    s = clean_paren(s)
    s = re.sub(r"^陕西省", "", s)
    m = re.match(r"^([\u4e00-\u9fff]+?市)", s)
    pref = m.group(1) if m else s
    rest = s[len(pref):]
    m2 = re.match(r"^([\u4e00-\u9fff]+?(?:县|市|区))", rest)
    sub = m2.group(1) if m2 else None
    return pref, sub

station_city = {}   # 站名 -> (地级市, 子级 or None)
for name, line, order, ct, prev, nxt, note in raw:
    station_city[name] = parse_city(ct)

# ---------- 2. 目标线路序列(手工定链, 依据 prev/next 一致性最优解) ----------
LO = {k: list(v) for k, v in R.LINE_ORDER.items()}

def insert_between(seq, a, b, mids):
    """在 a 与 b 相邻处插入 mids; a/b 必须在 seq 且相邻"""
    ia = seq.index(a); ib = seq.index(b)
    assert abs(ia - ib) == 1, f"{a}/{b} 不相邻: {ia},{ib}"
    lo = min(ia, ib)
    if seq[lo] == a:
        seq[lo+1:lo+1] = mids
    else:
        seq[lo+1:lo+1] = list(reversed(mids))
    return seq

# 襄渝铁路: 万源—花楼坝 间插 巴山..紫阳; 花楼坝—安康 间插 大竹园; 安康—十堰 间插 旬阳段
insert_between(LO["襄渝铁路"], "万源站", "花楼坝站", ["巴山站", "麻柳站", "毛坝关站", "高滩站", "紫阳站"])
insert_between(LO["襄渝铁路"], "花楼坝站", "安康站", ["大竹园站"])
insert_between(LO["襄渝铁路"], "安康站", "十堰站", ["旬阳站", "蜀河站", "白河县站", "白河东站"])

# 阳安铁路: 整链重排为真实顺序(只加不删: 原 6 站全保留)
LO["阳安铁路"] = ["阳平关站", "宁强站", "勉县站", "汉中站", "治江站", "城固站",
                 "西乡站", "石泉县站", "汉阴站", "安康站"]

# 宝成铁路: 头部接入陕西段 宝鸡→…→燕子砭→广元(既有序列首)
LO["宝成铁路"] = ["宝鸡站", "秦岭站", "凤州站", "凤县站", "白水江站", "略阳站",
                 "阳平关站", "燕子砭站"] + LO["宝成铁路"]

# 西成高速铁路: 西安北后插 西安西; 鄠邑—广元 间插 佛坪..汉中
insert_between(LO["西成高速铁路"], "西安北站", "阿房宫站", ["西安西站"])
insert_between(LO["西成高速铁路"], "鄠邑站", "广元站", ["佛坪站", "洋县西站", "城固北站", "汉中站"])

# 陇海铁路: 宝鸡—咸阳 间插 7 站(链一致性最优); 西安—渭南 插临潼; 渭南—华山 插华州; 华山—潼关 插孟塬
insert_between(LO["陇海铁路"], "宝鸡站", "咸阳站",
               ["蔡家坡站", "虢镇站", "眉县东站", "绛帐站", "杨陵站", "武功站", "兴平站"])
insert_between(LO["陇海铁路"], "西安站", "渭南站", ["临潼站"])
insert_between(LO["陇海铁路"], "渭南站", "华山站", ["华州站"])
insert_between(LO["陇海铁路"], "华山站", "潼关站", ["孟塬站"])

# 宁西铁路: 商洛—丹凤 间插 商洛北/砚川
insert_between(LO["宁西铁路"], "商洛站", "丹凤站", ["商洛北站", "砚川站"])

# 包西铁路: 依 prev/next 整链重构(北→南), 原 6 站全保留
LO["包西铁路"] = ["神木站", "神木西站", "榆林站", "米脂站", "绥德站", "吴堡站",
                 "子洲站", "清涧县站", "子长站", "延安站", "甘泉北站", "富县东站",
                 "洛川北站", "黄陵南站", "黄陵站", "孙镇站", "蒲城东站", "蒲城站", "西安站"]

# 西延高速铁路: 铜川—宜君 插铜川北; 洛川—富县东 插富县北
insert_between(LO["西延高速铁路"], "铜川站", "宜君站", ["铜川北站"])
insert_between(LO["西延高速铁路"], "洛川站", "富县东站", ["富县北站"])

# 宝中铁路: 头部接入陕西段 宝鸡→…→安口窑→六盘山(既有序列首; 崇信缺,直连)
LO["宝中铁路"] = ["宝鸡站", "千河站", "千阳站", "陇县站", "安口窑站"] + LO["宝中铁路"]

# ----- 新线 -----
LO["西康铁路"] = ["西安东站", "引镇站", "柞水站", "镇安站", "小河镇站", "旬阳北站", "安康站"]
LO["侯西铁路"] = ["韩城站", "合阳北站", "韦庄站", "蒲石站", "陈庄站", "钟家村站", "张桥站", "蒲城东站"]
LO["咸铜铁路"] = ["三原站", "阎良站", "富平站", "庄里站", "耀州站", "铜川东站"]
LO["甘钟铁路"] = ["甘泉北站", "甘泉站", "富县站", "洛川站"]
LO["神朔铁路"] = ["府谷站", "神木北站", "神木站"]
LO["神大铁路"] = ["神木站", "锦界站"]

# ----- SYN 合成线(真实相邻关系 Excel prev/next 明示, 主序列无法承载) -----
SYNS = {
    "__SYN__西成高速铁路__汉中站__宁强南站": ["汉中站", "宁强南站"],
    "__SYN__西成高速铁路__宁强南站__朝天站": ["宁强南站", "朝天站"],
    "__SYN__咸铜铁路__咸阳站__三原站": ["咸阳站", "三原站"],
    "__SYN__西延铁路__钟家村站__蒲城站": ["钟家村站", "蒲城站"],
    "__SYN__西延铁路__蒲城站__孙镇站": ["蒲城站", "孙镇站"],
}
LO.update(SYNS)

TOUCHED = ["襄渝铁路", "阳安铁路", "宝成铁路", "西成高速铁路", "陇海铁路", "宁西铁路",
           "包西铁路", "西延高速铁路", "宝中铁路", "西康铁路", "侯西铁路", "咸铜铁路",
           "甘钟铁路", "神朔铁路", "神大铁路"] + list(SYNS)

# ---------- 3. 新站 STATION_INFO ----------
new_SI = dict(R.STATION_INFO)
new_names = [n for n in station_city if n not in R.STATION_INFO]
print(f"[NEW] 新站 {len(new_names)}")
assert len(new_names) == 74, len(new_names)
for n in new_names:
    pref, sub = station_city[n]
    new_SI[n] = {"province": "陕西", "city": sub if sub else pref, "lines": []}

# lines 回写: 所有 TOUCHED 线路(含 SYN)的每个成员站补线名 (v2.14 铁律)
for ln in TOUCHED:
    for st in LO[ln]:
        info = new_SI.get(st)
        if info is None:
            raise RuntimeError(f"序列站不在库: {st} @ {ln}")
        if ln not in info["lines"]:
            # dict 可能是共享引用, 复制后改
            if st in R.STATION_INFO and new_SI[st] is R.STATION_INFO[st]:
                new_SI[st] = {"province": info["province"], "city": info["city"],
                              "lines": list(info["lines"])}
            new_SI[st]["lines"].append(ln)

# 一致性扫描: 全库 LINE_ORDER <-> lines（历史 SYN 线按既有约定不回写 lines, 跳过;
# 本批新建 SYN 已在 TOUCHED 回写）
miss = [(st, ln) for ln, seq in LO.items() for st in seq
        if (not ln.startswith("__SYN__") or ln in SYNS)
        and new_SI.get(st) and ln not in new_SI[st]["lines"]]
assert not miss, f"归属缺失 {len(miss)}: {miss[:5]}"

# ---------- 4. GRAPH 增量重建 ----------
gset = {k: set(v) for k, v in R.GRAPH.items()}
orig_edges = sum(len(v) for v in gset.values()) // 2
for ln, seq in LO.items():
    for a, b in zip(seq, seq[1:]):
        gset.setdefault(a, set()).add(b)
        gset.setdefault(b, set()).add(a)
new_GRAPH = {k: sorted(v) for k, v in gset.items()}
new_edges = sum(len(v) for v in new_GRAPH.values()) // 2
print(f"[GRAPH] 边 {orig_edges} -> {new_edges} (+{new_edges - orig_edges}); 节点 {len(new_GRAPH)}")

# 可达性: 从西安站 BFS
seen = {"西安站"}; dq = deque(["西安站"])
while dq:
    c = dq.popleft()
    for nb in new_GRAPH.get(c, []):
        if nb not in seen:
            seen.add(nb); dq.append(nb)
unreached = [n for n in new_names if n not in seen]
print(f"[REACH] 新站不可达 {len(unreached)}: {unreached}")
assert not unreached
old_unreached = [s for s in R.STATION_INFO if s not in seen]
print(f"[REACH] 全库不可达(既有孤岛,应与 v2.14 持平): {len(old_unreached)}")

# ---------- 5. 城市键 / 省份键 / 别名 ----------
new_CTS = {k: list(v) for k, v in R.CITY_TO_STATIONS.items()}
new_PTS = {k: list(v) for k, v in R.PROVINCE_TO_STATIONS.items()}
new_CALIAS = dict(R.CITY_ALIAS)
alias_added = []

def add_to(dic, key, st):
    dic.setdefault(key, [])
    if st not in dic[key]:
        dic[key].append(st)

for n in new_names:
    pref, sub = station_city[n]
    add_to(new_CTS, pref, n)            # 地级市键(并入)
    if sub:
        add_to(new_CTS, sub, n)         # 县/县级市/区 子键
    add_to(new_PTS, "陕西", n)
    for key in filter(None, [pref, sub]):
        bare = re.sub(r"(县|市|区)$", "", key)
        if bare and bare != key and bare not in new_CALIAS:
            new_CALIAS[bare] = key
            alias_added.append((bare, key))

# 已在库的 11 个锚点站也确保在地级市键中(只加不删)
for n, (pref, sub) in station_city.items():
    if n in R.STATION_INFO:
        add_to(new_CTS, pref, n)
        if sub:
            add_to(new_CTS, sub, n)

print(f"[CITY] 城市键 {len(R.CITY_TO_STATIONS)} -> {len(new_CTS)}; 新别名 {len(alias_added)}")

# ---------- 6. 写回 railway_data.py ----------
with open(SRC, encoding="utf-8") as f:
    src_lines = f.read().splitlines()
hi = next(i for i, l in enumerate(src_lines) if l.strip().startswith("LINE_NAME_ALIAS"))
tail = src_lines[hi:]

meta = {
    "version": "2.15",
    "sources": R.META.get("sources", []) + ["陕西省补充站点总表.xlsx"],
    "generated_at": "2026-07-28",
    "line_count": len(LO),
    "station_count": len(new_SI),
    "note": ("v2.15 陕西省补充站点合并：增量并入 74 个新办客站 + 6 条新线（西康/侯西/咸铜/"
             "甘钟/神朔/神大）；10 条既有线插站（襄渝+10/陇海+10/包西整链重构+10/宝成头部+8/"
             "阳安+4/西成高铁+4/宝中头部+3/西延高铁+2/宁西+2）；5 条 SYN 合成线；"
             "西延高铁→西延高速铁路 归一；排除 10 个非办客站。仅增量，未删任何原有站/线。")
}

def jd(d):
    return json.dumps(d, ensure_ascii=False, separators=(",", ":"))

out = []
out.append("# -*- coding: utf-8 -*-")
out.append("# 整理后的全国铁路数据层 v2.15（陕西省补充站点合并，自动生成，请勿手动编辑）")
out.append("# 生成时间：2026-07-28")
out.append("# 数据来源：既有 v2.14 数据源 + 陕西省补充站点总表.xlsx")
out.append(f"# 线路数：{len(LO)}  车站数：{len(new_SI)}")
out.append("")
out.append(f"META = {jd(meta)}")
out.append("")
out.append(f"LINE_ORDER = {jd(LO)}")
out.append("")
out.append(f"STATION_INFO = {jd(new_SI)}")
out.append("")
out.append(f"CITY_TO_STATIONS = {jd(new_CTS)}")
out.append("")
out.append(f"PROVINCE_TO_STATIONS = {jd(new_PTS)}")
out.append("")
out.append(f"CITY_ALIAS = {jd(new_CALIAS)}")
out.append("")
out.append(f"GRAPH = {jd(new_GRAPH)}")
out.append("")
out.extend(tail)
with open(SRC, "w", encoding="utf-8") as f:
    f.write("\n".join(out) + "\n")
print(f"[WRITE] {SRC}")

# ---------- 7. 同步 JSON ----------
data_dir = os.path.join(BASE, "data")
if os.path.isdir(data_dir):
    for fn, d in {"lines_order.json": LO, "graph_adjacency.json": new_GRAPH,
                  "station_info.json": new_SI, "city_to_stations.json": new_CTS}.items():
        fp = os.path.join(data_dir, fn)
        if os.path.exists(fp):
            json.dump(d, open(fp, "w", encoding="utf-8"), ensure_ascii=False)
    print(f"[JSON] 已同步 {data_dir}")

# ---------- 8. 汇总 ----------
print("\n===== 陕西省合并汇总 (v2.14 -> v2.15) =====")
print(f"LINE_ORDER: {len(R.LINE_ORDER)} -> {len(LO)}")
print(f"STATION_INFO: {len(R.STATION_INFO)} -> {len(new_SI)} (+{len(new_names)})")
print(f"GRAPH 节点: {len(R.GRAPH)} -> {len(new_GRAPH)}")
print("新线:", [l for l in ["西康铁路","侯西铁路","咸铜铁路","甘钟铁路","神朔铁路","神大铁路"]])
print("SYN:", list(SYNS))
for ln in ["襄渝铁路","阳安铁路","宝成铁路","西成高速铁路","陇海铁路","宁西铁路",
           "包西铁路","西延高速铁路","宝中铁路"]:
    print(f"  ~ {ln}: {len(R.LINE_ORDER[ln])} -> {len(LO[ln])}")

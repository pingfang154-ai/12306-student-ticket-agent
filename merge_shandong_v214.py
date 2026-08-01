# -*- coding: utf-8 -*-
"""山东省补充站点合并 v2.13 -> v2.14 （增量只加不删，线内链 + 分支补 SYN）
读取「山东省/山东省补充站点总表.xlsx」，与 railway_data.py 比对整合。
铁律：仅增量、只加不删；新线/合成线必须写入 LINE_ORDER；GRAPH 从原图增量加边。
关键映射（Excel 标签 -> 规范库线键）：
  - 京沪铁路        -> 京沪铁路（普速）     （DB 京沪铁路 为 3 站残线，完整普速键为「京沪铁路（普速）」）
  - 济青高铁        -> 济青高速铁路
  - 日兰高铁        -> 日兰高速铁路
  - 石济客运专线     -> 石济高速铁路
  - 胶济客专        -> 胶济客运专线
  - 潍烟高铁        -> 潍烟高速铁路
其余 Excel 标签与库键同名（辛泰/德大/兖石/蓝烟/新兖/胶济/淄东/邯济/桃威/海青/枣临/青荣城际/京九 等）。
排除站（仅出现在备注、未计入 77 办客站数据行）：梁山站/郓城站/东明县站/福山北站/莱芜西站/商河北站。
"""
import sys, importlib.util, openpyxl, collections, json, re, os

BASE = "C:/Users/cjp15/Desktop/全国客运站点/交接文件夹第三版（含一、二合并）"
SRC = os.path.join(BASE, "src", "railway_data.py")
EXCEL = "C:/Users/cjp15/Desktop/全国客运站点/各省市细分站点/山东省/山东省补充站点总表.xlsx"

spec = importlib.util.spec_from_file_location("rd", SRC)
R = importlib.util.module_from_spec(spec); spec.loader.exec_module(R)

def clean(s):
    """剥离括号注记（路线/方位/省别），返回纯站名/地名。"""
    if not s:
        return s
    s = re.sub(r'[（(][^（）()]*[）)]', '', str(s))
    return s.strip()

# ---------- 1. 读取 Excel ----------
wb = openpyxl.load_workbook(EXCEL, data_only=True, read_only=True)
ws = wb.active
rows = list(ws.iter_rows(values_only=True))
raw = []
for r in rows[2:]:
    if r[0] is None:
        continue
    if str(r[0]).startswith("（"):
        continue
    raw.append(r)
# 补充被 Excel 遗漏但被多站 prev/next 引用、且为真实客运站的过路节点（德大铁路 商河站：
# Excel 备注明言“德大线在商河县的客运站为商河站”，阳信 prev/临邑 next 均指向它，缺则德大岛失连）。
raw.append(("商河站", "德大铁路", "—", "山东省济南市商河县", "阳信站", "临邑站",
            "德大铁路客运站（补充 pass-through，Excel 未单列但多站引用，真实办客站）"))
print(f"[读取] 山东省数据站行数 = {len(raw)}（含补充过路站 商河站）")

# ---------- 2. Excel 线路名 -> 规范库线路键 ----------
ALIAS = {
 "京沪铁路": ["京沪铁路（普速）"],          # DB 完整京沪普速线键
 "京九铁路": ["京九铁路"],
 "辛泰铁路": ["辛泰铁路"],
 "德大铁路": ["德大铁路"],
 "青荣城际铁路": ["青荣城际铁路"],
 "兖石铁路": ["兖石铁路"],
 "蓝烟铁路": ["蓝烟铁路"],
 "新兖铁路": ["新兖铁路"],
 "胶济铁路": ["胶济铁路"],
 "济青高铁": ["济青高速铁路"],
 "淄东铁路": ["淄东铁路"],
 "石济客运专线": ["石济高速铁路"],
 "日兰高铁": ["日兰高速铁路"],
 "邯济铁路": ["邯济铁路"],
 "桃威铁路": ["桃威铁路"],
 "胶济客专": ["胶济客运专线"],
 "枣临铁路": ["枣临铁路"],
 "海青铁路": ["海青铁路"],
 "潍莱高速铁路": ["潍莱高速铁路"],
 "济青高速铁路": ["济青高速铁路"],
 "青盐铁路": ["青盐铁路"],
 "潍烟高铁": ["潍烟高速铁路"],
 "济莱高速铁路": ["济莱高速铁路"],
}

# ---------- 3. 排除站（仅备注提及，未计入 77 办客站行；此处显式列出以防误入）----------
EXCLUDE = {"梁山站", "郓城站", "东明县站", "福山北站", "莱芜西站", "商河北站"}

# ---------- 4. 解析 所属省市 -> (province裸名, city键) ----------
def parse_prov(s):
    m = re.match(r'^([\u4e00-\u9fff]+?)(?:省|市|自治区)', s or "")
    return m.group(1) if m else (s or "")
def parse_city(s):
    # 行政区划片段：以 省/市/县/区/街道 结尾；剔除「乡/镇」避免「新乡」被误拆为「新+乡」。
    toks = re.findall(r'[\u4e00-\u9fff]+?(?:省|市|县|区|街道)', s or "")
    cands = [t for t in toks if t.endswith(('市', '县', '区')) and not t.startswith(('市', '区'))]
    if cands:
        return cands[-1]
    return s or ""

# ---------- 5. 建立 station_lines / line_rows ----------
station_lines = collections.defaultdict(list)   # st -> [(canon, prev, next, prov, city)]
line_rows = collections.defaultdict(list)        # canon -> [(st, prev, next)]
for r in raw:
    st_raw, lab_raw, order, prov_field, prev_raw, nxt_raw, note = r
    st = clean(st_raw)
    lab = clean(lab_raw)   # 线路名同样需剥离括号（如 兖石铁路（新石铁路）->兖石铁路）
    if st in EXCLUDE:
        continue
    for canon in ALIAS.get(lab, [lab]):  # 未显式归一的线直接用清洗后标签作规范键
        pv = parse_prov(clean(prov_field)); ct = parse_city(clean(prov_field))
        prev = clean(prev_raw); nxt = clean(nxt_raw)
        station_lines[st].append((canon, prev, nxt, pv, ct))
        line_rows[canon].append((st, prev, nxt))

# ---------- 6. 新站信息（工作态）----------
new_info = {}   # st -> {province, city, lines}
for st, lst in station_lines.items():
    if st in R.STATION_INFO:
        continue
    lines = []
    for (canon, p, n, pv, ct) in lst:
        if canon not in lines:
            lines.append(canon)
    pv = lst[0][3]; ct = lst[0][4]
    new_info[st] = {"province": pv, "city": ct, "lines": lines}

work_SI = dict(R.STATION_INFO)
for st, info in new_info.items():
    work_SI[st] = {"province": info["province"], "city": info["city"], "lines": list(info["lines"])}

def in_work(x):
    return x is not None and x in work_SI

# ---------- 7. 线路序列构建（统一链 + 分支补 SYN）----------
def build_line(canon, rows_for_line):
    base = list(R.LINE_ORDER.get(canon, []))
    data = [(st, prev, next) for (st, prev, next) in rows_for_line]
    nodes = set(base)
    for st, _, _ in data:
        nodes.add(st)
    for st, prev, next in data:
        for a in (prev, next):
            if in_work(a):
                nodes.add(a)
    adj = collections.defaultdict(set)
    for a, b in zip(base, base[1:]):
        if a in nodes and b in nodes:
            adj[a].add(b); adj[b].add(a)
    for st, prev, next in data:
        for a in (prev, next):
            if a in nodes:
                adj[st].add(a); adj[a].add(st)
    # 起点：优先 base[0]；否则取 prev 不在 nodes 的“头”站，否则度<=1 站，否则首个节点
    start = None
    if base:
        start = base[0]
    else:
        for st, prev, next in data:
            if prev not in nodes:
                start = st; break
        if start is None:
            for n in nodes:
                if len([y for y in adj[n] if y in nodes]) <= 1:
                    start = n; break
        if start is None:
            start = next(iter(nodes))
    chain = []; seen = set()
    stack = [(start, None)]
    while stack:
        cur, parent = stack.pop()
        if cur in seen:
            continue
        seen.add(cur); chain.append(cur)
        nbrs = [y for y in adj[cur] if y in nodes and y not in seen]
        for y in reversed(nbrs):
            stack.append((y, cur))
    # 分支边补 SYN：邻接但不在 chain 中相邻的边
    syn_edges = set()
    idx = {c: i for i, c in enumerate(chain)}
    for a in chain:
        for b in adj[a]:
            if b in nodes and abs(idx[a] - idx[b]) != 1:
                syn_edges.add(tuple(sorted((a, b))))
    return chain, syn_edges

new_LINE_ORDER = dict(R.LINE_ORDER)
branch_syn = set()          # 分支补 SYN 边 (a,b)
built_summary = []
for canon, rows_for_line in line_rows.items():
    seq, syn_edges = build_line(canon, rows_for_line)
    new_LINE_ORDER[canon] = seq
    for e in syn_edges:
        branch_syn.add(e)
    if canon in R.LINE_ORDER:
        built_summary.append(("UPDATE", canon, len(seq), len(R.LINE_ORDER[canon])))
    else:
        built_summary.append(("NEW", canon, len(seq), 0))

# 同步已存在站的 line 归属（Excel 中已存在站补线，如 庄寨/平度/莱西/胶州北/董家口/招远/历城 等）
for st, lst in station_lines.items():
    if st in R.STATION_INFO:
        cur = set(R.STATION_INFO[st].get("lines", []))
        changed = False
        for (canon, p, n, pv, ct) in lst:
            if canon not in cur:
                cur.add(canon); changed = True
        if changed:
            work_SI[st] = dict(R.STATION_INFO[st]); work_SI[st]["lines"] = sorted(cur)
            R.STATION_INFO[st] = work_SI[st]

# ---------- 8. 重建 GRAPH（增量加边）----------
gset = {k: set(v) for k, v in R.GRAPH.items()}
for line, seq in new_LINE_ORDER.items():
    for a, b in zip(seq, seq[1:]):
        gset.setdefault(a, set()).add(b)
        gset.setdefault(b, set()).add(a)

# 分支 SYN 线写入（Dijkstra 可见）
for a, b in branch_syn:
    name = f"__SYN__{a}__{b}"
    if name in new_LINE_ORDER:
        continue
    new_LINE_ORDER[name] = [a, b]
    gset.setdefault(a, set()).add(b); gset.setdefault(b, set()).add(a)

# ---------- 9. 连通性修复（合成线兜底孤立新站）----------
from collections import deque
hubs = [h for h in ["北京南站", "上海虹桥站", "上海站", "广州南站", "武汉站", "西安站", "成都东站",
                   "杭州东站", "南京南站", "合肥站", "徐州站", "郑州站", "南昌站", "长沙南站", "温州南站", "济南站", "青岛站"]
        if h in gset]
reach = set(); dq = deque(hubs)
while dq:
    x = dq.popleft()
    if x in reach:
        continue
    reach.add(x)
    for y in gset.get(x, []):
        if y not in reach:
            dq.append(y)

new_stations_all = list(new_info.keys())
syn_lines = []   # 兜底 SYN (st, cand, name)
def add_syn(st, cand):
    name = f"__SYN__{st}__{cand}"
    if name in new_LINE_ORDER:
        return
    new_LINE_ORDER[name] = [st, cand]
    gset.setdefault(st, set()).add(cand); gset.setdefault(cand, set()).add(st)
    syn_lines.append((st, cand, name))
    reach.add(st); reach.add(cand)

for st in new_stations_all:
    if st in reach:
        continue
    info = new_info[st]; pv = info["province"]; ct = info["city"]
    st_lines = set(info.get("lines", []))
    cand = None
    # 1) 优先同线可达站（铁路连通最合理）
    for c in reach:
        ci = work_SI.get(c)
        if ci and (st_lines & set(ci.get("lines", []))) and c != st:
            cand = c; break
    # 2) 同城可达站
    if cand is None:
        for c in reach:
            ci = work_SI.get(c)
            if ci and ci.get("city") == ct and c != st:
                cand = c; break
    # 3) 同省可达站（优先市后缀）
    if cand is None:
        prov_cands = []
        for c in reach:
            ci = work_SI.get(c)
            if ci and ci.get("province") == pv and c != st:
                prov_cands.append(c)
        if prov_cands:
            se = prov_cands[0]
            for c in prov_cands:
                if str(work_SI.get(c, {}).get("city", "")).endswith("市"):
                    se = c; break
            cand = se
    if cand is None:
        cand = next(iter(reach))
    add_syn(st, cand)

new_GRAPH = {k: sorted(v) for k, v in gset.items()}

# ---------- 10. 更新 CITY/PROV/ALIAS ----------
new_CTS = {k: list(v) for k, v in R.CITY_TO_STATIONS.items()}
new_PTS = {k: list(v) for k, v in R.PROVINCE_TO_STATIONS.items()}
new_CALIAS = dict(R.CITY_ALIAS)
alias_added = []
for st, info in new_info.items():
    ct = info["city"]; pv = info["province"]
    new_CTS.setdefault(ct, [])
    if st not in new_CTS[ct]:
        new_CTS[ct].append(st)
    new_PTS.setdefault(pv, [])
    if st not in new_PTS[pv]:
        new_PTS[pv].append(st)
    m = re.match(r'^([\u4e00-\u9fff]+?)(?:市|县|区|州|盟)$', ct)
    if m:
        bare = m.group(1)
        if bare not in new_CALIAS and bare != ct:
            new_CALIAS[bare] = ct
            alias_added.append((bare, ct))

# ---------- 11. 写回 railway_data.py ----------
new_SI = dict(R.STATION_INFO)
for st, info in new_info.items():
    new_SI[st] = {"province": info["province"], "city": info["city"], "lines": info["lines"]}

with open(SRC, encoding="utf-8") as f:
    src_lines = f.read().splitlines()
hi = next(i for i, l in enumerate(src_lines) if l.strip().startswith("LINE_NAME_ALIAS"))
tail = src_lines[hi:]

total_lines = len(new_LINE_ORDER)
total_stations = len(new_SI)
meta = {
    "version": "2.14",
    "sources": R.META.get("sources", []) + ["山东省补充站点总表.xlsx"],
    "generated_at": "2026-07-27",
    "line_count": total_lines,
    "station_count": total_stations,
    "note": ("v2.14 山东省补充站点合并：单点式增量并入 67 个新办客站 + 11 条新线（辛泰/德大/兖石/蓝烟/新兖/"
             "胶济/淄东/邯济/桃威/海青/枣临），并向 11 条既有线（京沪铁路（普速）/京九铁路/青荣城际铁路/"
             "石济高速铁路/日兰高速铁路/胶济客运专线/潍莱高速铁路/济青高速铁路/青盐铁路/潍烟高速铁路/"
             "济莱高速铁路）精确插入新站；济青高铁/日兰高铁/石济客运专线/胶济客专 归一为库内规范键。"
             "仅增量，未删任何原有边。")
}

def jd(d):
    return json.dumps(d, ensure_ascii=False, separators=(',', ':'))

out = []
out.append("# -*- coding: utf-8 -*-")
out.append("# 整理后的全国铁路数据层 v2.14（山东省补充站点合并，自动生成，请勿手动编辑）")
out.append("# 生成时间：2026-07-27")
out.append("# 数据来源：既有 v2.13 数据源 + 山东省补充站点总表.xlsx")
out.append(f"# 线路数：{total_lines}  车站数：{total_stations}")
out.append("")
out.append(f"META = {jd(meta)}")
out.append("")
out.append(f"LINE_ORDER = {jd(new_LINE_ORDER)}")
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

# ---------- 12. 同步 4 个 JSON ----------
data_dir = None
for cand in [os.path.join(BASE, "data"), os.path.join(BASE, "src", "data")]:
    if os.path.isdir(cand):
        data_dir = cand; break
json_map = {
    "lines_order.json": new_LINE_ORDER,
    "graph_adjacency.json": new_GRAPH,
    "station_info.json": new_SI,
    "city_to_stations.json": new_CTS,
}
if data_dir:
    for fn, d in json_map.items():
        fp = os.path.join(data_dir, fn)
        if os.path.exists(fp):
            json.dump(d, open(fp, "w", encoding="utf-8"), ensure_ascii=False)
    print(f"[JSON] 已同步 {data_dir}")
else:
    print("[JSON] 未找到 data 目录，跳过")

# ---------- 13. 汇总输出 ----------
print("\n===== 山东省合并汇总 =====")
print(f"新增线路: {sum(1 for t,_,_,_ in built_summary if t=='NEW')} 条；更新既有线: {sum(1 for t,_,_,_ in built_summary if t=='UPDATE')} 条")
print(f"新增车站(STATION_INFO): {len(new_info)} 个")
print(f"新增城市别名: {len(alias_added)} 条")
print(f"分支补 SYN 线: {len(branch_syn)} 条")
print(f"兜底连通性修复合成线: {len(syn_lines)} 条")
print("\n-- 新建线路 --")
for t, c, n, o in built_summary:
    if t == "NEW":
        print(f"  + {c}  ({n} 站)")
print("\n-- 更新既有线（新站数）--")
for t, c, n, o in built_summary:
    if t == "UPDATE":
        diff = n - o
        if diff != 0:
            print(f"  ~ {c}: {o} -> {n} (+{diff})")
print("\n-- 分支补 SYN 线 --")
for a, b in sorted(branch_syn):
    print(f"  * {a} -- {b}")
print("\n-- 兜底连通性修复合成线 --")
for st, cand, name in syn_lines:
    print(f"  * {st} -- {cand}")
print(f"\n总计: LINE_ORDER={total_lines}  STATION_INFO={total_stations}  GRAPH节点={len(new_GRAPH)}")
print("DONE")

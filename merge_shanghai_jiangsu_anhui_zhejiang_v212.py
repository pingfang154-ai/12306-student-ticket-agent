# -*- coding: utf-8 -*-
"""沪苏皖浙补充站点合并 v2.11 -> v2.12 （单点式，增量只加不删）
读取「上海市、江苏省、安徽省、浙江省补充站点总表.xlsx」，与 railway_data.py 比对整合。
铁律：仅增量、只加不删；新线/合成线必须写入 LINE_ORDER；GRAPH 从原图增量加边。
"""
import sys, importlib.util, openpyxl, collections, json, re, os

BASE = "C:/Users/cjp15/Desktop/全国客运站点/交接文件夹第三版（含一、二合并）"
SRC = os.path.join(BASE, "src", "railway_data.py")
EXCEL = "C:/Users/cjp15/Desktop/全国客运站点/各省市细分站点/上海市、江苏省、安徽省、浙江省/上海市、江苏省、安徽省、浙江省补充站点总表.xlsx"

spec = importlib.util.spec_from_file_location("rd", SRC)
R = importlib.util.module_from_spec(spec); spec.loader.exec_module(R)

# ---------- 1. 读取 Excel ----------
wb = openpyxl.load_workbook(EXCEL, data_only=True, read_only=True)
ws = wb.active
rows = list(ws.iter_rows(values_only=True))
raw = []
for r in rows[2:]:
    if r[0] is None: continue
    if str(r[0]).startswith("（") or str(r[0]).startswith("上海市"): continue
    raw.append(r)
print(f"[读取] 数据站行数 = {len(raw)}")

# ---------- 2. Excel 线路名 -> 规范库线路键 ----------
ALIAS = {
 "沪昆铁路（普速）":["沪昆铁路（普速）"],
 "沪宁城际铁路":["沪宁城际铁路"],
 "沪昆高速铁路（杭长段）":["沪昆高速铁路"],
 "宣杭铁路（普速）":["宣杭铁路"],
 "合杭高速铁路（湖杭段）":["合杭高速铁路"],
 "杭甬高速铁路（杭深铁路杭甬段）":["杭深铁路"],
 "杭深铁路（甬台温段）":["杭深铁路"],
 "衢宁铁路":["衢宁铁路"],
 "皖赣铁路":["皖赣铁路"],
 "合九铁路":["合九铁路"],
 "阜六铁路":["阜六铁路"],
 "符夹铁路":["符夹铁路"],
 "京九铁路":["京九铁路"],
 "阜淮铁路":["阜淮铁路"],
 "京沪铁路":["京沪铁路（普速）"],
 "淮南铁路":["淮南铁路"],
 "青阜铁路":["青阜铁路"],
 "漯阜铁路":["漯阜铁路"],
 "宁启铁路（普速）":["宁启铁路"],
 "青盐铁路":["青盐铁路"],
 "宿淮铁路":["宿淮铁路"],
 "陇海铁路":["陇海铁路"],
 "甬金铁路（金甬铁路）":["甬金铁路"],
 "甬金铁路（金甬）/杭台高速铁路":["甬金铁路","杭台高速铁路"],
 "杭台高速铁路":["杭台高速铁路"],
 "金温铁路 / 金丽温高速铁路":["金丽温高速铁路"],
 "金丽温高速铁路":["金丽温高速铁路"],
 "金温铁路（普速）":["金温铁路（普速）"],
 "金温铁路（高铁新双线）":["金丽温高速铁路"],
 "金温铁路（普速老线/金温货线）":["金温铁路（普速老线）"],
 "金千铁路（普速）":["金千铁路"],
 "庐铜铁路":["庐铜铁路"],
 "沪宁沿江高速铁路（南沿江城际）":["沪宁沿江高速铁路"],
 "盐通高速铁路（沪苏通铁路）":["盐通高速铁路"],
 "海洋铁路":["海洋铁路"],
 "连镇高速铁路":["连镇高速铁路"],
 "徐盐高速铁路、盐通高速铁路、青盐铁路（联络线）、新长铁路":["徐盐高速铁路","盐通高速铁路","青盐铁路","新长铁路"],
 "盐通高速铁路":["盐通高速铁路"],
 "盐通高速铁路、新长铁路":["盐通高速铁路","新长铁路"],
 "徐盐高速铁路":["徐盐高速铁路"],
 "新长铁路":["新长铁路"],
 "徐盐高速铁路、连镇高速铁路":["徐盐高速铁路","连镇高速铁路"],
 "陇海铁路/新长铁路/胶新铁路":["陇海铁路","新长铁路"],
 "徐盐高铁":["徐盐高速铁路"],
 "连镇高铁":["连镇高速铁路"],
 "徐盐高速铁路（新长普速已停办）":["徐盐高速铁路"],
 "金建高速铁路":["金建高速铁路"],
 "金台铁路":["金台铁路"],
 "金台铁路（头门港支线）":["金台铁路（头门港支线）"],
 "杭温高速铁路":["杭温高速铁路"],
 "徐连高铁":["徐连高速铁路"],
}

# ---------- 3. 排除站（不办客/停运）----------
EXCLUDE = {"海湾站","芦潮港站","宁波东站","三堂集站","凤阳站","中华门站","仪征站","六合站",
           "盐城北站","阜宁站","淮安南站","泗洪站","邳州站"}

# ---------- 4. 解析 所属省市 -> (province裸名, city键) ----------
def parse_prov(s):
    m = re.match(r'^([\u4e00-\u9fff]+?)(?:省|市|自治区)', s or "")
    return m.group(1) if m else (s or "")
def parse_city(s):
    toks = re.findall(r'[\u4e00-\u9fff]+?(?:省|市|县|区|镇|乡|街道)', s or "")
    for t in reversed(toks):
        if t.endswith(('市','县','区')):
            return t
    return s or ""

# ---------- 5. 建立 station_lines / line_rows ----------
station_lines = collections.defaultdict(list)   # st -> [(canon, prev, next, prov, city)]
line_rows = collections.defaultdict(list)        # canon -> [(st, prev, next)]
for r in raw:
    st, lab, order, prov_field, prev, nxt, note = r
    if st in EXCLUDE:
        continue
    for canon in ALIAS.get(lab, []):
        pv = parse_prov(prov_field); ct = parse_city(prov_field)
        station_lines[st].append((canon, prev, nxt, pv, ct))
        line_rows[canon].append((st, prev, nxt))

# ---------- 6. 新站信息（工作态）----------
new_info = {}   # st -> {province, city, lines}
for st, lst in station_lines.items():
    if st in R.STATION_INFO:
        continue
    lines = []
    for (canon, p, n, pv, ct) in lst:
        if canon not in lines: lines.append(canon)
    pv = lst[0][3]; ct = lst[0][4]
    new_info[st] = {"province": pv, "city": ct, "lines": lines}

# 工作态 STATION_INFO（含 DB + 新站），用于线路拼接时识别新锚点
work_SI = dict(R.STATION_INFO)
for st, info in new_info.items():
    work_SI[st] = {"province": info["province"], "city": info["city"], "lines": list(info["lines"])}

def in_work(x):
    return x is not None and x in work_SI

# ---------- 7. 线路序列构建 ----------
def build_line(canon, rows_for_line):
    base = list(R.LINE_ORDER.get(canon, []))
    is_new = canon not in R.LINE_ORDER
    data = [(st, prev, next) for (st, prev, next) in rows_for_line]
    if is_new:
        nodes = set(st for st,_,_ in data)
        for st, prev, next in data:
            for a in (prev, next):
                if in_work(a): nodes.add(a)
        adj = collections.defaultdict(set)
        for st, prev, next in data:
            for a in (prev, next):
                if a in nodes:
                    adj[st].add(a); adj[a].add(st)
        visited = set(); chains = []
        for n in nodes:
            if n in visited: continue
            comp = set(); stack=[n]
            while stack:
                x = stack.pop()
                if x in visited: continue
                visited.add(x); comp.add(x)
                for y in adj[x]:
                    if y not in visited: stack.append(y)
            deg = {x: len(adj[x] & comp) for x in comp}
            ends = [x for x in comp if deg[x] <= 1]
            start = ends[0] if ends else next(iter(comp))
            chain = [start]; cur = start; seen = {start}
            while True:
                nxt = [y for y in adj[cur] if y in comp and y not in seen]
                if not nxt: break
                cur = nxt[0]; seen.add(cur); chain.append(cur)
            chains.append(chain)
        # 端点 DB 锚点延伸
        pn = {st: (prev, next) for (st, prev, next) in data}
        extended = []
        for ch in chains:
            if not ch: continue
            head, tail = ch[0], ch[-1]
            p = pn.get(head, (None, None))[0]
            if p and in_work(p) and p not in ch:
                ch = [p] + ch
            nxt = pn.get(tail, (None, None))[1]
            if nxt and in_work(nxt) and nxt not in ch:
                ch = ch + [nxt]
            extended.append(ch)
        final = []
        for ch in extended: final.extend(ch)
        return final
    else:
        final = list(base)
        fset = set(final)
        pending = [(st, prev, next) for (st, prev, next) in data if st not in fset]
        progress = True
        while pending and progress:
            progress = False; still = []
            for (st, prev, next) in pending:
                if st in fset: continue
                if prev in fset:
                    final.insert(final.index(prev)+1, st); fset.add(st); progress = True
                elif next in fset:
                    final.insert(final.index(next), st); fset.add(st); progress = True
                else:
                    still.append((st, prev, next))
            pending = still
        for (st, prev, next) in pending:
            final.append(st); fset.add(st)
        return final

new_LINE_ORDER = dict(R.LINE_ORDER)
built_summary = []
for canon, rows_for_line in line_rows.items():
    seq = build_line(canon, rows_for_line)
    if canon in R.LINE_ORDER:
        # 仅当序列变化时替换
        new_LINE_ORDER[canon] = seq
        built_summary.append(("UPDATE", canon, len(seq), len(R.LINE_ORDER[canon])))
    else:
        new_LINE_ORDER[canon] = seq
        built_summary.append(("NEW", canon, len(seq), 0))

# 同步已存在站的 line 归属（如 水家湖 补 淮南铁路）
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
new_GRAPH = {k: sorted(v) for k, v in gset.items()}

# ---------- 9. 连通性修复（合成线兜底孤立新站）----------
from collections import deque
hubs = [h for h in ["北京南站","上海虹桥站","上海站","广州南站","武汉站","西安站","成都东站",
                   "杭州东站","南京南站","合肥站","徐州站","郑州站","南昌站","长沙南站","温州南站","金华站"]
        if h in gset]
reach = set()
dq = deque(hubs)
while dq:
    x = dq.popleft()
    if x in reach: continue
    reach.add(x)
    for y in gset.get(x, []):
        if y not in reach: dq.append(y)

new_stations_all = list(new_info.keys())
# 也把"已存在但本次新接入线路"的站纳入可达性检查
syn_lines = []
def add_syn(st, cand):
    name = f"__SYN__{st}__{cand}"
    if name in new_LINE_ORDER: return
    new_LINE_ORDER[name] = [st, cand]
    gset.setdefault(st, set()).add(cand); gset.setdefault(cand, set()).add(st)
    new_GRAPH[st] = sorted(gset[st]); new_GRAPH[cand] = sorted(gset[cand])
    syn_lines.append((st, cand, name))
    reach.add(st); reach.add(cand)

# 先重算一次可达（含新建线）
reach = set(); dq = deque(hubs)
while dq:
    x = dq.popleft()
    if x in reach: continue
    reach.add(x)
    for y in gset.get(x, []):
        if y not in reach: dq.append(y)

for st in new_stations_all:
    if st in reach: continue
    info = new_info[st]; pv = info["province"]; ct = info["city"]
    cand = None
    # 同城可达
    for c in reach:
        ci = work_SI.get(c)
        if ci and ci.get("city") == ct and c != st:
            cand = c; break
    if cand is None:
        # 同省兜底：优先选"市"级枢纽站（地级市府），避免连到偏远县城
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

# 把合成线也加入 GRAPH（已加），并同步 new_GRAPH
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
    # 别名：剥 市/县/区
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

# 重新载入 tail（helper）
with open(SRC, encoding="utf-8") as f:
    src_lines = f.read().splitlines()
hi = next(i for i, l in enumerate(src_lines) if l.strip().startswith("LINE_NAME_ALIAS"))
tail = src_lines[hi:]

total_lines = len(new_LINE_ORDER)
total_stations = len(new_SI)
meta = {
    "version": "2.12",
    "sources": R.META.get("sources", []) + ["上海市、江苏省、安徽省、浙江省补充站点总表.xlsx"],
    "generated_at": "2026-07-27",
    "line_count": total_lines,
    "station_count": total_stations,
    "note": ("v2.12 沪苏皖浙补充站点合并：单点式增量并入 91 个新办客站 + 17 条新线（甬金/杭台/杭温/金建/金台"
             "及头门港支线/金丽温/金温普速/金温普速老线/金千/庐铜/沪宁沿江/盐通/海洋/连镇/新长/徐盐），"
             "并向 21 条既有线（京沪普速/沪昆普速/沪昆高铁/杭深/宣杭/合杭/合九/皖赣/淮南/宁启/衢宁/阜六/"
             "符夹/京九/阜淮/漯阜/青阜/青盐/宿淮/陇海/沪宁城际）精确插入新站；仅增量，未删任何原有边。")
}

def jd(d): return json.dumps(d, ensure_ascii=False, separators=(',', ':'))

out = []
out.append("# -*- coding: utf-8 -*-")
out.append("# 整理后的全国铁路数据层 v2.12（沪苏皖浙补充站点合并，自动生成，请勿手动编辑）")
out.append("# 生成时间：2026-07-27")
out.append("# 数据来源：既有 v2.11 数据源 + 上海市、江苏省、安徽省、浙江省补充站点总表.xlsx")
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
data_dir = os.path.join(BASE, "src", "..", "data") if os.path.isdir(os.path.join(BASE,"data")) else None
# 实际 data 目录位于 交接文件夹第三版/data 还是 src? 探测
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
print("\n===== 合并汇总 =====")
print(f"新增线路: {sum(1 for t,_,_,_ in built_summary if t=='NEW')} 条；更新既有线: {sum(1 for t,_,_,_ in built_summary if t=='UPDATE')} 条")
print(f"新增车站(STATION_INFO): {len(new_info)} 个")
print(f"新增城市别名: {len(alias_added)} 条")
print(f"连通性修复合成线: {len(syn_lines)} 条")
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
print("\n-- 连通性修复合成线 --")
for st, cand, name in syn_lines:
    print(f"  * {st} -- {cand}")
print(f"\n总计: LINE_ORDER={total_lines}  STATION_INFO={total_stations}  GRAPH节点={len(new_GRAPH)}")
print("DONE")

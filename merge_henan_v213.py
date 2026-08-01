# -*- coding: utf-8 -*-
"""河南省补充站点合并 v2.12 -> v2.13 （单点式，增量只加不删）
读取「河南省/河南省补充站点总表.xlsx」，与 railway_data.py 比对整合。
铁律：仅增量、只加不删；新线/合成线必须写入 LINE_ORDER；GRAPH 从原图增量加边。
关键修正（相对 v2.12 沪苏皖浙批）：
  - 原始 DB 中「京广铁路（普速）」是缺河南段的残线，完整京广普速线键为「京广铁路」，
    Excel 的「京广铁路（普速）」「京广铁路」一律归一为「京广铁路」。
  - 「太焦高速铁路」与 DB 中「郑太高速铁路」为同一线，归一为「郑太高速铁路」。
  - Excel 的 前/后一站 含括号路线注记（如「遂平站（经驻马店）」「阜南站（皖）」），
    须剥离括号后再作为节点名使用；所属省市的「（航空港区）」亦剥离。
"""
import sys, importlib.util, openpyxl, collections, json, re, os

BASE = "C:/Users/cjp15/Desktop/全国客运站点/交接文件夹第三版（含一、二合并）"
SRC = os.path.join(BASE, "src", "railway_data.py")
EXCEL = "C:/Users/cjp15/Desktop/全国客运站点/各省市细分站点/河南省/河南省补充站点总表.xlsx"

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
print(f"[读取] 河南省数据站行数 = {len(raw)}")

# ---------- 2. Excel 线路名 -> 规范库线路键 ----------
ALIAS = {
 "京广铁路（普速）":["京广铁路"],            # DB 完整京广普速线键为「京广铁路」
 "京广高速铁路":["京广高速铁路"],
 "京九铁路":["京九铁路"],
 "宁西铁路":["宁西铁路"],
 "漯阜铁路":["漯阜铁路"],
 "焦柳铁路":["焦柳铁路"],
 "孟宝铁路（漯宝铁路）":["孟宝铁路"],
 "商合杭高铁":["商合杭高速铁路"],
 "陇海铁路":["陇海铁路"],
 "京广铁路":["京广铁路"],
 "郑开城际":["郑开城际铁路"],
 "郑机城际":["郑机城际铁路"],
 "郑焦城际":["郑焦城际铁路"],
 "郑焦城际铁路":["郑焦城际铁路"],   # Excel 同线标签不统一（南阳寨/黄河景区用「郑焦城际」）
 "济郑高铁":["济郑高速铁路"],
 "新月铁路":["新月铁路"],
 "太焦高速铁路":["郑太高速铁路"],          # 与「郑太高速铁路」同线
 "瓦日铁路":["瓦日铁路"],
}

# ---------- 3. 排除站（不办客/停运，见 Excel 备注说明）----------
EXCLUDE = {"长垣站","沁阳站","修武站","焦作东站"}

# ---------- 4. 解析 所属省市 -> (province裸名, city键) ----------
def parse_prov(s):
    m = re.match(r'^([\u4e00-\u9fff]+?)(?:省|市|自治区)', s or "")
    return m.group(1) if m else (s or "")
def parse_city(s):
    # 行政区划片段：以 省/市/县/区/街道 结尾；剔除「乡/镇」避免「新乡」被误拆为「新+乡」，
    # 进而产生以伪「市X」开头的错误 token（如 市原阳县）。
    toks = re.findall(r'[\u4e00-\u9fff]+?(?:省|市|县|区|街道)', s or "")
    cands = [t for t in toks if t.endswith(('市','县','区')) and not t.startswith(('市','区'))]
    if cands:
        return cands[-1]
    return s or ""

# ---------- 5. 建立 station_lines / line_rows ----------
station_lines = collections.defaultdict(list)   # st -> [(canon, prev, next, prov, city)]
line_rows = collections.defaultdict(list)        # canon -> [(st, prev, next)]
for r in raw:
    st_raw, lab, order, prov_field, prev_raw, nxt_raw, note = r
    st = clean(st_raw)
    if st in EXCLUDE:
        continue
    for canon in ALIAS.get(lab, []):
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

# ---------- 7. 线路序列构建 ----------
def build_line(canon, rows_for_line):
    base = list(R.LINE_ORDER.get(canon, []))
    is_new = canon not in R.LINE_ORDER
    data = [(st, prev, next) for (st, prev, next) in rows_for_line]
    if is_new:
        nodes = set(st for st,_,_ in data)
        for st, prev, next in data:
            for a in (prev, next):
                if in_work(a):
                    nodes.add(a)
        adj = collections.defaultdict(set)
        for st, prev, next in data:
            for a in (prev, next):
                if a in nodes:
                    adj[st].add(a); adj[a].add(st)
        visited = set(); chains = []
        for n in nodes:
            if n in visited:
                continue
            comp = set(); stack=[n]
            while stack:
                x = stack.pop()
                if x in visited:
                    continue
                visited.add(x); comp.add(x)
                for y in adj[x]:
                    if y not in visited:
                        stack.append(y)
            deg = {x: len(adj[x] & comp) for x in comp}
            ends = [x for x in comp if deg[x] <= 1]
            start = ends[0] if ends else next(iter(comp))
            chain = [start]; cur = start; seen = {start}
            while True:
                nxt = [y for y in adj[cur] if y in comp and y not in seen]
                if not nxt:
                    break
                cur = nxt[0]; seen.add(cur); chain.append(cur)
            chains.append(chain)
        # 端点 DB 锚点延伸
        pn = {st: (prev, next) for (st, prev, next) in data}
        extended = []
        for ch in chains:
            if not ch:
                continue
            head, tail = ch[0], ch[-1]
            p = pn.get(head, (None, None))[0]
            if p and in_work(p) and p not in ch:
                ch = [p] + ch
            nxt = pn.get(tail, (None, None))[1]
            if nxt and in_work(nxt) and nxt not in ch:
                ch = ch + [nxt]
            extended.append(ch)
        final = []
        for ch in extended:
            final.extend(ch)
        return final
    else:
        final = list(base)
        fset = set(final)
        pending = [(st, prev, next) for (st, prev, next) in data if st not in fset]
        progress = True
        while pending and progress:
            progress = False; still = []
            for (st, prev, next) in pending:
                if st in fset:
                    continue
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
        new_LINE_ORDER[canon] = seq
        built_summary.append(("UPDATE", canon, len(seq), len(R.LINE_ORDER[canon])))
    else:
        new_LINE_ORDER[canon] = seq
        built_summary.append(("NEW", canon, len(seq), 0))

# 同步已存在站的 line 归属（如 固始站 已含宁西铁路，无需改；此处对 Excel 中已存在站补线）
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

# ---------- 7b. 济郑高速铁路南段补完（河南终到郑州东）----------
# DB 济郑高速铁路仅含山东段（…莘县站,濮阳东站）。河南段：濮阳东—新乡南—新乡东—郑州东。
if "济郑高速铁路" in new_LINE_ORDER:
    seq = list(new_LINE_ORDER["济郑高速铁路"])
    for extra in ["新乡南站", "新乡东站", "郑州东站"]:
        if extra not in seq:
            seq.append(extra)
    new_LINE_ORDER["济郑高速铁路"] = seq
    for extra in ["新乡南站", "新乡东站", "郑州东站"]:
        info = work_SI.get(extra) or R.STATION_INFO.get(extra)
        if info is not None:
            cur = set(info.get("lines", []))
            if "济郑高速铁路" not in cur:
                cur.add("济郑高速铁路")
                work_SI[extra] = dict(info); work_SI[extra]["lines"] = sorted(cur)
                if extra in R.STATION_INFO:
                    R.STATION_INFO[extra] = work_SI[extra]
    print("[补完] 济郑高速铁路南段：新乡南/新乡东/郑州东 已接入")

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
syn_lines = []
def add_syn(st, cand):
    name = f"__SYN__{st}__{cand}"
    if name in new_LINE_ORDER:
        return
    new_LINE_ORDER[name] = [st, cand]
    gset.setdefault(st, set()).add(cand); gset.setdefault(cand, set()).add(st)
    new_GRAPH[st] = sorted(gset[st]); new_GRAPH[cand] = sorted(gset[cand])
    syn_lines.append((st, cand, name))
    reach.add(st); reach.add(cand)

# 重算可达（含新建线）
reach = set(); dq = deque(hubs)
while dq:
    x = dq.popleft()
    if x in reach:
        continue
    reach.add(x)
    for y in gset.get(x, []):
        if y not in reach:
            dq.append(y)

for st in new_stations_all:
    if st in reach:
        continue
    info = new_info[st]; pv = info["province"]; ct = info["city"]
    cand = None
    for c in reach:
        ci = work_SI.get(c)
        if ci and ci.get("city") == ct and c != st:
            cand = c; break
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
    "version": "2.13",
    "sources": R.META.get("sources", []) + ["河南省补充站点总表.xlsx"],
    "generated_at": "2026-07-27",
    "line_count": total_lines,
    "station_count": total_stations,
    "note": ("v2.13 河南省补充站点合并：单点式增量并入 56 个新办客站 + 5 条新线（孟宝/新月/郑开城际/"
             "郑机城际/郑焦城际），并向 11 条既有线（京广铁路/京广高速铁路/京九铁路/宁西铁路/漯阜铁路/"
             "焦柳铁路/商合杭高速铁路/陇海铁路/济郑高速铁路/瓦日铁路/郑太高速铁路）精确插入新站；"
             "补完济郑高速铁路河南终到段（新乡南/新乡东/郑州东）；仅增量，未删任何原有边。")
}

def jd(d):
    return json.dumps(d, ensure_ascii=False, separators=(',', ':'))

out = []
out.append("# -*- coding: utf-8 -*-")
out.append("# 整理后的全国铁路数据层 v2.13（河南省补充站点合并，自动生成，请勿手动编辑）")
out.append("# 生成时间：2026-07-27")
out.append("# 数据来源：既有 v2.12 数据源 + 河南省补充站点总表.xlsx")
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
print("\n===== 河南省合并汇总 =====")
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

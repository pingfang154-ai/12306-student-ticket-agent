# -*- coding: utf-8 -*-
"""
学生票区间合规判断引擎
======================
基于数据层 railway_data.py（图 + 同城解析）与规则层 student_rules.json
实现：区间合规判断 / 反向购票识别 / 修改建议。

用法：
    from student_ticket_checker import check_student_ticket
    res = check_student_ticket("成都","北京","成都东","北京西",seat="二等座")

命令行交互：
    python student_ticket_checker.py
批量自测：
    python student_ticket_checker.py --test
"""
import json, os, sys, heapq, itertools
from collections import deque, defaultdict

# ---- 复用同目录下的数据层与规则层 ----
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
import railway_data as R   # 数据层：LINE_ORDER/GRAPH/STATION_INFO/resolve_location

# ---- 路径适配：支持 flat 和 handover 分层结构 ----
_rules_candidates = [
    os.path.join(_HERE, "student_rules.json"),                   # flat: src/
    os.path.join(os.path.dirname(_HERE), "data", "student_rules.json"),  # handover: data/
]
_RULES_PATH = None
for _p in _rules_candidates:
    if os.path.isfile(_p):
        _RULES_PATH = _p
        break
if _RULES_PATH is None:
    _RULES_PATH = _rules_candidates[0]  # 即使不存在也 fallback

with open(_RULES_PATH, encoding="utf-8") as _f:
    RULES = json.load(_f)["student_ticket"]

ALLOWED_SEATS = set(RULES["allowed_seats"])
DISALLOWED_SEATS = set(RULES["disallowed_seats"])
QUOTA = RULES["annual_quota"]
INTERVAL_MOD = RULES["interval_modification"]
FRESH = RULES["freshman_graduate"]

# 预构建：相邻站对 -> 共享线路集合（用于判断是否跨线换乘）
_EDGE_LINES = defaultdict(set)
for _ln, _sts in R.LINE_ORDER.items():
    for i in range(len(_sts) - 1):
        a, b = _sts[i], _sts[i+1]
        _EDGE_LINES[frozenset((a, b))].add(_ln)
TRANSFER_PENALTY = 2.0   # 每次跨线换乘的额外权重，使路径优先沿单一干线行进

# =====================================================================
# 1. 路径搜索核心：带换乘惩罚的 Dijkstra（支持临时边禁）
# =====================================================================
def _dijkstra(setA, setB, blocked_edges=None):
    """带换乘惩罚的 Dijkstra 内核，支持临时边禁。
    
    参数：
        setA, setB: 源站集与目标站集（均为 set[str]）
        blocked_edges: 需禁用的边集合（frozenset/set 的 frozenset((u,v))）
    返回：
        (path: list[str] | None, cost: float)
    """
    if blocked_edges is None:
        blocked_edges = frozenset()
    ends = set(setB)
    prev = {}   # (station, incoming_line) -> (prev_station, prev_line)
    best = {}   # (station, incoming_line) -> cost
    pq = []
    for s in setA:
        if s in R.GRAPH:
            heapq.heappush(pq, (0.0, s, None))
            best[(s, None)] = 0.0
            prev[(s, None)] = None
    for s in setA:
        if s in ends:
            return ([s], 0.0)
    final_state = None
    while pq:
        cost, u, in_line = heapq.heappop(pq)
        if cost > best.get((u, in_line), float("inf")):
            continue
        if u in ends:
            final_state = (u, in_line)
            break
        for v in R.GRAPH.get(u, []):
            if frozenset((u, v)) in blocked_edges:
                continue
            lines = _EDGE_LINES.get(frozenset((u, v)), set())
            if not lines:
                continue
            if in_line in lines:
                ncost = cost + 1.0
                nline = in_line
            else:
                nline = next(iter(lines))
                ncost = cost + 1.0 + (0.0 if in_line is None else TRANSFER_PENALTY)
            key = (v, nline)
            if ncost < best.get(key, float("inf")):
                best[key] = ncost
                prev[key] = (u, in_line)
                heapq.heappush(pq, (ncost, v, nline))
    if final_state is None:
        return (None, float("inf"))
    path = []
    cur = final_state
    while cur is not None:
        path.append(cur[0])
        cur = prev.get(cur)
    return (path[::-1], best[final_state])

# =====================================================================
# 2. 单路径搜索（向后兼容的薄封装）
# =====================================================================
def find_path_between_cities(cityA, cityB):
    """返回 cityA 任一车站 → cityB 任一车站 的一条合理径路（站点列表）。"""
    setA = R.resolve_location(cityA)
    setB = R.resolve_location(cityB)
    if not setA or not setB:
        return None
    path, _ = _dijkstra(setA, setB)
    return path

# =====================================================================
# 3. 多路径搜索（简化版 Yen's KSP）
# =====================================================================
def find_multiple_paths_between_cities(cityA, cityB, K=3):
    """返回 cityA ↔ cityB 间的前 K 条合理径路（简化版 Yen's KSP）。
    
    返回：
        list[list[str]]，按路径代价升序排列，最多 K 条。
        若无路径则返回空列表。
    """
    setA = R.resolve_location(cityA)
    setB = R.resolve_location(cityB)
    if not setA or not setB:
        return []
    path1, _ = _dijkstra(setA, setB)
    if path1 is None:
        return []
    paths = [path1]
    path_set = {tuple(path1)}
    candidates = {}
    explored_edges = set()
    while len(paths) < K:
        current_path = paths[-1]
        found_any = False
        for i in range(len(current_path) - 1):
            edge = frozenset((current_path[i], current_path[i+1]))
            if edge in explored_edges:
                continue
            explored_edges.add(edge)
            new_path, cost = _dijkstra(setA, setB, blocked_edges={edge})
            if new_path is None:
                continue
            found_any = True
            key = tuple(new_path)
            if key not in path_set:
                if key not in candidates or cost < candidates[key][1]:
                    candidates[key] = (new_path, cost)
        if not candidates:
            break
        best_key = min(candidates, key=lambda k: candidates[k][1])
        best_path, _ = candidates.pop(best_key)
        paths.append(best_path)
        path_set.add(best_key)
    return paths

# =====================================================================
# 2.5 廊道探测（跨廊道 / 多枢纽绕行场景）
# =====================================================================
# 加载枢纽站清单（data/hub_stations.json）：用于"经枢纽绕行"的补充验证
_HUB_PATH_CANDIDATES = [
    os.path.join(os.path.dirname(_HERE), "data", "hub_stations.json"),
    os.path.join(_HERE, "hub_stations.json"),
]
HUB_STATIONS = []
for _hp in _HUB_PATH_CANDIDATES:
    if os.path.isfile(_hp):
        try:
            _loaded = json.load(open(_hp, encoding="utf-8"))
            if isinstance(_loaded, list):
                HUB_STATIONS = _loaded
            elif isinstance(_loaded, dict):
                # 兼容 {"hub_stations": [...]} / {"hubs": [...]} 两种字典格式
                HUB_STATIONS = _loaded.get("hub_stations") or _loaded.get("hubs") or []
        except Exception:
            HUB_STATIONS = []
        break

# 绕行上限守卫（auto 廊道，无显式途经站时）：廊道路径跳数不得超过
# "学校↔家庭直达最短跳数"的该倍数。实测用于拦截南京→贵阳→西安(1.91)、
# 南京→成都→西安(1.43) 这类离谱绕行，避免误判合规。
CORRIDOR_HOPS_FACTOR = 1.4

# 绕行上限守卫（explicit 廊道，用户显式给出途经站时）：允许更大绕行，因为
# 途经站是用户明确指定的真实行程。实测：武汉→大理经重庆+成都+广通北=1.33、
# 南京→西安经凯里南+荔波+安顺=2.45（均放行）；南昌→株洲绕行福建=4.80（拦截）。
CORRIDOR_VIA_FACTOR = 2.6

# 反向邻接表（用于"能否到达家庭所在地"的可达性判定）
_REV_GRAPH = {}
for _u, _vs in R.GRAPH.items():
    for _v in _vs:
        _REV_GRAPH.setdefault(_v, []).append(_u)


# =====================================================================
# 2.4 枢纽站别名映射（A 组：自动对齐同城节点）
# ---------------------------------------------------------------------
# 背景：hub_stations.json 中部分站名在拓扑图里没有同名节点（例如“株洲站”在图里
# 只有“株洲西站”），导致这些枢纽“失效”——auto 廊道会静默跳过它们，若用户把其中
# 某个当作显式途经站输入也会因无法归一化而被略过。
# 解决：加载时把“失效枢纽”自动映射到同城既有图节点，使其可作为廊道枢轴 / 用户
# 显式途经站生效。B 组（城市整体缺失于拓扑）仍保持未解析（交由用户补数据）。
# =====================================================================
# 方向后缀剥离：单次从左到右剥离所有已知后缀，避免把“济南站”误剥成“济”。
_HUB_SUFFIXES = ["中心站", "北站", "南站", "东站", "西站", "站"]

def _strip_station_suffix(name):
    n = name
    for s in _HUB_SUFFIXES:
        if n.endswith(s) and len(n) > len(s):
            n = n[:len(n) - len(s)]
    return n

def _same_city_node(name):
    """在 GRAPH 中找与 name 同城（城市核心前缀匹配）的图节点，返回候选列表。"""
    b = _strip_station_suffix(name)
    best, bl = [], 0
    for n in R.GRAPH:
        nb = _strip_station_suffix(n)
        l = 0
        for a, c in zip(b, nb):
            if a == c:
                l += 1
            else:
                break
        if l > bl:
            bl, best = l, [n]
        elif l == bl and l > 0:
            best.append(n)
    return best if bl >= 2 else []

# 手动特例：非方向后缀、需显式指定同城目标的枢纽（目标节点须经图验证存在）
HUB_MANUAL_ALIAS = {
    "广州白云站": "广州南站",
    "重庆沙坪坝站": "重庆西站",
    "济南站": "济南西站",
}

# HUB_ALIAS：枢纽原始名 -> 解析后的站集（set[str]，可能为空 = B 组未解决）
HUB_ALIAS = {}
for _h in HUB_STATIONS:
    _s = R.resolve_location(_h)
    if not _s:
        if _h in HUB_MANUAL_ALIAS:
            _t = HUB_MANUAL_ALIAS[_h]
            _s = {_t} if _t in R.GRAPH else set()
        else:
            _c = _same_city_node(_h)
            _s = {_c[0]} if _c else set()
    HUB_ALIAS[_h] = _s

# 所有枢纽解析后站点的并集（用于 _is_hub_set 判断）
HUB_NODES = set()
for _s in HUB_ALIAS.values():
    HUB_NODES |= _s

def resolve_hub(name):
    """解析枢纽名：优先用别名映射（含 A 组同城对齐），否则回退 resolve_location。
    若 name 已是站集/列表（内部调用场景），直接归一化返回。"""
    if isinstance(name, str):
        if name in HUB_ALIAS:
            return HUB_ALIAS[name]
        return R.resolve_location(name)
    return _as_set(name)

def _is_hub_set(station_set):
    """判断一组车站是否包含枢纽站（基于解析后的枢纽节点并集）。"""
    return bool(station_set & HUB_NODES)


def _as_set(x):
    """将站名/城市名/集合/列表统一为站集（set[str]）。"""
    if isinstance(x, set):
        return x
    if isinstance(x, (list, tuple)):
        s = set()
        for _i in x:
            s |= _as_set(_i)
        return s
    return R.resolve_location(x)


def _bfs_path(src_set, dst_set):
    """无向 BFS 求 src_set 中任一站→dst_set 中任一站 的一条最短路（按跳数）。
    返回站序列 list[str] 或 None。"""
    src_set = set(src_set)
    dst_set = set(dst_set)
    if not src_set or not dst_set:
        return None
    inter = src_set & dst_set
    if inter:
        return [next(iter(inter))]
    prev = {}
    dq = deque()
    for s in src_set:
        if s not in prev:
            prev[s] = None
            dq.append(s)
    found = None
    while dq:
        u = dq.popleft()
        if u in dst_set:
            found = u
            break
        for v in R.GRAPH.get(u, []):
            if v not in prev:
                prev[v] = u
                dq.append(v)
    if found is None:
        return None
    path = [found]
    while prev[found] is not None:
        found = prev[found]
        path.append(found)
    return path[::-1]


def _bfs_dist(src_set):
    """多源 BFS 距离字典（从 src_set 出发的跳数）。"""
    src_set = set(src_set)
    dist = {}
    dq = deque()
    for s in src_set:
        if s not in dist:
            dist[s] = 0
            dq.append(s)
    while dq:
        u = dq.popleft()
        for v in R.GRAPH.get(u, []):
            if v not in dist:
                dist[v] = dist[u] + 1
                dq.append(v)
    return dist


def _bfs_dist_rev(dst_set):
    """多源反向 BFS 距离字典（到达 dst_set 还需的跳数）。"""
    dst_set = set(dst_set)
    dist = {}
    dq = deque()
    for s in dst_set:
        if s not in dist:
            dist[s] = 0
            dq.append(s)
    while dq:
        u = dq.popleft()
        for v in _REV_GRAPH.get(u, []):
            if v not in dist:
                dist[v] = dist[u] + 1
                dq.append(v)
    return dist


def _direct_hops(setA, setB):
    """学校↔家庭 直达最短跳数（廊道路径的绕行上限基准）。"""
    d = _bfs_dist(setA)
    best = None
    for st in setB:
        if st in d:
            best = d[st] if best is None else min(best, d[st])
    return best if best is not None else float("inf")


def find_path_via_hubs(start, end, via_stations, hub_list, max_depth=3):
    """廊道探测（核心 API）：让 start→end 依次途经 via_stations 中的各站，
    逐段用现有图搜索（BFS 最短路径，复用 _bfs_path）拼接出完整径路。

    参数：
      start/end：起点/终点站名或城市名（自动经 resolve_location 归一化为站集）。
      via_stations：用户输入的途经站列表（有序）。函数会按序把 start→via[0]→
                    …→via[n]→end 各段分别搜索并拼接。
      hub_list：枢纽站名称列表（自 data/hub_stations.json 加载）。其中属于枢纽的
                途经站作为“拼接枢轴”；非枢纽途经站合并到相邻段，视为该段中间站
                （要求其确实落在该段最短路径上）。
      max_depth：最大途经站个数上限（防止无限拼接），默认 3。

    返回：
      (是否找到路径: bool, 完整路径列表: list[str])

    示例：
      find_path_via_hubs("武汉","大理",["重庆","成都","广通北"], HUB_STATIONS)
        → (True, 武汉→重庆→成都→广通北→大理 的完整站序)
    """
    setA = _as_set(start)
    setB = _as_set(end)
    if not setA or not setB:
        return (False, [])
    via = [resolve_hub(v) for v in via_stations]
    via = [v for v in via if v]
    # max_depth 作为途经站个数上限（防止无限拼接）
    if max_depth and len(via) > max_depth:
        return (False, [])
    if not via:
        p = _bfs_path(setA, setB)
        return (bool(p), p) if p else (False, [])

    def _is_hub(s):
        return _is_hub_set(s)

    # 将 via 中非枢纽站“挂”到相邻枢纽段，并校验其确在段路径上。
    # 实现上：依次路由 起点→via[0]→…→via[n]→终点（全部途经站按序作为必经点），
    # 每段独立 BFS 最短路径；拼接后去重（保证无环）。
    points = [setA] + via + [setB]
    built = []
    for i in range(len(points) - 1):
        seg = _bfs_path(points[i], points[i + 1])
        if not seg:
            return (False, [])
        if built:
            built = built[:-1] + seg   # 去掉衔接重复站
        else:
            built = list(seg)

    # 去重：仅消除相邻重复，保留顺序（非相邻重复为正常换乘，不动）
    out = []
    for s in built:
        if not out or out[-1] != s:
            out.append(s)

    # 校验：所有途经站确实出现在最终路径上（非枢纽站须落于其相邻段路径）
    outset = set(out)
    for v in via:
        if not (v & outset):
            return (False, [])

    # 校验：枢纽途经站必须作为“枢轴”出现在路径中（即确实被用作拼接点）
    for v in via:
        if _is_hub(v) and not (v & outset):
            return (False, [])
    return (True, out)


def _corridor_all_paths(setA, setB, via_hubs, limit=12, max_hops_factor=CORRIDOR_HOPS_FACTOR):
    """auto 廊道候选生成（无显式途经站时的回退）：在 find_path_via_hubs 基础上
    枚举枢纽子集/排列拼接，并施加绕行守卫，仅返回跳数 <= 直达最短跳数*因子 的径路。
    端点固定为 setA↔setB（即学校↔家庭），via_hubs 作为中间枢轴池。"""
    L0 = _direct_hops(setA, setB)
    if L0 == float("inf"):
        return []
    cap = int(L0 * max_hops_factor) + 1
    hubs = [resolve_hub(h) for h in via_hubs]
    hubs = [h for h in hubs if h]
    n = len(hubs)
    results = []
    # 枚举枢纽子集（从大到小）与排列，逐段 BFS 拼接
    for k in range(min(n, 3), 0, -1):
        for sub in itertools.combinations(range(n), k):
            for perm in itertools.permutations(sub):
                via_seq = [hubs[i] for i in perm]
                found, p = find_path_via_hubs(setA, setB, via_seq, HUB_STATIONS, max_depth=k)
                if found and p and len(p) <= cap:
                    results.append(p)
                    if len(results) >= limit:
                        return results[:limit]
    return results[:limit]


def _select_relevant_hubs(setSchool, setHome, top_n=8):
    """从 HUB_STATIONS 中挑选与当前优惠区间相关的枢纽（可达学校且能到达家庭），
    按"介于度"（到两端跳数和）升序取前 top_n。"""
    if not HUB_STATIONS:
        return []
    ds = _bfs_dist(setSchool)
    dh = _bfs_dist_rev(setHome)
    ranked = []
    for h in HUB_STATIONS:
        hs = resolve_hub(h)
        if not hs:
            continue
        d_s = min((ds[x] for x in hs if x in ds), default=None)
        d_h = min((dh[x] for x in hs if x in dh), default=None)
        if d_s is None or d_h is None:
            continue
        ranked.append((d_s + d_h, h))
    ranked.sort(key=lambda t: t[0])
    return [h for _, h in ranked[:top_n]]


def _match_on_path(path, setC, setD, setSchool, setHome):
    """在单条候选径路上判断购票区间是否合规，返回 (ok, is_reverse, reason)。
    reason 为 None 表示 C/D 不在该路径上（无需记录诊断）。"""
    if not path:
        return False, False, None
    path_set = set(path)
    c_in_school = bool(setC & setSchool)
    c_in_home = bool(setC & setHome)
    d_in_school = bool(setD & setSchool)
    d_in_home = bool(setD & setHome)
    if (c_in_school and d_in_home) or (c_in_home and d_in_school):
        is_reverse = bool(c_in_home and d_in_school)
        return True, is_reverse, "购票区间端点分别落在学校所在地与家庭所在地，符合优惠区间"
    c_on = setC & path_set
    d_on = setD & path_set
    if not c_on or not d_on:
        return False, False, None
    c_idx = min(path.index(s) for s in c_on)
    d_idx = min(path.index(s) for s in d_on)
    if c_idx < d_idx:
        return True, False, "购票区间落在优惠路径上（正向），符合优惠区间"
    if d_idx < c_idx:
        return True, True, "购票区间落在优惠路径上（反向），符合优惠区间，可购买反向车票"
    return False, False, None


# =====================================================================
# 2. 区间合规判断
# =====================================================================
def check_compliance(school_city, home_city, dep_station, arr_station,
                     seat=None, fresh_grad=False, new_home_city=None,
                     via_stations=None):
    """判断购票区间是否符合学生优惠区间。

    参数：
      new_home_city: 可选，若用户已修改家庭所在地，传入新家庭城市；
                     引擎将用 school↔new_home 新区间搜索路径。
    
    返回 dict:
      ok: bool                 区间是否合规
      is_reverse: bool         是否为反向购票（家庭→学校方向之外的逆序）
      seat_invalid: bool       席别是否不符
      reason: str              结论说明
      path: list[str]          优惠区间代表路径（站点序列）
      dep_city / arr_city: str 出发/到达站所在城市
      warnings: list[str]      非阻断提示（资质/次数/新生）
    """
    setSchool = R.resolve_location(school_city)
    setHome = R.resolve_location(home_city)
    setC = R.resolve_location(dep_station)
    setD = R.resolve_location(arr_station)

    warnings = []

    # 城市解析失败
    if not setSchool:
        return _fail(f"无法识别学校所在地「{school_city}」", warnings)
    if not setHome:
        return _fail(f"无法识别家庭所在地「{home_city}」", warnings)
    if not setC:
        return _fail(f"无法识别出发站「{dep_station}」", warnings)
    if not setD:
        return _fail(f"无法识别到达站「{arr_station}」", warnings)

    # 学校与家庭同城 -> 无优惠区间
    if setSchool & setHome:
        return _fail("学校所在地与家庭所在地在同一城市，不构成学生优惠区间", warnings)

    # ---- 改家端点切换（多区间联合判断）----
    # 保留原家庭 setHome；若提供 new_home_city，则另存新家庭，两个区间都参与判断。
    using_new_home = False
    setHomeNew = None
    home_city_new = None
    if new_home_city and new_home_city.strip():
        new_set = R.resolve_location(new_home_city.strip())
        if new_set and not (setSchool & new_set):
            setHomeNew = new_set
            home_city_new = new_home_city.strip()
            using_new_home = True
            warnings.append(f"已切换优惠区间为：{school_city}(学校) ↔ {home_city_new}(新家庭所在地)")
            warnings.append(f"注意：修改家庭所在地后有 24 小时冷却期，当前学年仍限购 4 次单程")
    # 多区间联合：端点判定时把"原家庭 ∪ 新家庭"都视为家庭所在地
    setHomeAll = set(setHome)
    if setHomeNew:
        setHomeAll |= setHomeNew

    # 取两条区间的代表路径（原区间 + 改家后新区间），任一区间的合理径路即可判定合规
    paths = find_multiple_paths_between_cities(school_city, home_city, K=10)
    if not paths:
        if setHomeNew:
            paths = find_multiple_paths_between_cities(school_city, home_city_new, K=10)
        if not paths:
            return _fail("在铁路网络中找不到学校所在地与家庭所在地之间的可达路径", warnings)
    paths2 = []
    if setHomeNew:
        p2 = find_multiple_paths_between_cities(school_city, home_city_new, K=10)
        if p2:
            paths2 = p2
    # 衍生区间：新家庭 ↔ 原家庭（改家后学生往返两家之间亦属合理行程）
    paths3 = []
    if setHomeNew:
        p3 = find_multiple_paths_between_cities(home_city_new, home_city, K=10)
        if p3:
            paths3 = p3

    dep_city = R.STATION_INFO.get(next(iter(setC)), {}).get("city", "")
    arr_city = R.STATION_INFO.get(next(iter(setD)), {}).get("city", "")

    best_result = [None]   # 记录最佳不匹配路径用于诊断（list 容器，便于闭包改写）
    ok = False
    is_reverse = False
    reason = ""
    path = paths[0]

    def _record_diag(p):
        if best_result[0] is not None:
            return
        pset = set(p)
        miss = []
        if not (setC & pset):
            miss.append(f"出发站「{dep_station}」")
        if not (setD & pset):
            miss.append(f"到达站「{arr_station}」")
        if miss:
            best_result[0] = ("、".join(miss) + "不在学校↔家庭的优惠路径上", p)

    # ---- 阶段一：显式途经站廊道探测（优先于 Yen，按新规范）----
    # 用户显式给出途经站时，优先尝试"经这些站的优惠路径"，以发现 KSP 单边阻塞
    # 无法发现的跨廊道/多枢纽绕行径路（如 武汉→大理 经 重庆+成都）。
    # 施加 2.6× 绕行守卫：廊道路径跳数不得超过"购票区间直达最短跳数"的该倍数，
    # 避免把离谱绕行（如 南昌→株洲 绕行福建）误判为合规。
    if via_stations:
        found, corr_path = find_path_via_hubs(
            dep_station, arr_station, via_stations, HUB_STATIONS, max_depth=3)
        if found and corr_path:
            L0 = _direct_hops(setC, setD)
            cap = int(L0 * CORRIDOR_VIA_FACTOR) + 1 if L0 != float("inf") else float("inf")
            if len(corr_path) <= cap:
                m_ok, m_rev, m_reason = _match_on_path(
                    corr_path, setC, setD, setSchool, setHomeAll)
                if m_ok:
                    ok, is_reverse, reason, path = (
                        True, m_rev,
                        "廊道探测：经途经站 " + "、".join(via_stations) + " 的优惠路径，符合优惠区间",
                        corr_path)
                elif m_reason is None:
                    _record_diag(corr_path)

    # ---- 阶段二：Yen 多路径匹配（保持原有判定，零回归）----
    if not ok:
        for p in paths:
            m_ok, m_rev, m_reason = _match_on_path(p, setC, setD, setSchool, setHomeAll)
            if m_ok:
                ok, is_reverse, reason, path = True, m_rev, m_reason, p
                break
            if m_reason is None:
                _record_diag(p)
        if not ok and paths2:
            for p in paths2:
                m_ok, m_rev, m_reason = _match_on_path(p, setC, setD, setSchool, setHomeAll)
                if m_ok:
                    ok, is_reverse, reason, path = True, m_rev, m_reason, p
                    break
                if m_reason is None:
                    _record_diag(p)
        if not ok and paths3:
            for p in paths3:
                m_ok, m_rev, m_reason = _match_on_path(p, setC, setD, setSchool, setHomeAll)
                if m_ok:
                    ok, is_reverse, reason, path = True, m_rev, m_reason, p
                    break
                if m_reason is None:
                    _record_diag(p)

    # ---- 阶段三：auto 廊道探测（无显式途经站时的补充回退）----
    # 仅在用户未显式给出途经站时启用，避免对简单区间造成误判；施加 1.4× 守卫。
    if not ok and HUB_STATIONS and not via_stations:
        via = _select_relevant_hubs(setSchool, setHomeAll)[:8]
        corr = _corridor_all_paths(setSchool, setHomeAll, via, limit=12)
        for p in corr:
            m_ok, m_rev, m_reason = _match_on_path(p, setC, setD, setSchool, setHomeAll)
            if m_ok:
                ok, is_reverse, reason, path = True, m_rev, m_reason, p
                break
            if m_reason is None:
                _record_diag(p)

    # ---- 阶段四：购票区间端点必经探测（KSP 遮蔽兜底）----
    # 场景：网络加密后出现更短的替代径路，Yen Top-K 枚举不再包含"较长但合法"
    # 的含购票端点径路（如 成都↔上海 经南京南 被 经徐州普速 的短径路遮蔽）。
    # 处理：把购票区间端点 C/D 自身作为必经点，探测 学校↔家庭 的廊道路径；
    # 施加 2.6× 绕行守卫（对比学校↔家庭直达最短跳数），杜绝离谱绕行误判。
    if not ok:
        def _canon_station(name, sset):
            """确定性取代表站：优先用户输入的真实站名（自动补「站」字），
            否则取字典序最小站，避免 set 迭代序引入随机性。"""
            n = (name or "").strip()
            for cand in (n, n + "站"):
                if cand in sset:
                    return cand
            return min(sset) if sset else None
        rep_c = _canon_station(dep_station, setC)
        rep_d = _canon_station(arr_station, setD)
        if rep_c and rep_d:
            L0sh = _direct_hops(setSchool, setHomeAll)
            cap4 = int(L0sh * CORRIDOR_VIA_FACTOR) + 1 if L0sh != float("inf") else float("inf")
            # 若购票区间两端点同处一条真实线路（如辛泰线慢车 泰山↔南博山），
            # 该区间本身就是实际列车径路，放宽绕行守卫至 3.5×。
            lines_c = set(R.STATION_INFO.get(rep_c, {}).get("lines", []))
            lines_d = set(R.STATION_INFO.get(rep_d, {}).get("lines", []))
            if lines_c & lines_d and L0sh != float("inf"):
                cap4 = max(cap4, int(L0sh * 3.5) + 1)
            for v1, v2 in ((rep_c, rep_d), (rep_d, rep_c)):
                # 朝家方向单调递进守卫：途经点须依次逼近家庭所在地，
                # 杜绝"先背向家庭绕行再折返"的离谱径路（如 南京↔保定 绕黄山、
                # 南昌↔上海 绕株洲），同时放行真正介于两地之间的枢纽（如
                # 成都↔上海 之 南京南：d(南京南,家)=5 < d(学校,家)=14）。
                # 端点站本就位于学校/家庭城市时不视为"途经绕行点"，豁免其守卫。
                d1 = L0sh if v1 in setSchool else _direct_hops({v1}, setHomeAll)
                d2 = _direct_hops({v2}, setHomeAll)
                if not (d1 <= L0sh and (d2 <= d1 or v2 in setHomeAll)):
                    continue
                # 分段 BFS 拼接（学校→v1→v2→家庭），不依赖枢纽表，
                # 各段均为最短路，总长确定，避免 set 迭代序引入的随机性。
                seg1 = _bfs_path(setSchool, {v1})
                seg2 = _bfs_path({v1}, {v2})
                seg3 = _bfs_path({v2}, setHomeAll)
                if not (seg1 and seg2 and seg3):
                    continue
                p4 = seg1 + seg2[1:] + seg3[1:]
                if len(p4) <= cap4:
                    m_ok, m_rev, m_reason = _match_on_path(
                        p4, setC, setD, setSchool, setHomeAll)
                    if m_ok:
                        ok, is_reverse, reason, path = True, m_rev, m_reason, p4
                        break

    if not ok:
        # 所有阶段均不匹配：使用诊断信息
        if best_result[0]:
            reason, path = best_result[0]
        else:
            reason, path = "出发站与到达站为同一车站", paths[0]

    # ---- Step 5: 席别校验（非阻断）----
    seat_invalid = False
    if seat:
        s = seat.strip()
        if s and s not in ALLOWED_SEATS:
            seat_invalid = True

    # ---- 非阻断提示 ----
    if fresh_grad:
        warnings.append("新生/毕业生仅可购买1次学生票（凭录取通知书/学校书面证明）")
    warnings.append(f"每学年（{QUOTA['school_year']}）可购 {QUOTA['count']} 次单程，不可结转")
    warnings.append("乘车前请确保已完成本学年学生优惠资质核验（未核验仅提示，不影响区间判断）")

    result = {
        "ok": ok,
        "is_reverse": is_reverse,
        "seat_invalid": seat_invalid,
        "reason": reason,
        "path": path,
        "dep_city": dep_city,
        "arr_city": arr_city,
        "warnings": warnings,
        "suggest_modify_home": False,
        "suggested_new_home": "",
        "new_path": [],
    }

    # ---- 修改家庭所在地建议（仅当不合规且未传入 new_home_city 时尝试）----
    if not ok and not new_home_city and arr_city and arr_city != home_city:
        # 尝试将家庭所在地改为到达城市，重新判断
        new_result = check_compliance(school_city, arr_city, dep_station, arr_station,
                                       seat=seat, fresh_grad=fresh_grad)
        if new_result["ok"]:
            result["suggest_modify_home"] = True
            result["suggested_new_home"] = arr_city
            result["new_path"] = new_result["path"]
            result["reason"] = f"若将家庭所在地修改为「{arr_city}」，则购票区间将合规。"

    return result

def _fail(reason, warnings):
    return {"ok": False, "is_reverse": False, "seat_invalid": False,
            "reason": reason, "path": [], "dep_city": "", "arr_city": "",
            "warnings": warnings,
            "suggest_modify_home": False, "suggested_new_home": "", "new_path": []}

# =====================================================================
# 3. 修改建议
# =====================================================================
def suggest(school_city, home_city, dep_station, arr_station, seat, result):
    """按规则 suggestion_priority 生成中文建议列表。"""
    tips = []
    if result["ok"]:
        # 合规情形下的提示
        if result["is_reverse"]:
            tips.append("✅ 您购买的是反向区间（家庭→学校方向），符合优惠区间，可直接购票。")
        else:
            tips.append("✅ 购票区间符合学生优惠区间，可直接购票。")
        if result["seat_invalid"]:
            tips.append(f"⚠️ 席别「{seat}」不在学生票允许范围。"
                        f"仅限：{'、'.join(RULES['allowed_seats'])}。")
        tips.append("💡 在优惠区间内购买联程车票，各段开车时间间隔在5个自然日内，仅扣减1次优惠乘车次数。")
        return tips

    # 不合规情形：按建议优先级
    path = result["path"]
    path_set = set(path)
    setC = R.resolve_location(dep_station)
    setD = R.resolve_location(arr_station)
    c_on = bool(setC & path_set)
    d_on = bool(setD & path_set)

    # 1) 反向可行：C、D 均在路径上但用户给的方向与优惠方向相反 -> 上面 ok 时已处理；
    #    不合规时若 C、D 都在路径但顺序问题，其实已被判 ok，故此处不重复。

    # 2) C 在区间、D 不在 -> 建议把到达站改为路径上离 D 最近的站
    if c_on and not d_on:
        nearest = _nearest_station_on_path(arr_station, path)
        if nearest:
            tips.append(f"📌 到达站「{arr_station}」不在优惠路径上。"
                        f"建议将到达站改为优惠路径上的「{nearest}」（离您原到达站较近的大站）。")
    # C 不在、D 在 -> 建议把出发站改为路径上离 C 最近的站
    if (not c_on) and d_on:
        nearest = _nearest_station_on_path(dep_station, path)
        if nearest:
            tips.append(f"📌 出发站「{dep_station}」不在优惠路径上。"
                        f"建议将出发站改为优惠路径上的「{nearest}」。")
    # 两端都不在 -> 整体超区间
    if (not c_on) and (not d_on):
        # 3) 整体超区间且根因可能是家庭变更
        if INTERVAL_MOD["home_changeable"]:
            d_city = result.get("arr_city", "")
            tips.append(f"📌 购票区间整体超出优惠区间。学校所在地不可修改；"
                        f"若父母已迁居，可在12306 App 内申请修改家庭所在地"
                        f"（如改为「{d_city}」），并重新加盖学校公章、更新学生优惠卡。")

    # 4) 席别不符
    if result["seat_invalid"]:
        tips.append(f"⚠️ 席别「{seat}」不在学生票允许范围。"
                    f"仅限：{'、'.join(RULES['allowed_seats'])}。")

    # 5) 端点站无快车/直通车
    tips.append("💡 若您学生证记载的车站无快车/直通车停靠，可发售至离该站最近的大站"
                "（可超过记载区间）。")

    if not tips:
        tips.append("📌 购票区间不符合优惠区间，请核对学校↔家庭所在地的优惠路径后调整。")
    return tips

def _nearest_station_on_path(query_station, path):
    """在 path 上找一个"较近"的代表站：优先同城站，否则取路径中点附近的大站。"""
    qset = R.resolve_location(query_station)
    if not qset:
        return path[len(path)//2] if path else None
    qcity = R.STATION_INFO.get(next(iter(qset)), {}).get("city", "")
    # 1) 路径上是否有同城站
    for s in path:
        if R.STATION_INFO.get(s, {}).get("city") == qcity:
            return s
    # 2) 否则取路径中点站
    return path[len(path)//2] if path else None

# =====================================================================
# 4. 综合入口
# =====================================================================
def check_student_ticket(school_city, home_city, dep_station, arr_station,
                         seat=None, fresh_grad=False, new_home_city=None,
                         via_stations=None):
    """一站式入口：返回 {result, suggestions}。

    新增参数：
      new_home_city: 若用户已修改家庭所在地，传入新家庭城市，启用多区间联合判断。
      via_stations: 用户显式给出的途经站列表，触发廊道探测（优先于 Yen 算法）。
    """
    res = check_compliance(school_city, home_city, dep_station, arr_station,
                           seat, fresh_grad, new_home_city, via_stations)
    tips = suggest(school_city, home_city, dep_station, arr_station, seat, res)
    return {"result": res, "suggestions": tips}

# =====================================================================
# 5. 命令行交互
# =====================================================================
def _print_report(report):
    r = report["result"]
    print("\n" + "=" * 56)
    print("【区间合规判断】", "✅ 符合" if r["ok"] else "❌ 不符合")
    print("结论：", r["reason"])
    if r["path"]:
        print("优惠路径：", " → ".join(r["path"]))
    if r["seat_invalid"]:
        print("席别：不符（学生票仅限：{}）".format("、".join(RULES["allowed_seats"])))
    if r["warnings"]:
        print("提示：")
        for w in r["warnings"]:
            print("  ·", w)
    print("-" * 56)
    print("建议：")
    for t in report["suggestions"]:
        print("  ", t)
    print("=" * 56)

def main_interactive():
    print("=== 学生票区间合规判断（输入城市名或站名均可，自动同城归并）===")
    school = input("学校所在地城市: ").strip()
    home = input("家庭所在地城市: ").strip()
    dep = input("出发站: ").strip()
    arr = input("到达站: ").strip()
    seat = input("席别(可空, 如 二等座/硬座/商务座): ").strip() or None
    fg = input("是否新生/毕业生?(y/N): ").strip().lower() == "y"
    report = check_student_ticket(school, home, dep, arr, seat, fg)
    _print_report(report)

if __name__ == "__main__":
    if "--test" in sys.argv:
        import test_cases
        test_cases.run_all()
    else:
        main_interactive()

# =====================================================================
# 途经点路线检查
# =====================================================================
def check_route_segments(school_city, home_city, stations, seat=None, fresh_grad=False,
                          new_home_city=None, via_stations=None):
    """检查包含途经站的整条路线，返回每个区间的独立判定结果。

    :param stations: 列表，如 ['北京南', '南京南', '武汉', '上海虹桥']
    :param new_home_city: 改家场景下的新家庭城市（多区间联合判断）。
    :param via_stations: 用户显式途经站（逐段触发廊道探测）。
    :return: dict {segments, overall_summary, has_adult_segments, has_student_segments}
    """
    if len(stations) < 2:
        return {"error": "至少需要出发站和到达站", "segments": [],
                "overall_summary": "", "has_adult_segments": False, "has_student_segments": False}

    segments = []
    for i in range(len(stations) - 1):
        dep = stations[i]
        arr = stations[i+1]
        # 多区间：整条路线的途经站依次作为各段的显式 via（廊道探测优先）
        seg_via = None
        if via_stations:
            seg_via = via_stations[i:i+1] if i < len(via_stations) else None
        result_wrapper = check_student_ticket(
            school_city, home_city, dep, arr, seat, fresh_grad,
            new_home_city=new_home_city, via_stations=seg_via)
        r = result_wrapper.get("result", {})
        ok = r.get("ok", False)
        ticket_type = "学生票" if ok else "成人票"
        reason = r.get("reason", "不在优惠路径上" if not ok else "在优惠路径上")
        segments.append({
            "dep": dep, "arr": arr, "ok": ok, "reason": reason,
            "ticket_type": ticket_type, "path": r.get("path", []),
            "is_reverse": r.get("is_reverse", False),
            "seat_invalid": r.get("seat_invalid", False),
        })

    student_segs = [s for s in segments if s["ok"]]
    adult_segs = [s for s in segments if not s["ok"]]
    if not adult_segs:
        summary = "✅ 全程均可购买学生票！"
    elif not student_segs:
        summary = "❌ 全程均需购买成人票，无法使用学生票。"
    else:
        summary = f"路线中 {len(adult_segs)} 个区间需购买成人票，其余 {len(student_segs)} 个区间可购买学生票。"

    return {
        "segments": segments,
        "overall_summary": summary,
        "has_adult_segments": bool(adult_segs),
        "has_student_segments": bool(student_segs),
    }

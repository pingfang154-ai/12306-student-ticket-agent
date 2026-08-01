# 新对话交接说明（学生票合规 Agent · 2026-07-25）

> **用途**：本文件 + 同包内其他文件，用于把「当前对话」中产生的全部新内容交接给一个**新的对话**，
> 让新对话在不依赖本对话上下文的情况下，安全地继续做学生票项目的功能开发，减少幻觉与模糊提问。
>
> **本包定位**：这是一次**对话级**交接，不是项目从零开始。项目基础（handover 文件夹）仍在磁盘原处；
> 本包只额外提供「本次对话新增/变更的产物 + 上手所需的最小代码、数据快照」。

---

## 0. 一句话背景

学生票优惠区间合规判定 Agent：给定「学校城市 ↔ 家庭城市」优惠区间和一次实际购票区间，判断是否符合学生票规则，
并给出修改建议。核心是一个铁路拓扑图 + 路径搜索 + 同城/反向/联程判定引擎。

---

## 1. 本次对话做了什么（时间线摘要）

| 阶段 | 关键动作 | 产物 |
|---|---|---|
| ① 接手 | 读取交接文件夹，确认初始库缺失山东/青海线路、38 个枢纽站无法解析 | `context/project_context_summary.md`（已更新） |
| ② A 组 | 23 个枢纽站自动映射到同城节点（站名↔城市解析增强） | `src/student_ticket_checker.py` 内 `HUB_ALIAS`/`resolve_hub` |
| ③ B 组根因 | 定位根因：初始库缺失**山东省、青海省**全部线路及车站 | — |
| ④ 补山东/青海 | 增量合并两份 Excel（`山东省…xlsx`、`青海省…xlsx`），+12 新线 +3 合成联络线 | `merge_shandong_qinghai.py`（项目根）、`railway_data.py`→v2.1 |
| ⑤ 补剩余 8 城 | 用 `冀黑湘苏津客运铁路线路站点表.xlsx` 把 B 组最后 8 城（山海关/大庆/大庆西/绥化/鹤岗/永州/连云港/塘沽）接入全国网 | `merge_remaining_8_cities.py`、`railway_data.py`→v2.2 |
| ⑥ GitHub | 建私有仓库 `12306-student-ticket-agent`，推送初始提交 + 本总结文档 | 仓库：`https://github.com/pingfang154-ai/12306-student-ticket-agent` |
| ⑦ 地图审计 | 基于全国铁路图做**宏观走廊级**视觉校验，输出不确定项清单 | `docs/railway_map_visual_audit_2025.md` |

**最终数据层状态（v2.2）**：
- 253 条线路 / 1530 个车站 / 330 个城市 / 1528 个图节点
- **192/192 枢纽站 100% 可解析**
- 27/27 测试通过（零回归）

---

## 2. 两个「致命坑」（新对话做数据层改动前必读）

1. **Dijkstra 只走「属于某条线」的边**
   `railway_data.py` 里 `_EDGE_LINES` 由 `LINE_ORDER` 派生；任何**裸 GRAPH 边**（没挂到线路上）对 Dijkstra 不可见。
   所以接入新城市/新线路时，**必须用「线路」形式**（哪怕是合成联络线），不能只往 `GRAPH` 加裸边。
   反例：曾直接加 `济南站—济南西站` 裸边，结果 BFS 通、Dijkstra 不通。

2. **再生成 `railway_data.py` 时，tail（helper 块）必须按「内容标记」截取，不能用行号**
   曾经用 `orig_all[13:]`（第 14 行起）截 helper，结果把文件中段的 `CITY_ALIAS/PROVINCE_TO_STATIONS/GRAPH`
   也当 tail 拷入，造成**文件里重复的 `GRAPH =`**——Python 加载时尾部陈旧 GRAPH 覆盖了正文新 GRAPH，
   表现为「LINE_ORDER 和 JSON 都有新站，但模块 GRAPH 没有，连通性全 FAIL」。
   **正确做法**：用 `LINE_NAME_ALIAS` / `def resolve_location` 作为 helper 起点定位，不要用行号。

---

## 3. 新对话上手清单（按这个顺序读）

1. **先读本包 `PROJECT_SUMMARY.md`** —— 项目定位、数据层规模、核心模块、算法设计、已知坑、SOP、TODO 一览。
2. **读 `src/student_ticket_checker.py`** —— 引擎：`resolve_location`/`_dijkstra`/`find_path_via_hubs`/`check_compliance`/`HUB_ALIAS`。
3. **读 `src/railway_data.py`** —— 数据层（`LINE_ORDER`/`STATION_INFO`/`CITY_TO_STATIONS`/`GRAPH`/`resolve_location`）。
4. **需要补某省数据时** —— 读 `skill/railway-data-province-merge/SKILL.md`，照 SOP 写 merge 脚本（见本包 `merge_*.py` 范例）。
5. **改完跑回归** —— `python -u src/student_ticket_checker.py --test`（27 条用例，必须全绿）。
6. **地图宏观校验** —— 参考 `docs/railway_map_visual_audit_2025.md` 的不确定项清单，逐项用分省 Excel/时刻表确认，不要直接按图写 `LINE_ORDER`。

---

## 4. 本包文件清单（含来源说明）

| 包内路径 | 来源 | 说明 |
|---|---|---|
| `README_新对话交接.md` | 本次新增 | 就是本文件 |
| `PROJECT_SUMMARY.md` | 本次新增 | 项目总览（最该先读） |
| `docs/railway_map_visual_audit_2025.md` | 本次新增 | 全国铁路图视觉审计 |
| `src/student_ticket_checker.py` | 继承+微调 | 合规引擎（功能开发主战场） |
| `src/railway_data.py` | 本次再生(v2.2) | 数据层（权威拓扑源） |
| `src/test_cases.py` | 继承 | 27 条测试用例 |
| `merge_shandong_qinghai.py` | 本次新增 | 山东/青海增量合并范例（项目根目录） |
| `merge_remaining_8_cities.py` | 本次新增 | 冀黑湘苏津 8 城合并范例（项目根目录） |
| `data/lines_order.json` | 本次同步 | 线路→有序车站 |
| `data/graph_adjacency.json` | 本次同步 | 邻接表 |
| `data/station_info.json` | 本次同步 | 车站→省份/城市/线路 |
| `data/city_to_stations.json` | 本次同步 | 城市→车站集 |
| `data/hub_stations.json` | 输入(继承) | 192 枢纽站清单 |
| `context/project_context_summary.md` | 本次更新 | 项目纪要 |
| `skill/railway-data-province-merge/SKILL.md` | 本次新增 | 分省合并可复用技能 |

> 注：原始 Excel 输入、全国铁路图图片、`web/` 演示前端、`*.bak` 备份未入包（属输入或可从磁盘取），
> 如新对话需要可在原项目目录读取。

---

## 5. 给新对话的「铁律」（改动数据层前默许遵守）

1. **增量只加不删**：合并省份数据时 `to_add = merged_edges - original_edges`，绝不删除旧边/旧站。
2. **Dijkstra 只走有线边**：新连接必须以「线路」形式存在（含合成联络线），禁止只加裸 GRAPH 边。
3. **再生 `railway_data.py` 按内容标记截取 tail**，不要用行号。
4. **每次数据层改动后必须跑 `python -u src/student_ticket_checker.py --test`**，27 条用例全绿才交付。
5. **枢纽解析必须 100%**：`data/hub_stations.json` 中 192 站全部能被 `HUB_ALIAS` 解析，否则功能不完整。

---

## 6. 已知 TODO（可交给新对话的下一步）

- [ ] 安装 FastAPI/uvicorn 跑通 `web_app`（沙箱未装依赖，引擎本身 import 正常）。
- [ ] 继续补全国其他省份线路数据（若有新 Excel），按 `railway-data-province-merge` SOP。
- [ ] 按地图审计报告的不确定项清单，用分省 Excel/时刻表逐一验证后写入数据层。
- [ ] 功能扩展：多区间联程的最优化建议、候补/中转时间约束、优惠区间自动推荐等。

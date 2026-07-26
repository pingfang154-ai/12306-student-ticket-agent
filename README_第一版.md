# 🚄 学生票 Agent — 优惠区间合规检查器

> 基于铁路拓扑网络，自动判断购票区间是否符合学生优惠区间（学校↔家庭所在地）的合理径路，并提供反向购票识别、途经段检查、家庭修改建议等功能。

---

## 目录结构

```
student_ticket_agent_handover/
├── README.md                          # 本文档
├── requirements.txt                   # Python 依赖清单
├── data/                              # 全量数据资产
│   ├── lines_order.json               # 线路车站顺序（核心拓扑）
│   ├── city_to_stations.json          # 同城车站映射
│   ├── graph_adjacency.json           # 图邻接表
│   ├── station_info.json              # 车站属性（省份/城市/线路）
│   ├── city_aliases.json              # 城市别名映射（309 条目）
│   ├── station_aliases.json           # 站名别名映射
│   ├── railway_data.json              # 数据层 JSON 备份
│   └── student_rules.json             # 规则配置 + 10 案例库
├── src/                               # Python 源代码
│   ├── web_app.py                     # FastAPI Web 入口
│   ├── student_ticket_checker.py      # 合规判断引擎
│   ├── railway_data.py                # 数据层（图 + 同城解析）
│   ├── test_cases.py                  # 18 个自动化测试用例
│   └── build_v2.py                    # 从 Excel 源构建数据的流水线
├── web/                               # Web 前端资源
│   ├── templates/
│   │   ├── index.html                 # 主页面（ECharts 可视化）
│   │   └── cases.html                 # 案例库页面
│   └── static/
│       └── style.css                  # 样式文件（响应式）
├── docs/                              # 项目文档
│   ├── data_quality_report.md         # 数据质量报告
│   ├── student_rules_analysis.md      # 规则学习报告
│   ├── broken_endpoints_review.md     # 断头端点分析
│   └── deployment_guide.md            # 部署指南
└── context/                           # 上下文摘要（供智能体快速恢复）
    └── project_context_summary.md     # 项目背景 + 已完工作 + 待办
```

---

## 环境要求

| 项目 | 要求 |
|------|------|
| Python | ≥ 3.9 |
| 操作系统 | Linux / macOS / Windows |
| 内存 | ≥ 512 MB |

---

## 快速启动

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 启动 Web 服务（项目根目录）
python -m uvicorn src.web_app:app --host 0.0.0.0 --port 8080

# 3. 访问页面
#    http://localhost:8080/       ← 主页面
#    http://localhost:8080/cases  ← 案例库
```

---

## 命令行使用

```bash
# 交互式输入
python -m src.student_ticket_checker

# 批量运行测试
python -m src.student_ticket_checker --test

# 或直接运行
python -m src.test_cases
```

---

## API 接口

### POST /api/check
```bash
curl -X POST "http://localhost:8080/api/check" \
  -d "school=武汉&home=大理&dep=武汉&arr=大理&seat=二等座"
```

### GET /api/stations
```bash
curl "http://localhost:8080/api/stations"
```

---

## 关键配置说明

- **数据路径**：所有数据文件路径均已自动适配，无需手动配置
- **端口**：默认 8080，可通过 `--port` 参数修改
- **规则文件**：`data/student_rules.json` 包含规则定义和案例库，可直接编辑

---

## 测试方法

### 运行全部测试
```bash
python -m src.test_cases
```

### 快速验证单个场景
```bash
python -c "
from src.student_ticket_checker import check_student_ticket
r = check_student_ticket('武汉', '大理', '武汉', '大理', seat='二等座')
print('✅ 合规' if r['result']['ok'] else '❌ 不合规')
print(r['result']['reason'])
"
```

### 已知测试场景

| 场景 | 学校 | 家庭 | 出发 | 到达 | 预期结果 |
|------|------|------|------|------|---------|
| 标准合规 | 成都 | 北京 | 成都东 | 北京西 | ✅ 合规 |
| 反向合规 | 成都 | 北京 | 北京西 | 成都东 | ✅ 反向合规 |
| 超区间 | 邢台 | 石家庄 | 邢台 | 北京 | ❌ 不合规 |
| 多径路 | 武汉 | 大理 | 武汉 | 大理 | ✅ 合规 |

---

## 常见问题 (FAQ)

### Q: 输入城市名还是站名？
**A**: 两者均可。输入"成都"会自动展开为成都市所有车站；输入"成都东"会定位到该站并关联到所在城市。

### Q: 支持多段行程检查吗？
**A**: 支持。在页面中添加途经站（点击「+ 添加途经站」），引擎会逐段检查每个区间。

### Q: 家庭所在地可以修改吗？
**A**: 可以。在页面中展开「已修改家庭所在地？」折叠面板，输入新家庭城市即可。修改后有 24 小时冷却期。

### Q: 学生票可以买商务座吗？
**A**: 不可以。学生票仅限：硬座、硬卧、二等座、二等包座、多功能座、一等座、动车组卧铺。

### Q: 联程（换乘）怎么扣次数？
**A**: 各段开车时间间隔 ≤ 5 个自然日，扣减 1 次优惠次数。如已被多扣，可在 12306 App 中申诉合并。

---

## 框架说明

本项目使用 **FastAPI**（Python 异步 Web 框架）+ **Jinja2**（模板引擎）+ **ECharts**（前端可视化图表库），均为开源组件。

## 关于 Author

学生票 Agent 项目 — 基于 12306 规则与铁路拓扑网络的智能合规检查工具。

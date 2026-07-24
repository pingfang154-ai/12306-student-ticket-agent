# 部署指南

## 环境要求

| 项目 | 要求 |
|------|------|
| Python | ≥ 3.9 |
| 操作系统 | Linux / macOS / Windows |
| 内存 | ≥ 512 MB |
| 磁盘 | ≥ 100 MB |

## 快速启动

```bash
# 1. 解压项目
unzip student_ticket_agent_handover_*.zip -d student_ticket_agent_handover
cd student_ticket_agent_handover

# 2. 安装依赖
pip install -r requirements.txt

# 3. 启动 Web 服务
python -m uvicorn src.web_app:app --host 0.0.0.0 --port 8080
```

或者从 `src/` 目录启动：

```bash
cd src
python -m uvicorn web_app:app --host 0.0.0.0 --port 8080
```

## 验证部署

启动后打开浏览器访问：
- **主页**：`http://localhost:8080/`
- **案例库**：`http://localhost:8080/cases`
- **API 接口**：`http://localhost:8080/api/stations`

## 目录结构说明

```
project_root/
├── src/           # Python 源代码
│   ├── web_app.py               # FastAPI Web 入口
│   ├── student_ticket_checker.py # 合规判断引擎
│   ├── railway_data.py          # 数据层（图 + 同城解析）
│   ├── test_cases.py            # 自动化测试
│   └── build_v2.py              # 数据构建脚本（高级）
├── web/           # Web 前端资源
│   ├── templates/               # Jinja2 模板
│   └── static/                  # CSS 静态文件
├── data/          # 数据资产
│   ├── lines_order.json         # 线路车站顺序（核心拓扑）
│   ├── city_to_stations.json    # 同城车站映射
│   ├── graph_adjacency.json     # 图邻接表
│   ├── station_info.json        # 车站属性
│   ├── city_aliases.json        # 城市别名
│   ├── station_aliases.json     # 站名别名
│   └── student_rules.json       # 规则 + 案例库
├── docs/          # 项目文档
├── context/       # 智能体上下文
└── requirements.txt
```

## 端口配置

如需修改端口，启动命令：
```bash
python -m uvicorn src.web_app:app --host 0.0.0.0 --port <YOUR_PORT>
```

## 环境变量

暂无需要配置的环境变量。所有路径均自动适配。

## 常见部署问题

### 1. ModuleNotFoundError: No module named 'src'
确保在项目根目录（而非 `src/` 内部）执行 `uvicorn src.web_app:app`。

### 2. student_rules.json 找不到
如果以 `src/` 为工作目录启动，程序会自动查找 `../data/student_rules.json`。

### 3. 端口被占用
使用 `lsof -i :8080` 查看占用进程，或更换端口号。

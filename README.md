# 模切流程系统 (Die-Cutting Process System)

首版定位：**非ERP**，聚焦模切制造核心流程（采购→库存→工程→MRP→生产→质量→成本→统计）。

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | Vue 3 + TypeScript + Vite + Element Plus + Pinia + Vue Router |
| 后端 | FastAPI + SQLAlchemy 2 (async) + Pydantic v2 |
| 数据库 | SQLite（首版） / 预留 PostgreSQL 迁移 |
| 迁移 | Alembic |
| 其他 | openpyxl（Excel）、pytest |

## 项目结构

```
die-cutting-system/
├── backend/                 # FastAPI 后端
│   ├── app/
│   │   ├── api/             # 路由
│   │   ├── core/            # 配置、数据库
│   │   ├── models/          # SQLAlchemy 模型
│   │   ├── schemas/         # Pydantic 模型
│   │   ├── services/        # 业务服务
│   │   └── main.py
│   ├── alembic/             # 数据库迁移
│   ├── data/                # SQLite 数据文件
│   └── requirements.txt
├── frontend/                # Vue3 前端
├── docs/                    # 文档
└── scripts/                 # 运维脚本
```

## 快速启动

### 后端

```bash
cd backend
# 建议使用虚拟环境
pip install -r requirements.txt
cp .env.example .env
# 数据库已初始化（或执行 alembic upgrade head）
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

访问：
- API 文档：http://localhost:8000/docs
- 健康检查：http://localhost:8000/api/v1/health

### 前端

```bash
cd frontend
npm install
npm run dev
```

访问：http://localhost:5173

## 开发阶段（对应清单）

| 阶段 | 名称 | 状态 |
|------|------|------|
| 0 | 技术底座 | ✅ 进行中 |
| 1 | 采购库存核心 | 待开始 |
| 2 | 模切工程 | 待开始 |
| 3 | MRP计划 | 待开始 |
| 4 | 完整生产 | 待开始 |
| 5 | 质量成本追溯 | 待开始 |
| 6 | 统计Excel | 待开始 |
| 7 | 稳定化 | 待开始 |

## 核心原则

1. **库存唯一事实源**：所有库存变化只能通过 `stock_ledger` 产生
2. **历史不可覆盖**：正式单据/流水不直接删除或修改，错误采用冲销
3. **版本冻结**：工单锁定产品/BOM/工艺/排版版本
4. **理论与实际分离**：BOM理论耗用、实际领料、实际产出分别记录
5. **来源可追溯**：每笔数据保留 `source_type` / `source_id`
6. **事务原子性**：业务单据状态与库存流水必须同事务提交

## 当前进度

### 阶段0 技术底座
- [x] 项目目录骨架
- [x] FastAPI 应用 + 健康检查
- [x] 统一 API 响应/错误模型
- [x] SQLAlchemy + Alembic 基础
- [x] 审计日志模型
- [x] 业务单据编号服务
- [x] Vue3 前端脚手架 + 健康检查页
- [x] Git 规范文档
- [x] 环境配置与密钥管理

### 阶段1 采购库存核心（已完成）
- [x] 基础数据模型：物料、供应商、客户、仓库、库位、单位、原因码
- [x] 库存余额模型 stock_balances
- [x] 库存流水模型 stock_ledgers（append-only）
- [x] InventoryService 统一入库/出库/转移/冲销（唯一入口）
- [x] 负库存拦截
- [x] 基础数据 CRUD API
- [x] 库存 API（/in /out /transfer /ledgers /balances）
- [x] 采购申请 / 订单 / 到货 / IQC 模型与服务
- [x] 采购 API（/purchase/requests|orders|arrivals|iqc）
- [x] IQC 合格自动入库（stock_ledger PURCHASE_IN）
- [x] 采购退货（确认后 PURCHASE_RETURN 出库）
- [x] 采购价格历史（订单确认时自动记录）
- [x] 阶段1闭环演示脚本 scripts/demo_phase1_flow.md
- [x] 库存服务单元测试骨架 tests/test_inventory_service.py
- [x] 前端布局 + hash 路由（无额外依赖）
- [x] 前端页面：总览 / 物料 / 供应商 / 仓库 / 库存余额 / 流水 / 采购订单 / 到货IQC



### 阶段2 模切工程（已完成）
- [x] 产品档案 / 产品版本（版本冻结）
- [x] BOM 主表+明细（损耗/替代料）
- [x] 工艺路线 + 模切工序类型
- [x] 模具档案 + 寿命累计
- [x] 排版版本 + 利用率计算
- [x] 工程 API + 前端产品页
- [ ] 多级 BOM 展开



### 阶段3 MRP计划（已完成）
- [x] 销售订单
- [x] 多级 BOM 展开（含损耗）
- [x] 可用库存 / 在途采购扣减
- [x] 净需求 + 采购/生产建议
- [x] MRP 运行可追溯
- [x] 前端销售订单/MRP页



### 阶段4 完整生产（已完成）
- [x] 生产工单（锁定产品版本/BOM/工艺）
- [x] 物料需求展开 + 领料/退料（库存流水）
- [x] 工序报工（良品/不良/报废）
- [x] 成品入库 + 工单完工
- [x] 模具寿命累计
- [x] 前端生产工单页



### 阶段5 质量成本追溯（已完成）
- [x] 缺陷字典 / IPQC / FQC
- [x] 质量异常单 + 处置（返工/报废/让步）
- [x] 正向追溯（物料/批次 → 流水/工单）
- [x] 反向追溯（工单/入库 → 领料/IQC）
- [x] 标准成本 + 工单实际成本归集
- [x] 前端质量/追溯/成本页



### 阶段6 统计Excel（已完成）
- [x] 统一指标引擎（采购入库/领料/生产入库/IQC合格率等）
- [x] 日报 + 自定义区间报表
- [x] Excel 导出（日报 / 库存流水）
- [x] 前端统计报表页

### 阶段7 稳定化（已完成核心）
- [x] SQLite 备份脚本 scripts/backup_db.sh
- [x] 库存守恒校验 scripts/check_stock_consistency.py
- [x] 期间锁定 API /periods/lock|unlock
- [x] 全链路测试 tests/test_full_chain.py
- [x] PostgreSQL 迁移说明 docs/postgresql-migration.md

---

*根据《模切流程系统-初版开发清单》启动*


## 演示数据

```bash
cd backend
python scripts/seed_demo_data.py
```

写入原料库存、已发布产品版本（BOM+工艺）、标准成本，可直接跑 MRP / 工单。

## 优化项（持续）

- 库存写入自动校验期间锁定
- 开发环境启动自动 `create_all`
- 首页展示今日指标与推荐操作路径


## Docker 一键启动

```bash
cd die-cutting-system
docker compose up --build
```

- 后端 http://localhost:8000/docs  
- 前端 http://localhost:5173  

首次进入后可在后端容器执行：

```bash
docker compose exec backend python scripts/seed_demo_data.py
```

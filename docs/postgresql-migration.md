# PostgreSQL 迁移说明

首版默认 SQLite，代码层使用 SQLAlchemy 异步引擎，切换 PostgreSQL 只需改连接串与驱动。

## 1. 安装依赖

```bash
pip install asyncpg
# requirements 可增加：
# asyncpg==0.30.0
```

## 2. 修改环境变量

`.env`：

```env
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/die_cutting
```

## 3. 建库

```bash
createdb die_cutting
# 或 SQL: CREATE DATABASE die_cutting;
```

## 4. 迁移

推荐使用 Alembic（项目已含 alembic 配置）：

```bash
cd backend
# 确保 app.models 全部导入后
alembic revision --autogenerate -m "full_schema"
alembic upgrade head
```

若 Alembic 在异步环境下有问题，可先用 `scripts/init_phase1_tables.sql` 的结构作参考，在 PG 中执行等价 DDL（注意：SQLite 的 `AUTOINCREMENT` / `BOOLEAN` 在 PG 中为 `SERIAL` / `BOOLEAN`）。

## 5. 差异注意点

| 点 | SQLite | PostgreSQL |
|----|--------|------------|
| 布尔 | INTEGER 0/1 | BOOLEAN |
| 自增 | INTEGER AUTOINCREMENT | SERIAL / IDENTITY |
| JSON | JSON 文本 | JSONB 可用 |
| 并发写 | 文件锁 | 行锁，适合多用户 |

## 6. 代码兼容性

- 模型未使用 SQLite 专有类型
- 连接通过 `DATABASE_URL` 注入
- 切换后重启 uvicorn 即可

## 7. 建议上线顺序

1. 本地 PG 跑通迁移与全链路测试  
2. 备份 SQLite，导出关键主数据  
3. 导入 PG，校验 `check_stock_consistency` 逻辑（可改写为 asyncpg 版本）  
4. 切换 `DATABASE_URL` 并观察健康检查 `/api/v1/health`

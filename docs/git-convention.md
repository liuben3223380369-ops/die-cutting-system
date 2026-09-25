# Git 分支 / Commit / Issue 规范

## 分支策略

| 分支 | 用途 | 保护 |
|------|------|------|
| `main` | 稳定可发布版本 | 禁止直接 push |
| `develop` | 日常集成分支 | 推荐 PR 合并 |
| `feature/xxx` | 功能开发 | 从 develop 拉出 |
| `fix/xxx` | 缺陷修复 | 从 develop 或 main 拉出 |
| `hotfix/xxx` | 紧急线上修复 | 从 main 拉出 |

命名示例：
- `feature/D013-customer-master`
- `feature/inventory-ledger`
- `fix/negative-stock-check`

## Commit Message 规范

格式：`<type>(<scope>): <subject>`

**type**：
- `feat`：新功能
- `fix`：缺陷修复
- `docs`：文档
- `style`：格式（不影响逻辑）
- `refactor`：重构
- `test`：测试
- `chore`：构建/工具

**scope** 示例：`inventory`, `purchase`, `bom`, `api`, `ui`

示例：
```
feat(inventory): 实现统一入库服务与 stock_ledger
fix(mrp): 修复在途采购扣减逻辑
docs: 更新阶段0完成标志
```

## Issue 规范

标题：`[模块] 简要描述`

标签建议：
- `P0` / `P1`
- `阶段0` ~ `阶段7`
- `bug` / `enhancement` / `tech-debt`
- `inventory` / `production` / ...

描述模板：
```
## 背景
## 目标
## 验收标准
## 相关清单ID（如 D049）
```

# study-ingest Skill 使用指南

## 快速开始

### 1. 安装依赖

```bash
pip install neo4j pyyaml
```

### 2. 配置 Neo4j

编辑 `config.yaml`，设置你的 Neo4j 连接信息：

```yaml
neo4j:
  uri: bolt://your-neo4j-host:7687
  user: neo4j
  password: your_password
```

或使用环境变量：

```bash
export NEO4J_PASSWORD=your_password
```

### 3. 在 OpenClaw 中调用

```python
# 方式一：直接调用
from study-ingest.ingest import run_skill

result = await run_skill({
    "action": "ingest",
    "concept": "Transformer",
    "content": "今天学了 Transformer，它依赖自注意力机制",
    "user_id": "your_user_id"
})

# 方式二：通过 OpenClaw Skill 系统
# 在 OpenClaw 对话中输入：
学习 Transformer
```

## 支持的 Action

### `ingest` - 学习新概念

```json
{
    "action": "ingest",
    "concept": "概念名称",
    "content": "可选的初始内容",
    "user_id": "用户标识"
}
```

### `resume` - 恢复上次学习

```json
{
    "action": "resume",
    "user_id": "用户标识"
}
```

### `import` - 导入文件

```json
{
    "action": "import",
    "file_path": "/path/to/file.md",
    "user_id": "用户标识"
}
```

## 输出示例

```json
{
    "status": "success",
    "concept": "Transformer",
    "knowledge_tree": {
        "concept": "Transformer",
        "children": [...]
    },
    "sensitive_info_found": 0,
    "next_step": "开始费曼学习法：请用 3 句话解释核心定义"
}
```

## 敏感信息检测

自动检测并脱敏以下类型：

- API Keys (`sk-xxx`, `ghp_xxx`, `AKIAxxx`)
- 数据库密码
- 邮箱、手机号
- 本地绝对路径

## 断点续传

每次学习后自动保存进度，下次调用 `resume` action 即可继续。

## 下一步开发

- [ ] 集成 OpenClaw LLM 调用实现 AI 知识补全
- [ ] 完善文件导入功能（支持 Markdown/PDF/代码文件）
- [ ] 添加 GitHub 自动发布功能
- [ ] 与 `study-review` Skill 对接

## 故障排查

### Neo4j 连接失败

检查 Neo4j 服务是否运行：

```bash
neo4j status
```

### SQLite 锁死

删除数据库文件重建：

```bash
rm study_engine.db
```

### 敏感信息误检

在 `config.yaml` 中调整正则规则。

### 整体模块解耦架构图

- [ ]  Ingest Orchestrator (ingest.py): 业务总调度，负责接收用户指令并协调各模块工作。

- [ ]  LLM Processor: 处理敏感信息脱敏（8种规则）及根据不同学科（Subject）生成补全 Prompt。

- [ ]  Graph Service: 专门负责 Neo4j 操作，支持多用户标签隔离（如 :User_Adam）。

- [ ]  DB Manager: 负责 SQLite 操作，采用标准 SQL 以兼容未来向 MySQL 的迁移。


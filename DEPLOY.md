# 部署说明

## 版本锁定
当前所有依赖版本已锁定在 `requirements.txt` 中，保证部署环境和开发环境完全一致。

## 部署方式

### 1. 环境准备
- 安装 Docker 和 Docker Compose
- 复制 `.env.example` 为 `.env` 并填写实际的 API Key

### 2. 启动服务
```bash
# 构建并启动容器
docker-compose up -d --build

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

### 3. 访问服务
API 服务默认运行在 `http://localhost:8000`

### 4. 测试服务
```bash
# 健康检查
curl http://localhost:8000/health

# 处理样本
curl -X POST http://localhost:8000/process \
  -H "Content-Type: application/json" \
  -d '{"sample_id": "CD888888"}'
```

## 其他命令
```bash
# 运行测试
docker-compose run --rm digitalme python -m pytest tests/ -v

# 进入容器 shell
docker-compose exec digitalme bash

# 提取样本数据
docker-compose run --rm digitalme python skills/extract_data_v1.py SAMPLE_ID
```
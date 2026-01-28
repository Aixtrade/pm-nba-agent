# Docker 部署指南

本文档说明如何使用 Docker 和 Docker Compose 部署 PM NBA Agent 应用。

## 前置要求

- Docker Engine 20.10+
- Docker Compose V2+

## 快速开始

### 1. 配置环境变量

复制示例配置文件并修改配置：

```bash
cp .env.example .env
```

编辑 `.env` 文件，填入你的配置：

```env
# OpenAI API 配置
OPENAI_API_KEY=sk-your-api-key-here
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o-mini

# AI 分析间隔配置（秒）
ANALYSIS_INTERVAL=30
ANALYSIS_EVENT_INTERVAL=15

# 登录口令与 Token 派生盐
LOGIN_PASSPHRASE=your-secure-passphrase
LOGIN_TOKEN_SALT=your-secure-salt
```

### 2. 构建和启动服务

```bash
# 构建并启动所有服务
docker compose up -d

# 查看日志
docker compose logs -f

# 查看特定服务日志
docker compose logs -f backend
docker compose logs -f frontend
```

### 3. 访问应用

- 前端界面: http://localhost
- 后端 API 文档: http://localhost/api/docs
- 后端健康检查: http://localhost/health

### 4. 停止服务

```bash
# 停止所有服务
docker compose down

# 停止并删除数据卷
docker compose down -v
```

## 架构说明

### 服务组成

1. **backend** - FastAPI 后端服务
   - 端口: 8000 (容器内部)
   - 功能: NBA 数据获取、AI 分析、SSE 流式推送
   - 健康检查: http://backend:8000/health

2. **frontend** - Nginx + Vue3 前端服务
   - 端口: 80 (宿主机映射)
   - 功能: 用户界面、反向代理
   - 静态资源服务 + API 代理

### 网络配置

- 容器网络: `nba-network` (bridge 模式)
- 前端通过 nginx 反向代理访问后端
- 后端服务不直接暴露到宿主机

### 环境变量

后端容器会自动加载项目根目录的 `.env` 文件，包含：

- OpenAI API 配置
- AI 分析参数
- 身份验证配置

⚠️ **安全提示**: 不要将 `.env` 文件提交到 Git 仓库。

## 开发模式

如果需要在开发模式下运行（支持热重载）：

```bash
# 仅启动后端容器
docker compose up backend -d

# 本地运行前端开发服务器
cd frontend
npm install
npm run dev
```

前端开发服务器会在 http://localhost:3000 运行，并自动代理 API 请求到 Docker 中的后端。

## 自定义配置

### 修改端口

编辑 `docker-compose.yml`，修改前端端口映射：

```yaml
services:
  frontend:
    ports:
      - "8080:80"  # 将宿主机端口改为 8080
```

### 修改 Nginx 配置

编辑 `nginx.conf` 文件，然后重新构建前端镜像：

```bash
docker compose build frontend
docker compose up -d frontend
```

### 添加环境变量

在 `.env` 文件中添加新的环境变量，然后重启后端服务：

```bash
docker compose restart backend
```

## 故障排查

### 查看容器状态

```bash
docker compose ps
```

### 查看容器日志

```bash
# 所有服务日志
docker compose logs

# 实时日志
docker compose logs -f

# 最近 100 行日志
docker compose logs --tail=100
```

### 进入容器调试

```bash
# 进入后端容器
docker compose exec backend /bin/bash

# 进入前端容器
docker compose exec frontend /bin/sh
```

### 健康检查失败

如果后端健康检查失败：

```bash
# 查看后端日志
docker compose logs backend

# 手动测试健康检查
docker compose exec backend curl http://localhost:8000/health
```

### 前端无法访问后端

1. 检查网络连接：
   ```bash
   docker compose exec frontend ping backend
   ```

2. 检查 nginx 配置：
   ```bash
   docker compose exec frontend cat /etc/nginx/conf.d/default.conf
   ```

3. 检查 nginx 日志：
   ```bash
   docker compose exec frontend cat /var/log/nginx/error.log
   ```

## 生产部署建议

### 1. 使用环境变量管理敏感信息

不要在镜像中硬编码敏感信息，使用 Docker secrets 或外部密钥管理系统。

### 2. 启用 HTTPS

使用 Let's Encrypt 证书，修改 nginx 配置启用 HTTPS：

```nginx
server {
    listen 443 ssl http2;
    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;
    # ... 其他配置
}
```

### 3. 配置日志轮转

添加 Docker 日志驱动配置：

```yaml
services:
  backend:
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

### 4. 资源限制

为容器设置资源限制：

```yaml
services:
  backend:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '0.5'
          memory: 512M
```

### 5. 健康检查

确保健康检查配置正确，Docker Compose 会自动重启不健康的容器。

### 6. 备份策略

定期备份 `.env` 文件和重要数据。

## 清理资源

```bash
# 停止并删除容器、网络
docker compose down

# 删除所有构建缓存
docker builder prune -a

# 删除未使用的镜像
docker image prune -a
```

## 更新应用

```bash
# 拉取最新代码
git pull

# 重新构建并启动
docker compose up -d --build
```

## 技术栈

- **后端**: Python 3.12, FastAPI, uv
- **前端**: Node.js 20, Vue 3, Vite, TailwindCSS, DaisyUI
- **反向代理**: Nginx (Alpine)
- **容器编排**: Docker Compose

## 许可证

MIT License - 详见 [LICENSE](./LICENSE) 文件。

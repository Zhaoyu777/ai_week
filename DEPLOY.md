# GitHub 与 Docker 部署说明

## 1. 上传到 GitHub

在项目根目录执行：

```bash
git init
git add .
git commit -m "init: docker deployment"
git branch -M main
git remote add origin https://github.com/<your-account>/<your-repo>.git
git push -u origin main
```

注意：

- `.env`、`data/`、`backups/`、`runtime/` 已加入忽略规则，不会被提交。
- 如果你本地 `.env` 里已经放过真实 API Key，不要提交该文件；如果 Key 曾经泄露，先去供应商控制台轮换。

## 2. 阿里云 ECS 准备

推荐环境：

- Ubuntu 22.04 LTS
- 已安装 Docker Engine 与 Docker Compose plugin
- 安全组放行你的应用端口，例如 `5100`

## 3. 服务器部署

首次部署：

```bash
git clone https://github.com/<your-account>/<your-repo>.git
cd <your-repo>
chmod +x deploy.sh
./deploy.sh
```

第一次执行会自动生成 `runtime/.env`，你需要填写真实配置，再执行一次：

```bash
vi runtime/.env
./deploy.sh
```

## 4. 运行目录说明

- `runtime/.env`：生产环境配置，页面里的 AI 配置会写回这个文件
- `data/`：业务数据
- `backups/`：备份数据

## 5. 常用命令

查看容器状态：

```bash
docker compose ps
```

查看日志：

```bash
docker compose logs -f ai-week
```

更新代码并重启：

```bash
git pull --ff-only
./deploy.sh
```

## 6. 反向代理建议

如果你要绑定域名，建议在 ECS 上再加一层 Nginx，把 `80/443` 反代到 `127.0.0.1:5100`。

## 7. 当前方案边界

当前项目使用本地 JSON 文件存储数据，适合单机部署。

- Docker 已默认使用单进程 Gunicorn，避免多进程同时写 JSON 导致数据冲突。
- 如果后续要多实例部署、自动扩缩容或更高并发，建议迁移到 MySQL/PostgreSQL。

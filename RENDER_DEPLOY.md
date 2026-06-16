# 部署到 Vercel + Render（免费）

## 架构

```
用户浏览器 → Vercel(前端静态页面) → Render(后端API) → 新浪财经
```

## 第一步：部署后端到 Render

1. 访问 https://dashboard.render.com
2. 点击 "New +" → "Web Service"
3. 连接您的 GitHub 仓库
4. 配置：
   - **Name**: `a-stock-trading-backend`
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python main.py`
   - **Root Directory**: `backend`
5. 点击 "Create Web Service"
6. 等待部署完成，记下 URL（如 `https://a-stock-trading-backend.onrender.com`）

## 第二步：部署前端到 Vercel

1. 访问 https://vercel.com
2. 点击 "Add New Project"
3. 导入同一个 GitHub 仓库
4. 配置：
   - **Framework Preset**: `Other`
   - **Build Command**: 留空（前端已预构建）
   - **Output Directory**: `frontend/dist`
5. 点击 "Deploy"
6. 部署完成后，进入项目设置 → Environment Variables
7. 添加环境变量（如果需要修改后端地址）：
   - `VITE_API_URL`: `https://a-stock-trading-backend.onrender.com`

## 第三步：更新后端 CORS

在 Render 的后端服务中，添加环境变量：
- `CORS_ORIGINS`: `https://你的vercel域名.vercel.app`

## 完成

访问 Vercel 提供的域名即可使用系统！

## 后续升级

1. 修改代码
2. `git add . && git commit -m "update" && git push`
3. Render 和 Vercel 会自动重新部署
4. 刷新页面即可看到更新

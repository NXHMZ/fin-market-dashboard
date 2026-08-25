# GitHub Pages 部署指南

## 前置条件
- GitHub 账号（https://github.com 注册）
- Git 已安装（https://git-scm.com 下载）

## 部署步骤

### 1. 创建 GitHub 仓库
1. 登录 GitHub，点击右上角 + → New repository
2. 仓库名填：fin-market-dashboard
3. 选择 Public（必须公开才能免费使用 Pages）
4. 勾选 Add a README file
5. 点击 Create repository

### 2. 上传项目代码
打开终端（CMD 或 PowerShell），执行：

```bash
# 进入项目目录
cd "你的项目路径\fin_market_aggregator"

# 初始化 Git 仓库
git init
git branch -M main

# 添加远程仓库（替换 YOUR_USERNAME 为你的 GitHub 用户名）
git remote add origin https://github.com/YOUR_USERNAME/fin-market-dashboard.git

# 添加所有文件
git add .
git commit -m "初始化金融市场信息聚合系统"

# 推送到 GitHub
git push -u origin main
```

### 3. 启用 GitHub Pages
1. 在仓库页面点击 Settings
2. 左侧菜单选 Pages
3. Source 选择 GitHub Actions
4. 保存

### 4. 等待自动部署
- 推送代码后，GitHub Actions 会自动运行
- 点击仓库页面顶部 Actions 标签查看运行状态
- 首次部署约 2-3 分钟完成

### 5. 访问网站
部署完成后，访问：
```
https://YOUR_USERNAME.github.io/fin-market-dashboard/
```
此网址可在任何设备（手机、平板、其他电脑）上打开，
不依赖你的电脑开关机。

## 自动刷新
- GitHub Actions 每 30 分钟自动运行一次采集
- 页面内容自动更新，无需手动操作

## 手动触发
在 Actions 页面可点击 Run workflow 手动触发一次采集。

# 阿里云轻量服务器部署指南

## 一、购买服务器

1. 访问 https://www.aliyun.com/product/swas
2. 选择 **轻量应用服务器**
3. 配置选择：
   - 地域：离你最近的城市
   - 镜像：Ubuntu 22.04
   - 套餐：最低配置即可（2核2G，约24元/月）
4. 购买后记住：
   - **公网IP**（如 47.xx.xx.xx）
   - **root密码**（购买时设置的）

## 二、连接服务器

### Windows 连接方式
1. 按 Win+R，输入 `cmd`，回车
2. 执行：
```bash
ssh root@你的公网IP
```
3. 输入密码，看到 `root@xxx:~#` 表示连接成功

## 三、安装环境（在服务器上执行）

复制以下命令，逐行粘贴执行：

### 1. 更新系统
```bash
apt update && apt upgrade -y
```

### 2. 安装 Python 和依赖
```bash
apt install -y python3 python3-pip python3-venv git
```

### 3. 创建项目目录
```bash
mkdir -p /opt/fin-dashboard
cd /opt/fin-dashboard
```

### 4. 创建虚拟环境
```bash
python3 -m venv venv
source venv/bin/activate
```

### 5. 安装 Python 依赖
```bash
pip install flask requests beautifulsoup4 lxml
```

## 四、上传项目代码

### 方式 A：从 GitHub 拉取（推荐）
```bash
cd /opt/fin-dashboard
git clone https://github.com/NXHMZ/fin-market-dashboard.git temp
cp temp/* . -r
cp temp/.gitignore . 2>/dev/null
rm -rf temp
```

### 方式 B：从本地上传
在本地 PowerShell 执行（替换 IP）：
```bash
scp -r "C:\Users\80909\AppData\Roaming\TRAE SOLO CN\ModularData\ai-agent\work-mode-projects\6a8d4332a65ab5fd4457b0ee\fin_market_aggregator\*" root@你的IP:/opt/fin-dashboard/
```

## 五、配置后台运行

### 1. 创建 systemd 服务
```bash
cat > /etc/systemd/system/fin-dashboard.service << 'EOF'
[Unit]
Description=Financial Dashboard
After=network.target

[Service]
User=root
WorkingDirectory=/opt/fin-dashboard
ExecStart=/opt/fin-dashboard/venv/bin/python app.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
```

### 2. 启动服务
```bash
systemctl daemon-reload
systemctl enable fin-dashboard
systemctl start fin-dashboard
```

### 3. 检查状态
```bash
systemctl status fin-dashboard
```
看到 `active (running)` 表示启动成功。

## 六、开放防火墙端口

### 1. 服务器内开放 5000 端口
```bash
ufw allow 5000
```

### 2. 阿里云控制台开放端口
1. 登录 https://swas.console.aliyun.com
2. 点击你的服务器实例
3. 左侧菜单 → **防火墙**
4. 添加规则：
   - 应用类型：自定义
   - 协议：TCP
   - 端口范围：5000
5. 保存

## 七、访问网站

浏览器打开：
```
http://你的公网IP:5000
```

30 秒自动刷新数据，7x24 小时运行。

## 八、管理命令

```bash
# 查看状态
systemctl status fin-dashboard

# 重启服务
systemctl restart fin-dashboard

# 停止服务
systemctl stop fin-dashboard

# 查看日志
journalctl -u fin-dashboard -f

# 更新代码后重启
cd /opt/fin-dashboard && git pull && systemctl restart fin-dashboard
```

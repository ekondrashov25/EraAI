# Deployment Guide for AI Assistant Application

This guide will help you deploy your AI Assistant application to a virtual server.

## Application Overview

Your application consists of:
- **Backend**: FastAPI server (`web_api.py`) with AI assistant capabilities
- **Frontend**: Static HTML/CSS/JS files served from `frontend/` directory
- **Database**: ChromaDB for vector storage
- **Dependencies**: Python packages listed in `requirements.txt`

## Prerequisites

### Server Requirements
- **OS**: Ubuntu 20.04+ or CentOS 8+ (recommended)
- **RAM**: Minimum 4GB (8GB+ recommended for better performance)
- **Storage**: At least 10GB free space
- **Python**: 3.9+ (3.11+ recommended)
- **Domain**: Optional but recommended for production

### Required Accounts
- OpenAI API key
- Virtual server access (SSH)

## Step 1: Server Setup

### 1.1 Connect to Your Server
```bash
ssh username@your-server-ip
```

### 1.2 Update System
```bash
sudo apt update && sudo apt upgrade -y
```

### 1.3 Install Python and Dependencies
```bash
# Install Python 3.11
sudo apt install python3.11 python3.11-venv python3.11-dev python3-pip -y

# Install system dependencies
sudo apt install build-essential libssl-dev libffi-dev python3-dev -y
sudo apt install nginx -y
```

### 1.4 Create Application Directory
```bash
sudo mkdir -p /opt/ai-assistant
sudo chown $USER:$USER /opt/ai-assistant
cd /opt/ai-assistant
```

## Step 2: Application Deployment

### 2.1 Upload Your Code
You have several options:

**Option A: Using Git (Recommended)**
```bash
# If your code is in a Git repository
git clone https://github.com/yourusername/ai-assistant.git .
```

**Option B: Using SCP**
```bash
# From your local machine
scp -r /path/to/your/project/* username@your-server-ip:/opt/ai-assistant/
```

**Option C: Using rsync**
```bash
# From your local machine
rsync -avz --exclude='.git' --exclude='env' /path/to/your/project/ username@your-server-ip:/opt/ai-assistant/
```

### 2.2 Set Up Python Environment
```bash
cd /opt/ai-assistant
python3.11 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 2.3 Configure Environment Variables
```bash
cp env.example .env
nano .env
```

Fill in your actual values:
```env
# OpenAI Configuration
OPENAI_API_KEY=sk-your-actual-openai-api-key
OPENAI_MODEL=gpt-4-turbo-preview

# MCP Server Configuration
MCP_SERVER_HOST=localhost
MCP_SERVER_PORT=8000

# External API Configuration (if needed)
EXTERNAL_API_BASE_URL=https://api.example.com
EXTERNAL_API_KEY=your_external_api_key_here

# Vector Database Configuration
CHROMA_DB_PATH=/opt/ai-assistant/chroma_db

# Logging Configuration
LOG_LEVEL=INFO
```

## Step 3: Production Configuration

### 3.1 Create Systemd Service
```bash
sudo nano /etc/systemd/system/ai-assistant.service
```

Add the following content:
```ini
[Unit]
Description=AI Assistant FastAPI Application
After=network.target

[Service]
Type=exec
User=www-data
Group=www-data
WorkingDirectory=/opt/ai-assistant
Environment=PATH=/opt/ai-assistant/venv/bin
ExecStart=/opt/ai-assistant/venv/bin/uvicorn web_api:app --host 0.0.0.0 --port 8000 --workers 2
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### 3.2 Set Permissions
```bash
sudo chown -R www-data:www-data /opt/ai-assistant
sudo chmod -R 755 /opt/ai-assistant
```

### 3.3 Enable and Start Service
```bash
sudo systemctl daemon-reload
sudo systemctl enable ai-assistant
sudo systemctl start ai-assistant
sudo systemctl status ai-assistant
```

## Step 4: Nginx Configuration

### 4.1 Configure Nginx for Backend API
```bash
sudo nano /etc/nginx/sites-available/ai-assistant
```

Add the following configuration:
```nginx
server {
    listen 80;
    server_name your-domain.com;  # Replace with your domain or server IP

    # Frontend static files
    location / {
        root /opt/ai-assistant/frontend;
        index index.html;
        try_files $uri $uri/ /index.html;
    }

    # Backend API proxy
    location /api/ {
        proxy_pass http://127.0.0.1:8000/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Health check
    location /health {
        proxy_pass http://127.0.0.1:8000/health;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "no-referrer-when-downgrade" always;
    add_header Content-Security-Policy "default-src 'self' http: https: data: blob: 'unsafe-inline'" always;
}
```

### 4.2 Enable Site and Configure SSL (Optional)
```bash
sudo ln -s /etc/nginx/sites-available/ai-assistant /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx

# Optional: SSL with Let's Encrypt
sudo apt install certbot python3-certbot-nginx -y
sudo certbot --nginx -d your-domain.com
```

## Step 5: Frontend Configuration

### 5.1 Update Frontend API Endpoint
Edit `/opt/ai-assistant/frontend/index.js` to point to your server:

```javascript
// Change the API base URL to your server
const API_BASE_URL = 'http://your-domain.com/api';  // or https://your-domain.com/api
```

### 5.2 Test the Application
```bash
# Check if the service is running
sudo systemctl status ai-assistant

# Check logs
sudo journalctl -u ai-assistant -f

# Test the API
curl http://localhost:8000/health
```

## Step 6: Security Considerations

### 6.1 Firewall Configuration
```bash
sudo ufw allow ssh
sudo ufw allow 'Nginx Full'
sudo ufw enable
```

### 6.2 Environment Security
```bash
# Secure the .env file
sudo chmod 600 /opt/ai-assistant/.env
sudo chown www-data:www-data /opt/ai-assistant/.env
```

### 6.3 Regular Updates
```bash
# Create update script
sudo nano /opt/ai-assistant/update.sh
```

```bash
#!/bin/bash
cd /opt/ai-assistant
git pull
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart ai-assistant
```

```bash
chmod +x /opt/ai-assistant/update.sh
```

## Step 7: Monitoring and Maintenance

### 7.1 Log Rotation
```bash
sudo nano /etc/logrotate.d/ai-assistant
```

```
/var/log/ai-assistant.log {
    daily
    missingok
    rotate 52
    compress
    delaycompress
    notifempty
    create 644 www-data www-data
    postrotate
        systemctl reload ai-assistant
    endscript
}
```

### 7.2 Health Monitoring
Create a simple health check script:
```bash
sudo nano /opt/ai-assistant/health_check.sh
```

```bash
#!/bin/bash
response=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health)
if [ $response -ne 200 ]; then
    echo "Health check failed with status $response"
    sudo systemctl restart ai-assistant
fi
```

```bash
chmod +x /opt/ai-assistant/health_check.sh
# Add to crontab: */5 * * * * /opt/ai-assistant/health_check.sh
```

## Troubleshooting

### Common Issues

1. **Service won't start**: Check logs with `sudo journalctl -u ai-assistant -f`
2. **Permission errors**: Ensure www-data owns the files
3. **Port conflicts**: Check if port 8000 is free with `netstat -tlnp | grep :8000`
4. **Memory issues**: Monitor with `htop` and consider increasing server RAM

### Useful Commands
```bash
# Restart application
sudo systemctl restart ai-assistant

# View logs
sudo journalctl -u ai-assistant -f

# Check status
sudo systemctl status ai-assistant

# Test API
curl http://localhost:8000/health

# Check nginx
sudo nginx -t
sudo systemctl status nginx
```

## Production Checklist

- [ ] Environment variables configured
- [ ] SSL certificate installed (if using domain)
- [ ] Firewall configured
- [ ] Log rotation set up
- [ ] Monitoring in place
- [ ] Backup strategy implemented
- [ ] Update process documented
- [ ] Security headers configured
- [ ] Rate limiting considered
- [ ] Error handling tested

Your AI Assistant should now be accessible at `http://your-domain.com` (or your server IP)!

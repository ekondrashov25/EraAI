#!/bin/bash

# AI Assistant Deployment Script
# This script automates the deployment process for your AI Assistant application

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
APP_NAME="ai-assistant"
APP_DIR="/opt/$APP_NAME"
SERVICE_NAME="$APP_NAME"
DOMAIN="${1:-localhost}"  # Use first argument as domain, default to localhost

echo -e "${BLUE}🚀 AI Assistant Deployment Script${NC}"
echo -e "${BLUE}================================${NC}"
echo ""

# Function to print colored output
print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   print_error "This script should not be run as root. Please run as a regular user with sudo privileges."
   exit 1
fi

# Check if we're in the project directory
if [ ! -f "web_api.py" ] || [ ! -f "requirements.txt" ]; then
    print_error "Please run this script from the project root directory (where web_api.py is located)"
    exit 1
fi

print_info "Starting deployment for domain: $DOMAIN"
echo ""

# Step 1: Update system
print_info "Step 1: Updating system packages..."
sudo apt update && sudo apt upgrade -y
print_status "System updated"

# Step 2: Install dependencies
print_info "Step 2: Installing system dependencies..."
sudo apt install -y python3.11 python3.11-venv python3.11-dev python3-pip
sudo apt install -y build-essential libssl-dev libffi-dev python3-dev
sudo apt install -y nginx curl git
print_status "System dependencies installed"

# Step 3: Create application directory
print_info "Step 3: Setting up application directory..."
sudo mkdir -p $APP_DIR
sudo chown $USER:$USER $APP_DIR
print_status "Application directory created: $APP_DIR"

# Step 4: Copy application files
print_info "Step 4: Copying application files..."
cp -r . $APP_DIR/
cd $APP_DIR
print_status "Application files copied"

# Step 5: Set up Python environment
print_info "Step 5: Setting up Python virtual environment..."
python3.11 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
print_status "Python environment configured"

# Step 6: Configure environment
print_info "Step 6: Configuring environment variables..."
if [ ! -f ".env" ]; then
    cp env.example .env
    print_warning "Please edit .env file with your actual API keys and configuration"
    print_info "You can do this by running: nano .env"
    read -p "Press Enter after you've configured the .env file..."
fi

# Step 7: Create systemd service
print_info "Step 7: Creating systemd service..."
sudo tee /etc/systemd/system/$SERVICE_NAME.service > /dev/null <<EOF
[Unit]
Description=AI Assistant FastAPI Application
After=network.target

[Service]
Type=exec
User=www-data
Group=www-data
WorkingDirectory=$APP_DIR
Environment=PATH=$APP_DIR/venv/bin
ExecStart=$APP_DIR/venv/bin/uvicorn web_api:app --host 0.0.0.0 --port 8000 --workers 2
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
print_status "Systemd service created"

# Step 8: Set permissions
print_info "Step 8: Setting file permissions..."
sudo chown -R www-data:www-data $APP_DIR
sudo chmod -R 755 $APP_DIR
sudo chmod 600 $APP_DIR/.env
print_status "Permissions set"

# Step 9: Configure Nginx
print_info "Step 9: Configuring Nginx..."
sudo tee /etc/nginx/sites-available/$APP_NAME > /dev/null <<EOF
server {
    listen 80;
    server_name $DOMAIN;

    # Frontend static files
    location / {
        root $APP_DIR/frontend;
        index index.html;
        try_files \$uri \$uri/ /index.html;
    }

    # Backend API proxy
    location /api/ {
        proxy_pass http://127.0.0.1:8000/;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    # Health check
    location /health {
        proxy_pass http://127.0.0.1:8000/health;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "no-referrer-when-downgrade" always;
    add_header Content-Security-Policy "default-src 'self' http: https: data: blob: 'unsafe-inline'" always;
}
EOF

sudo ln -sf /etc/nginx/sites-available/$APP_NAME /etc/nginx/sites-enabled/
sudo nginx -t
print_status "Nginx configured"

# Step 10: Enable and start services
print_info "Step 10: Starting services..."
sudo systemctl daemon-reload
sudo systemctl enable $SERVICE_NAME
sudo systemctl start $SERVICE_NAME
sudo systemctl restart nginx
print_status "Services started"

# Step 11: Configure firewall
print_info "Step 11: Configuring firewall..."
sudo ufw allow ssh
sudo ufw allow 'Nginx Full'
sudo ufw --force enable
print_status "Firewall configured"

# Step 12: Create update script
print_info "Step 12: Creating update script..."
tee $APP_DIR/update.sh > /dev/null <<EOF
#!/bin/bash
cd $APP_DIR
git pull
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart $SERVICE_NAME
echo "Update completed!"
EOF

chmod +x $APP_DIR/update.sh
print_status "Update script created"

# Step 13: Test the application
print_info "Step 13: Testing the application..."
sleep 5  # Wait for service to start

if curl -s http://localhost:8000/health > /dev/null; then
    print_status "Backend API is running"
else
    print_error "Backend API is not responding. Check logs with: sudo journalctl -u $SERVICE_NAME -f"
fi

if curl -s http://localhost > /dev/null; then
    print_status "Frontend is accessible"
else
    print_error "Frontend is not accessible. Check nginx logs"
fi

# Final status
echo ""
echo -e "${GREEN}🎉 Deployment completed!${NC}"
echo ""
echo -e "${BLUE}Application Information:${NC}"
echo -e "  • Backend API: http://$DOMAIN/api"
echo -e "  • Frontend: http://$DOMAIN"
echo -e "  • Health Check: http://$DOMAIN/health"
echo ""
echo -e "${BLUE}Useful Commands:${NC}"
echo -e "  • Check service status: sudo systemctl status $SERVICE_NAME"
echo -e "  • View logs: sudo journalctl -u $SERVICE_NAME -f"
echo -e "  • Restart service: sudo systemctl restart $SERVICE_NAME"
echo -e "  • Update application: $APP_DIR/update.sh"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo -e "  1. Configure your domain DNS to point to this server"
echo -e "  2. Set up SSL certificate: sudo certbot --nginx -d $DOMAIN"
echo -e "  3. Update frontend API endpoint in $APP_DIR/frontend/index.js"
echo -e "  4. Test the application thoroughly"
echo ""

if [ "$DOMAIN" != "localhost" ]; then
    print_info "For SSL certificate, run: sudo certbot --nginx -d $DOMAIN"
fi

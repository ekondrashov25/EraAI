# Quick Start Deployment Guide

## Prerequisites
- Virtual server with Ubuntu 20.04+ or CentOS 8+
- SSH access to your server
- OpenAI API key
- Domain name (optional but recommended)

## Option 1: Automated Deployment (Recommended)

### 1. Upload your project to the server
```bash
# From your local machine, upload the project
scp -r /path/to/your/project/* username@your-server-ip:/tmp/ai-assistant/
```

### 2. SSH into your server
```bash
ssh username@your-server-ip
```

### 3. Run the deployment script
```bash
# Move to the uploaded directory
cd /tmp/ai-assistant

# Make the script executable
chmod +x deploy.sh

# Run deployment (replace with your domain if you have one)
./deploy.sh your-domain.com
# OR for localhost testing:
./deploy.sh localhost
```

### 4. Configure environment variables
The script will prompt you to edit the `.env` file. Make sure to set:
- `OPENAI_API_KEY`: Your actual OpenAI API key
- `OPENAI_MODEL`: The model you want to use (e.g., gpt-4-turbo-preview)

## Option 2: Manual Deployment

Follow the detailed steps in `DEPLOYMENT_GUIDE.md` for manual deployment.

## Post-Deployment Steps

### 1. Test your application
```bash
# Check if the service is running
sudo systemctl status ai-assistant

# Test the API
curl http://your-server-ip/health
```

### 2. Set up SSL (if you have a domain)
```bash
sudo apt install certbot python3-certbot-nginx -y
sudo certbot --nginx -d your-domain.com
```

### 3. Update frontend API endpoint
Edit `/opt/ai-assistant/frontend/index.js` and update the API base URL:
```javascript
const API_BASE_URL = 'https://your-domain.com/api';  // or http://your-server-ip/api
```

## Access Your Application

- **Frontend**: http://your-server-ip (or https://your-domain.com)
- **API**: http://your-server-ip/api (or https://your-domain.com/api)
- **Health Check**: http://your-server-ip/health

## Troubleshooting

### Common Issues

1. **Service won't start**
   ```bash
   sudo journalctl -u ai-assistant -f
   ```

2. **Permission errors**
   ```bash
   sudo chown -R www-data:www-data /opt/ai-assistant
   ```

3. **Port conflicts**
   ```bash
   sudo netstat -tlnp | grep :8000
   ```

### Useful Commands

```bash
# Restart the application
sudo systemctl restart ai-assistant

# View logs
sudo journalctl -u ai-assistant -f

# Update the application
/opt/ai-assistant/update.sh

# Check nginx status
sudo systemctl status nginx
```

## Security Notes

- The deployment script configures basic security measures
- Consider setting up additional security measures for production
- Regularly update your system and application
- Monitor logs for any suspicious activity

## Support

If you encounter issues:
1. Check the logs: `sudo journalctl -u ai-assistant -f`
2. Verify environment variables are set correctly
3. Ensure all dependencies are installed
4. Check firewall and network configuration

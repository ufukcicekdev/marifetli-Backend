# Deployment Guide for Marifetli.com.tr

## Production Deployment Setup

This guide outlines the steps to deploy the Marifetli.com.tr forum application to a production environment.

## Prerequisites

- Ubuntu 20.04+ VPS
- Domain name pointing to the server
- SSL certificate (Let's Encrypt)
- PostgreSQL database server
- Redis server

## Step-by-Step Deployment

### 1. Server Setup

```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Install essential packages
sudo apt install python3-pip python3-dev python3-venv nginx supervisor postgresql redis-server git curl -y

# Install Node.js and npm
curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo -E bash -
sudo apt-get install -y nodejs
```

### 2. PostgreSQL Setup

```bash
# Create database and user
sudo -u postgres psql
CREATE DATABASE marifetli_db;
CREATE USER marifetli_user WITH PASSWORD 'strong_password';
ALTER ROLE marifetli_user SET client_encoding TO 'utf8';
ALTER ROLE marifetli_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE marifetli_user SET timezone TO 'UTC';
GRANT ALL PRIVILEGES ON DATABASE marifetli_db TO marifetli_user;
\q
```

### 3. Application Setup

```bash
# Create application directory
sudo mkdir -p /var/www/marifetli
sudo chown $USER:$USER /var/www/marifetli

# Clone repository
cd /var/www/marifetli
git clone <repository-url> .

# Create virtual environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Create environment file
cat > .env << EOF
DEBUG=False
SECRET_KEY=your_production_secret_key
DATABASE_URL=postgresql://marifetli_user:strong_password@localhost:5432/marifetli_db
REDIS_URL=redis://localhost:6379/0
EMAIL_HOST_USER=your_email@gmail.com
EMAIL_HOST_PASSWORD=your_app_password
SOCIAL_AUTH_GOOGLE_OAUTH2_KEY=your_google_client_id
SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET=your_google_client_secret
EOF
```

### 4. Django Configuration

```bash
# Run migrations
source venv/bin/activate
cd backend
python manage.py migrate

# Collect static files
python manage.py collectstatic --noinput

# Create superuser
python manage.py createsuperuser
```

### 5. Supervisor Configuration

Create supervisor config for Django:

```bash
sudo nano /etc/supervisor/conf.d/marifetli.conf
```

Add the following content:

```ini
[program:marifetli]
command=/var/www/marifetli/venv/bin/gunicorn --bind 127.0.0.1:8000 marifetli_project.wsgi:application
directory=/var/www/marifetli/backend
user=www-data
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/supervisor/marifetli.log
environment=PATH="/var/www/marifetli/venv/bin"
```

Start the service:

```bash
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start marifetli
```

### 6. Nginx Configuration

Create Nginx configuration:

```bash
sudo nano /etc/nginx/sites-available/marifetli
```

Add the following content:

```nginx
server {
    listen 80;
    server_name your-domain.com www.your-domain.com;
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static/ {
        alias /var/www/marifetli/backend/staticfiles/;
        expires 30d;
    }

    location /media/ {
        alias /var/www/marifetli/backend/media/;
        expires 30d;
    }
}
```

Enable the site:

```bash
sudo ln -s /etc/nginx/sites-available/marifetli /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### 7. SSL Certificate (Let's Encrypt)

```bash
sudo apt install certbot python3-certbot-nginx -y
sudo certbot --nginx -d your-domain.com -d www.your-domain.com
```

### 8. Frontend Deployment

Deploy the Next.js frontend separately (Vercel, Netlify, or self-hosted):

```bash
cd frontend
npm install
npm run build
```

Configure the frontend to point to your API endpoint:
```bash
NEXT_PUBLIC_API_BASE_URL=https://api.your-domain.com
```

### 9. Security Hardening

1. Configure firewall:
```bash
sudo ufw enable
sudo ufw allow OpenSSH
sudo ufw allow 'Nginx Full'
```

2. Set secure file permissions:
```bash
sudo chown -R www-data:www-data /var/www/marifetli
sudo chmod -R 755 /var/www/marifetli
```

### 10. Backup Strategy

Set up automated backups for database and media files:

```bash
# Create backup script
sudo nano /opt/backup-marifetli.sh
```

```bash
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backups/marifetli"
mkdir -p $BACKUP_DIR

# Backup database
pg_dump -U marifetli_user -h localhost marifetli_db > $BACKUP_DIR/db_backup_$DATE.sql

# Compress backup
tar -czf $BACKUP_DIR/backup_$DATE.tar.gz -C /var/www/marifetli/backend media
rm -f $BACKUP_DIR/db_backup_$DATE.sql

# Keep only last 7 days of backups
find $BACKUP_DIR -type f -mtime +7 -delete
```

Set up cron job:
```bash
crontab -e
# Add: 0 2 * * * /opt/backup-marifetli.sh
```

## Monitoring and Maintenance

- Monitor logs: `/var/log/supervisor/marifetli.log`
- Check service status: `sudo supervisorctl status marifetli`
- Update application: Pull latest changes, run migrations, restart services
- Monitor disk space and database size regularly
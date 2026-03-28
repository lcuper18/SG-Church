# Deployment Guide - SG Church

Guía completa para deployar SG Church a producción.

## Tabla de Contenidos

- [Opciones de Hosting](#opciones-de-hosting)
- [Deployment en Render](#deployment-en-render)
- [Deployment en VPS (DigitalOcean/Railway)](#deployment-en-vps-digitaloceanrailway)
- [Deployment en AWS](#deployment-en-aws)
- [Configuración de PostgreSQL](#configuración-de-postgresql)
- [Configuración de Redis](#configuración-de-redis)
- [Variables de Entorno](#variables-de-entorno)
- [Configuración de Gunicorn](#configuración-de-gunicorn)
- [Nginx como Reverse Proxy](#nginx-como-reverse-proxy)
- [SSL con Let's Encrypt](#ssl-con-lets-encrypt)
- [Celery Configuration](#celery-configuration)
- [Monitoreo](#monitoreo)
- [Backups](#backups)
- [Troubleshooting](#troubleshooting)

---

## Opciones de Hosting

### Comparación

| Opción | Costo | Dificultad | Ideal para |
|--------|-------|------------|------------|
| **Render** | $15-25/mes | Fácil | MVP, startups |
| **Railway** | $20-50/mes | Fácil | Startups |
| **DigitalOcean Droplet** | $15-40/mes | Media | Control total |
| **AWS EC2** | $20-100+/mes | Avanzado | Alta escala |

### Requisitos Mínimos

- **CPU**: 1 vCPU
- **RAM**: 1 GB (2 GB recomendado)
- **Disk**: 20 GB SSD
- **PostgreSQL**: Externo o incluido en el plan
- **Redis**: Externo o incluido en el plan

---

## Deployment en Render

Render es la opción recomendada para el MVP por su facilidad de setup.

### 1. Crear Cuenta

1. Ir a [render.com](https://render.com)
2. Crear cuenta gratuita
3. Conectar repositorio de GitHub

### 2. Crear PostgreSQL

1. Dashboard > New > PostgreSQL
2. Configurar:
   - **Name**: `sgchurch-db`
   - **Database**: `sgchurch`
   - **User**: `sgchurch`
   - **Plan**: $7/mo (Standard)
3. Copiar URL de conexión

### 3. Crear Redis

1. Dashboard > New > Redis
2. Configurar:
   - **Name**: `sgchurch-redis`
   - **Plan**: $7/mo (Standard)
3. Copiar URL de conexión

### 4. Configurar Environment Variables

Dashboard > Environment Variables:

```env
# Django
DEBUG=False
SECRET_KEY=your-very-long-secret-key
ALLOWED_HOSTS=your-domain.com,www.your-domain.com

# Database
DATABASE_URL=postgresql://sgchurch:password@host.render.internal:5432/sgchurch

# Redis
CELERY_BROKER_URL=redis://redis:password@redis.render.internal:6379/0
CELERY_RESULT_BACKEND=redis://redis:password@redis.render.internal:6379/0

# Email (SendGrid ejemplo)
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.sendgrid.net
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=apikey
EMAIL_HOST_PASSWORD=SG.xxxxxx

# Stripe
STRIPE_SECRET_KEY=sk_live_xxxxx
STRIPE_PUBLISHABLE_KEY=pk_live_xxxxx
STRIPE_WEBHOOK_SECRET=whsec_xxxxx

# AWS S3 (para archivos)
AWS_STORAGE_BUCKET_NAME=sgchurch-media
AWS_ACCESS_KEY_ID=xxxxx
AWS_SECRET_ACCESS_KEY=xxxxx
AWS_S3_REGION_NAME=us-east-1
AWS_S3_CUSTOM_DOMAIN=sgchurch-media.s3.amazonaws.com
```

### 5. Crear Web Service

1. Dashboard > New > Web Service
2. Conectar repositorio
3. Configurar:
   - **Name**: `sgchurch`
   - **Build Command**: `./build.sh`
   - **Start Command**: `gunicorn sg_church.wsgi:application`
   - **Plan**: $15/mo

### 6. Build Script

Crear `build.sh` en raíz del proyecto:

```bash
#!/bin/bash
set -e

# Instalar dependencias
pip install -r requirements.txt

# Recompilar assets estáticos
python manage.py collectstatic --noinput

# Ejecutar migraciones
python manage.py migrate --noinput
```

### 7. Dominio Personalizado

1. Dashboard > Your Web Service > Settings > Custom Domains
2. Agregar dominio
3. Configurar DNS según instrucciones

---

## Deployment en VPS (DigitalOcean/Railway)

### DigitalOcean Droplet

#### 1. Crear Droplet

1. Crear Droplet con:
   - **Image**: Ubuntu 22.04 LTS
   - **Size**: $15/mo (1GB RAM)
   - **Region**: Más cercana a usuarios

#### 2. Setup Inicial

```bash
# Conectar via SSH
ssh root@your-droplet-ip

# Actualizar sistema
apt update && apt upgrade -y

# Instalar dependencias
apt install -y python3.12 python3.12-venv python3.12-dev
apt install -y postgresql postgresql-contrib
apt install -y redis-server
apt install -y nginx certbot python3-certbot-nginx
apt install -y build-essential libpq-dev

# Crear usuario deployment
adduser deploy
usermod -aG sudo deploy
```

#### 3. Configurar PostgreSQL

```bash
# Cambiar a usuario postgres
sudo -u postgres psql

# Crear base de datos y usuario
CREATE DATABASE sgchurch;
CREATE USER sgchurch_user WITH PASSWORD 'your-strong-password';
GRANT ALL PRIVILEGES ON DATABASE sgchurch TO sgchurch_user;
ALTER USER sgchurch_user CREATEDB;

\q
```

#### 4. Configurar Aplicación

```bash
# Cambiar a usuario deployment
su - deploy
cd ~

# Clonar repositorio
git clone https://github.com/your-org/sg-church.git
cd sg-church

# Crear entorno virtual
python3.12 -m venv venv
source venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt

# Configurar variables de entorno
cp .env.example .env
nano .env
```

#### 5. Configurar Gunicorn

Crear `gunicorn.conf.py`:

```python
# gunicorn.conf.py
import multiprocessing

bind = "127.0.0.1:8000"
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "sync"
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 50
timeout = 30
keepalive = 2

# Logging
accesslog = "/var/log/sgchurch/access.log"
errorlog = "/var/log/sgchurch/error.log"
loglevel = "info"

# Python
pythonpath = "/home/deploy/sg-church"
```

#### 6. Configurar Systemd

Crear `/etc/systemd/system/sgchurch.service`:

```ini
[Unit]
Description=SG Church Django Application
After=network.target postgresql.service redis.service

[Service]
Type=notify
User=deploy
Group=deploy
WorkingDirectory=/home/deploy/sg-church
Environment="PATH=/home/deploy/sg-church/venv/bin"
ExecStart=/home/deploy/sg-church/venv/bin/gunicorn sg_church.wsgi:application -c /home/deploy/sg-church/gunicorn.conf.py
ExecReload=/bin/kill -s HUP $MAINPID
KillMode=mixed
TimeoutStopSec=5
PrivateTmp=true
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

```bash
# Habilitar yiciar servicio
sudo systemctl daemon-reload
sudo systemctl enable sgchurch
sudo systemctl start sgchurch
```

#### 7. Configurar Celery

Crear `/etc/systemd/system/celery.service`:

```ini
[Unit]
Description=Celery Worker for SG Church
After=network.target redis.service

[Service]
Type=forking
User=deploy
Group=deploy
WorkingDirectory=/home/deploy/sg-church
Environment="PATH=/home/deploy/sg-church/venv/bin"
ExecStart=/home/deploy/sg-church/venv/bin/celery -A sg_chorld worker --loglevel=info --logfile=/var/log/sgchurch/celery.log --pidfile=/var/run/celery.pid
ExecStop=/bin/kill -s TERM $MAINPID
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

---

## Deployment en AWS

### Arquitectura

```
┌──────────────────────┐
│  CloudFront (CDN)    │
│  (Static files, SSL) │
└──────────┬───────────┘
           │
┌──────────▼───────────┐
│  Application Load     │
│  Balancer (ALB)       │
└──────────┬───────────┘
           │
┌──────────▼───────────┐
│  EC2 Auto Scaling    │
│  (Django + Gunicorn)│
└──────────┬───────────┘
           │
    ┌──────┴──────┐
    │             │
┌───▼────┐  ┌────▼────┐
│RDS PG  │  │ElastiCache
│(Multi- │  │(Redis)  │
│ AZ)    │  │         │
└────────┘  └─────────┘
```

### RDS PostgreSQL

```bash
# Usar AWS Console o CLI
aws rds create-db-instance \
  --db-instance-identifier sgchurch-db \
  --db-instance-class db.t3.micro \
  --engine postgres \
  --engine-version 16.1 \
  --allocated-storage 20 \
  --db-name sgchurch \
  --master-username sgchurch \
  --master-user-password 'your-password' \
  --backup-retention-period 30 \
  --multi-az
```

### ElastiCache Redis

```bash
aws elasticache create-cache-cluster \
  --cache-cluster-id sgchurch-redis \
  --cache-node-type cache.t3.micro \
  --engine redis \
  --engine-version 7.0 \
  --num-cache-nodes 1
```

### ECS/Fargate (Alternativa)

```json
{
  "family": "sgchurch",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "512",
  "memory": "1024",
  "containerDefinitions": [
    {
      "name": "sgchurch",
      "image": "your-registry/sgchurch:latest",
      "essential": true,
      "portMappings": [
        {
          "containerPort": 8000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {"name": "DEBUG", "value": "False"},
        {"name": "DATABASE_URL", "value": "postgresql://..."}
      ]
    }
  ]
}
```

---

## Variables de Entorno

### Producción (.env)

```env
# ===========================================
# DJANGO
# ===========================================
DEBUG=False
SECRET_KEY=your-very-long-random-secret-key-at-least-50-chars
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com,localhost
CSRF_TRUSTED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com

# ===========================================
# DATABASE
# ===========================================
DATABASE_URL=postgresql://user:password@host:5432/dbname
# Para migraciones (opcional)
DATABASE_URL_UNPOOLED=postgresql://user:password@host:5432/dbname

# ===========================================
# REDIS / CELERY
# ===========================================
CELERY_BROKER_URL=redis://:password@host:6379/0
CELERY_RESULT_BACKEND=redis://:password@host:6379/0

# ===========================================
# EMAIL
# ===========================================
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.sendgrid.net
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=apikey
EMAIL_HOST_PASSWORD=SG.xxxxxxxx
DEFAULT_FROM_EMAIL=noreply@yourdomain.com

# ===========================================
# STRIPE
# ===========================================
STRIPE_SECRET_KEY=sk_live_xxxxx
STRIPE_PUBLISHABLE_KEY=pk_live_xxxxx
STRIPE_WEBHOOK_SECRET=whsec_xxxxx

# ===========================================
# AWS S3 (Storage)
# ===========================================
AWS_STORAGE_BUCKET_NAME=sgchurch-media
AWS_ACCESS_KEY_ID=AKIAxxxxx
AWS_SECRET_ACCESS_KEY=xxxxx
AWS_S3_REGION_NAME=us-east-1
AWS_S3_CUSTOM_DOMAIN=sgchurch-media.s3.amazonaws.com

# ===========================================
# SECURITY
# ===========================================
SECURE_SSL_REDIRECT=True
SECURE_PROXY_SSL_HEADER=HTTP_X_FORWARDED_PROTO,https
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
SECURE_HSTS_SECONDS=31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS=True
SECURE_HSTS_PRELOAD=True
```

---

## Configuración de Gunicorn

```python
# gunicorn.conf.py
import os
import multiprocessing

# Binding
bind = "127.0.0.1:8000"

# Workers (2-4 por core CPU)
workers = multiprocessing.cpu_count() * 2 + 1

# Worker class
worker_class = "sync"  # o "gevent" para async

# Timeouts
timeout = 60
keepalive = 5

# Logging
accesslog = "-"
errorlog = "-"
loglevel = "info"

# Security
limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190

# SSL (si se usa gunicorn directamente)
# keyfile = "/path/to/key.pem"
# certfile = "/path/to/cert.pem"
```

---

## Nginx como Reverse Proxy

```nginx
# /etc/nginx/sites-available/sgchurch

upstream sgchurch_app {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;
    
    # Redirect to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com www.yourdomain.com;
    
    # SSL Certificate
    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256;
    
    # Static files
    location /static/ {
        alias /home/deploy/sg-church/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
    
    # Media files
    location /media/ {
        alias /home/deploy/sg-church/media/;
        expires 7d;
    }
    
    # Django app
    location / {
        proxy_pass http://sgchurch_app;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
}
```

---

## SSL con Let's Encrypt

```bash
# Instalar certbot
sudo apt install certbot python3-certbot-nginx

# Obtener certificado
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com

# Renovar automáticamente
sudo certbot renew --dry-run
```

Agregar a crontab:
```
0 0 * * * /usr/bin/certbot renew --quiet
```

---

## Celery Configuration

### Production Settings

```python
# settings/production.py

# Broker
CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL')
CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND')

# Serialization
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_ACCEPT_CONTENT = ['json']

# Timezone
CELERY_TIMEZONE = 'America/New_York'
USE_TZ = True

# Task configuration
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60  # 30 minutes

# Retry configuration
CELERY_TASK_ACKS_LATE = True
CELERY_WORKER_PREFETCH_MULTIPLIER = 4

# Monitoring
CELERY_SEND_TASK_SENT_EVENT = True
CELERY_SEND_TASK_ERROR_EMAILS = True
```

### Beat Schedule (Cron Jobs)

```python
# schedules.py
from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    # Recordatorios de cumpleaños (diario a las 8am)
    'send-birthday-reminders': {
        'task': 'members.tasks.send_birthday_reminders',
        'schedule': crontab(hour=8, minute=0),
    },
    
    # Limpiar sesiones expiradas (cada hora)
    'cleanup-expired-sessions': {
        'task': 'core.tasks.cleanup_expired_sessions',
        'schedule': crontab(minute=0),
    },
    
    # Generar reportes mensuales (1ro de cada mes)
    'generate-monthly-reports': {
        'task': 'finance.tasks.generate_monthly_reports',
        'schedule': crontab(1, 0, month_of_year='1-12'),
    },
}
```

---

## Monitoreo

### Sentry (Error Tracking)

```bash
pip install sentry-sdk
```

```python
# settings/production.py
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration

sentry_sdk.init(
    dsn=os.environ.get('SENTRY_DSN'),
    integrations=[DjangoIntegration()],
    traces_sample_rate=0.1,
    send_default_pii=False,
    environment='production',
)
```

### Health Checks

```python
# health/views.py
from django.http import JsonResponse
from django.db import connection

def health_check(request):
    # Check database
    try:
        connection.ensure_connection()
        db_status = 'healthy'
    except Exception:
        db_status = 'unhealthy'
    
    return JsonResponse({
        'status': 'healthy' if db_status == 'healthy' else 'unhealthy',
        'database': db_status,
    })

# URLs
# path('health/', health_check, name='health_check'),
```

### Monitoring con Uptime Robot

Agregar endpoint de health a uptime monitoring:
- `https://yourdomain.com/health/`

---

## Backups

### PostgreSQL Backup Script

```bash
#!/bin/bash
# /scripts/backup.sh

DATE=$(date +%Y-%m-%d_%H%M%S)
BACKUP_DIR="/backups"
DB_NAME="sgchurch"
DB_USER="sgchurch_user"

# Create backup
pg_dump -U $DB_USER -h localhost $DB_NAME > "$BACKUP_DIR/db_$DATE.sql"

# Compress
gzip "$BACKUP_DIR/db_$DATE.sql"

# Upload to S3
aws s3 cp "$BACKUP_DIR/db_$DATE.sql.gz" s3://sgchurch-backups/

# Keep only last 30 days
find $BACKUP_DIR -name "*.sql.gz" -mtime +30 -delete
```

Agregar a crontab:
```
0 2 * * * /scripts/backup.sh
```

### Restaurar Backup

```bash
# Download from S3
aws s3 cp s3://sgchurch-backups/db_2024-01-15.sql.gz /tmp/

# Decompress
gunzip /tmp/db_2024-01-15.sql.gz

# Restore
psql -U sgchurch_user -d sgchurch < /tmp/db_2024-01-15.sql
```

---

## Troubleshooting

### Error: Database Connection Refused

```bash
# Verificar que PostgreSQL esté corriendo
sudo systemctl status postgresql

# Verificar credenciales
psql -U sgchurch_user -h localhost -d sgchurch

# Revisar logs
sudo tail -f /var/log/postgresql/postgresql-16-main.log
```

### Error: Bad Gateway (502)

```bash
# Verificar que Gunicorn esté corriendo
sudo systemctl status sgchurch

# Ver logs de Gunicorn
sudo tail -f /var/log/sgchurch/error.log

# Restart servicio
sudo systemctl restart sgchurch
```

### Error: CSRF Verification Failed

```bash
# Agregar a settings
CSRF_TRUSTED_ORIGINS=https://yourdomain.com
ALLOWED_HOSTS=yourdomain.com
```

### Error: Static Files Not Loading

```bash
# Recolectar static files
python manage.py collectstatic --noinput

# Verificar permisos
ls -la /home/deploy/sg-church/static/

# Verificar nginx config
sudo nginx -t
sudo systemctl reload nginx
```

### Error: Celery Tasks Not Running

```bash
# Verificar que Celery esté corriendo
sudo systemctl status celery

# Ver logs
sudo tail -f /var/log/sgchurch/celery.log

# Restart
sudo systemctl restart celery
```

---

## Checklist de Production

- [ ] DEBUG=False
- [ ] SECRET_KEY segura (al menos 50 caracteres)
- [ ] ALLOWED_HOSTS configurado
- [ ] HTTPS habilitado (SSL certificate)
- [ ] Database backups automatizados
- [ ] Static files servidos correctamente
- [ ] Celery workers corriendo
- [ ] Health check endpoint configurado
- [ ] Logging configurado
- [ ] Monitoring (Sentry) configurado

---

**Última actualización**: Marzo 2026

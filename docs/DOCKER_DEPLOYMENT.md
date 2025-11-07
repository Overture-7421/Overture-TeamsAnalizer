# Alliance Simulator - Docker Deployment Guide

## 🐳 Quick Start with Docker

### Prerequisites
- Docker installed on your system ([Get Docker](https://docs.docker.com/get-docker/))
- Docker Compose (included with Docker Desktop)

### Option 1: Using Docker Compose (Recommended)

This is the easiest way to run the application:

```bash
# Clone the repository
git clone https://github.com/Overture-7421/Overture-TeamsAnalizer.git
cd Overture-TeamsAnalizer

# Start the application
docker-compose up -d

# View logs
docker-compose logs -f

# Stop the application
docker-compose down
```

The application will be available at: **http://localhost:8501**

### Option 2: Using Docker Build & Run

```bash
# Build the image
docker build -t alliance-simulator:latest .

# Run the container
docker run -d \
  --name alliance-simulator \
  -p 8501:8501 \
  -v $(pwd)/data:/app/uploads \
  alliance-simulator:latest

# View logs
docker logs -f alliance-simulator

# Stop and remove
docker stop alliance-simulator
docker rm alliance-simulator
```

## 📁 Data Persistence

The Docker setup includes a volume mount for data persistence:

```yaml
volumes:
  - ./data:/app/uploads
```

This ensures that:
- Uploaded CSV files are persisted
- Data survives container restarts
- You can easily backup/restore data

## 🔧 Configuration

### Environment Variables

You can customize the application by setting environment variables in `docker-compose.yml`:

```yaml
environment:
  - STREAMLIT_SERVER_PORT=8501
  - STREAMLIT_SERVER_ADDRESS=0.0.0.0
  - STREAMLIT_SERVER_HEADLESS=true
  - STREAMLIT_BROWSER_GATHER_USAGE_STATS=false
```

### Custom Port

To use a different port (e.g., 8080):

```yaml
ports:
  - "8080:8501"
```

Then access at: http://localhost:8080

## 🚀 Production Deployment

### Deploy to Cloud Platforms

#### AWS ECS / Fargate

```bash
# Build and push to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account>.dkr.ecr.us-east-1.amazonaws.com
docker tag alliance-simulator:latest <account>.dkr.ecr.us-east-1.amazonaws.com/alliance-simulator:latest
docker push <account>.dkr.ecr.us-east-1.amazonaws.com/alliance-simulator:latest
```

#### Google Cloud Run

```bash
# Build and push to GCR
docker tag alliance-simulator:latest gcr.io/<project-id>/alliance-simulator:latest
docker push gcr.io/<project-id>/alliance-simulator:latest

# Deploy
gcloud run deploy alliance-simulator \
  --image gcr.io/<project-id>/alliance-simulator:latest \
  --platform managed \
  --port 8501 \
  --allow-unauthenticated
```

#### Azure Container Instances

```bash
# Build and push to ACR
az acr build --registry <registry-name> --image alliance-simulator:latest .

# Deploy
az container create \
  --resource-group <resource-group> \
  --name alliance-simulator \
  --image <registry-name>.azurecr.io/alliance-simulator:latest \
  --dns-name-label alliance-simulator \
  --ports 8501
```

#### DigitalOcean App Platform

1. Create a new app from your GitHub repository
2. Configure the Dockerfile deployment
3. Set the HTTP port to 8501
4. Deploy!

### Using a Reverse Proxy (Nginx)

For production deployments, use Nginx as a reverse proxy:

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### SSL/HTTPS with Let's Encrypt

```bash
# Install certbot
sudo apt-get install certbot python3-certbot-nginx

# Obtain certificate
sudo certbot --nginx -d your-domain.com

# Auto-renewal is configured automatically
```

## 🔍 Monitoring & Debugging

### Health Check

The container includes a health check:

```bash
# Check container health
docker ps

# Manual health check
curl http://localhost:8501/_stcore/health
```

### View Logs

```bash
# Docker Compose
docker-compose logs -f

# Docker
docker logs -f alliance-simulator
```

### Enter Container Shell

```bash
# Docker Compose
docker-compose exec alliance-simulator /bin/bash

# Docker
docker exec -it alliance-simulator /bin/bash
```

## 🛠️ Development Mode

For local development with hot-reload:

1. Uncomment the volume mount in `docker-compose.yml`:
   ```yaml
   volumes:
  - ../lib/streamlit_app.py:/app/lib/streamlit_app.py
   ```

2. Start the container:
   ```bash
   docker-compose up
   ```

3. Edit `lib/streamlit_app.py` locally - changes will be reflected immediately!  

## 📊 Resource Requirements

### Minimum Requirements
- **CPU**: 1 core
- **RAM**: 512MB
- **Storage**: 500MB

### Recommended for Production
- **CPU**: 2 cores
- **RAM**: 2GB
- **Storage**: 2GB

## 🔒 Security Best Practices

1. **Don't expose ports directly** - Use a reverse proxy
2. **Use environment variables** for sensitive configuration
3. **Regular updates**: Keep the base image updated
   ```bash
   docker-compose pull
   docker-compose up -d
   ```
4. **Scan for vulnerabilities**:
   ```bash
   docker scan alliance-simulator:latest
   ```

## 🐛 Troubleshooting

### Container won't start

```bash
# Check logs
docker-compose logs

# Verify port is not in use
lsof -i :8501
```

### Application crashes

```bash
# Check resource usage
docker stats alliance-simulator

# Increase memory limit in docker-compose.yml
deploy:
  resources:
    limits:
      memory: 2G
```

### Data not persisting

```bash
# Verify volume mount
docker inspect alliance-simulator | grep Mounts -A 10

# Check permissions
ls -la ./data/
```

## 📚 Additional Resources

- [Streamlit Documentation](https://docs.streamlit.io/)
- [Docker Documentation](https://docs.docker.com/)
- [Docker Compose Reference](https://docs.docker.com/compose/)

## 🆘 Support

For issues related to:
- **Application**: Create an issue on GitHub
- **Docker deployment**: Check the troubleshooting section above
- **FRC/Competition**: Contact Team Overture 7421

---

**Happy Deploying! 🚀**

*Team Overture 7421 - FIRST Robotics Competition 2025*

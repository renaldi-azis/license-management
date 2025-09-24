# Deployment Guide

---

## Prerequisites

- **Python** 3.8+
- **Redis** 6+ (for rate limiting)
- **Git**

---

## Local Development

<details>
<summary><strong>1. Clone and Setup</strong></summary>

```bash
git clone <your-repo>
cd license-server
cp .env.example .env
# Edit .env with your configuration
```
</details>

<details>
<summary><strong>2. Install Dependencies</strong></summary>

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```
</details>

<details>
<summary><strong>3. Initialize Database</strong></summary>

```bash
# Run the setup script
bash scripts/setup.sh

# Or manually
python -c "from models.database import init_db; init_db()"
python -c "from models.database import insert_default_users; insert_default_users()"
```
</details>

<details>
<summary><strong>4. Run Development Server</strong></summary>

```bash
# With Flask development server
flask run --host=0.0.0.0 --port=5000

# Or with the app directly
python app.py
```
</details>

<details>
<summary><strong>5. Access Application</strong></summary>

- **Admin Dashboard:** [https://<your-server-ip>:5000/admin](http://103.152.165.248:5000/admin)
- **API:** [https://<your-server-ip>:5000/api](http://103.152.165.248:5000/api)
</details>

---

## 🐳 Docker Deployment

<details>
<summary><strong>1. Build and Run with Docker Compose</strong></summary>

```bash
# Start with docker-compose (includes Redis)
docker-compose up --build

# Or run individual services
docker-compose up redis  # Start Redis first
docker-compose up web    # Then start the app
```
</details>

<details>
<summary><strong>2. Production Docker</strong></summary>

```bash
# Build production image
docker build -t license-server:latest .

# Run with persistent volume
docker run -d \
    --name license-server \
    -p 5000:5000 \
    -v license-data:/app/data \
    -e FLASK_ENV=production \
    -e SECRET_KEY=your-production-secret \
    license-server:latest
```
</details>

---

## ☁️ Cloud Deployment (DigitalOcean Example)

<details>
<summary><strong>1. Create Droplet</strong></summary>

- Choose **Ubuntu 22.04**
- Select **1GB RAM / 1 CPU** ($6/month)
- Add **SSH key** for access
</details>

<details>
<summary><strong>2. Initial Setup</strong></summary>

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```
</details>

<details>
<summary><strong>3. Deploy Application</strong></summary>

```bash
# Clone your repository
git clone <your-repo> /opt/license-server
cd /opt/license-server

# Copy environment file
sudo cp .env.example .env
sudo nano .env  # Configure your settings

# Start with docker-compose
sudo docker-compose up -d

# Enable auto-restart
sudo systemctl enable docker
```
</details>


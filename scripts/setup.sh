#!/bin/bash

set -e

echo "🚀 Setting up License Management Server..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check Python version
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Python 3 is required but not installed${NC}"
    exit 1
fi

PYTHON_VERSION=$(python3 -c "import sys; print('.'.join(map(str, sys.version_info[:2])))")
if [[ $(echo "$PYTHON_VERSION >= 3.8" | bc -l 2>/dev/null) -ne 1 ]]; then
    echo -e "${RED}Python 3.8+ is required (found $PYTHON_VERSION)${NC}"
    exit 1
fi

# Create virtual environment
echo -e "${YELLOW}Creating virtual environment...${NC}"
python3 -m venv venv

# Activate virtual environment
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    source venv/Scripts/activate
else
    source venv/bin/activate
fi

# Upgrade pip
echo -e "${YELLOW}Upgrading pip...${NC}"
pip install --upgrade pip

# Install dependencies
echo -e "${YELLOW}Installing dependencies...${NC}"
pip install -r requirements.txt

# Copy environment file
if [ ! -f .env ]; then
    echo -e "${YELLOW}Creating .env file...${NC}"
    cp .env.example .env
    echo -e "${GREEN}Please edit .env file with your configuration${NC}"
fi

# Initialize database
echo -e "${YELLOW}Initializing database...${NC}"
python -c "from models.database import init_db; init_db()"

# Create logs directory
mkdir -p logs

# Create admin user
echo -e "${YELLOW}Setting up admin user...${NC}"
python -c "
from services.security import verify_admin_credentials
if not verify_admin_credentials('admin', 'adminpass'):
    from services.user_service import create_admin_user
    create_admin_user()
else:
    print('Admin user already exists')
"

# Test Redis connection (if configured)
if grep -q "REDIS_URL=" .env; then
    echo -e "${YELLOW}Testing Redis connection...${NC}"
    python -c "
import os
from dotenv import load_dotenv
import redis

load_dotenv()
try:
    r = redis.from_url(os.getenv('REDIS_URL'))
    r.ping()
    print('✅ Redis connection successful')
except Exception as e:
    print('⚠️  Redis connection failed:', e)
    print('Rate limiting will be disabled')
"
fi

# Success message
echo -e "${GREEN}✅ Setup completed successfully!${NC}"
echo ""
echo "Next steps:"
echo "1. Edit .env file: nano .env"
echo "2. Change default admin password immediately"
echo "3. Start development server: flask run --host=0.0.0.0"
echo "4. Access admin dashboard: http://localhost:5000/admin"
echo "5. Test API: curl -X POST http://localhost:5000/api/auth/login \\"
echo "   -H 'Content-Type: application/json' \\"
echo "   -d '{\"username\":\"admin\",\"password\":\"adminpass\"}'"
echo ""
echo "For production deployment, see docs/DEPLOYMENT.md"
# UserManagementMicroservice
### Services Overview

1. **API Gateway** (Port 8000)
   - Single entry point for all client requests
   - Routes requests to appropriate services
   - Provides unified API interface

2. **User Service** (Port 8001)
   - Manages user CRUD operations
   - Stores users in-memory (SQLite)
   - Triggers notifications on user creation

3. **Notification Service** (Port 8002)
   - Handles notification delivery
   - Logs notifications to console
   - Stores notification history

   ### Running with Docker Compose

```bash
# Clone the repository
git clone 
cd UserManagementMicroservice

# Start all services
docker-compose up --build

# Or run in detached mode
docker-compose up -d --build

# View logs
docker-compose logs -f

# Stop all services
docker-compose down

### Building Individual Services

```bash
# Build User Service
cd user-service
docker build -t user-service:latest .

# Build Notification Service
cd notification-service
docker build -t notification-service:latest .

# Build API Gateway
cd api-gateway
docker build -t api-gateway:latest .
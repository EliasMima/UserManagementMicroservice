"""
API Gateway - Routes and orchestrates requests to backend services
Entry point for all client requests
"""
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr
import httpx
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="API Gateway",
    version="1.0.0",
    description="Gateway service for DevOps Learning Microservices"
)

# Service URLs (configured via environment variables)
USER_SERVICE_URL = os.getenv("USER_SERVICE_URL", "http://user-service:8001")
NOTIFICATION_SERVICE_URL = os.getenv("NOTIFICATION_SERVICE_URL", "http://notification-service:8002")


class User(BaseModel):
    """User model for API requests"""
    name: str
    email: EmailStr


@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "service": "api-gateway",
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "users": "/api/users",
            "docs": "/docs"
        }
    }


@app.get("/health")
async def health_check():

    logger.info("Health check requested")
    
    # Basic health check
    health_status = {
        "service": "api-gateway",
        "status": "healthy",
        "version": "1.0.0",
        "downstream_services": {}
    }
    
    # Check downstream services
    async with httpx.AsyncClient(timeout=5.0) as client:
        # Check User Service
        try:
            user_response = await client.get(f"{USER_SERVICE_URL}/health")
            health_status["downstream_services"]["user-service"] = {
                "status": "healthy" if user_response.status_code == 200 else "unhealthy",
                "response_time_ms": user_response.elapsed.total_seconds() * 1000
            }
        except Exception as e:
            logger.error(f"User service health check failed: {str(e)}")
            health_status["downstream_services"]["user-service"] = {
                "status": "unhealthy",
                "error": str(e)
            }
        
        # Check Notification Service
        try:
            notif_response = await client.get(f"{NOTIFICATION_SERVICE_URL}/health")
            health_status["downstream_services"]["notification-service"] = {
                "status": "healthy" if notif_response.status_code == 200 else "unhealthy",
                "response_time_ms": notif_response.elapsed.total_seconds() * 1000
            }
        except Exception as e:
            logger.error(f"Notification service health check failed: {str(e)}")
            health_status["downstream_services"]["notification-service"] = {
                "status": "unhealthy",
                "error": str(e)
            }
    
    return health_status


# ============================================
# User Service Proxy Endpoints
# ============================================

@app.get("/api/users")
async def get_users():
    """Get all users from User Service"""
    logger.info("Fetching all users")
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{USER_SERVICE_URL}/users")
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        logger.error(f"User service returned error: {e.response.status_code}")
        raise HTTPException(status_code=e.response.status_code, detail="User service error")
    except Exception as e:
        logger.error(f"Failed to connect to user service: {str(e)}")
        raise HTTPException(status_code=503, detail="User service unavailable")


@app.get("/api/users/{user_id}")
async def get_user(user_id: int):
    """Get specific user from User Service"""
    logger.info(f"Fetching user: {user_id}")
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{USER_SERVICE_URL}/users/{user_id}")
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise HTTPException(status_code=404, detail="User not found")
        logger.error(f"User service returned error: {e.response.status_code}")
        raise HTTPException(status_code=e.response.status_code, detail="User service error")
    except Exception as e:
        logger.error(f"Failed to connect to user service: {str(e)}")
        raise HTTPException(status_code=503, detail="User service unavailable")


@app.post("/api/users")
async def create_user(user: User):
    """Create new user via User Service"""
    logger.info(f"Creating user: {user.name}")
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{USER_SERVICE_URL}/users",
                json=user.model_dump()
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        logger.error(f"User service returned error: {e.response.status_code}")
        raise HTTPException(status_code=e.response.status_code, detail="User service error")
    except Exception as e:
        logger.error(f"Failed to connect to user service: {str(e)}")
        raise HTTPException(status_code=503, detail="User service unavailable")


@app.put("/api/users/{user_id}")
async def update_user(user_id: int, user: User):
    """Update user via User Service"""
    logger.info(f"Updating user: {user_id}")
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.put(
                f"{USER_SERVICE_URL}/users/{user_id}",
                json=user.model_dump()
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise HTTPException(status_code=404, detail="User not found")
        logger.error(f"User service returned error: {e.response.status_code}")
        raise HTTPException(status_code=e.response.status_code, detail="User service error")
    except Exception as e:
        logger.error(f"Failed to connect to user service: {str(e)}")
        raise HTTPException(status_code=503, detail="User service unavailable")


@app.delete("/api/users/{user_id}")
async def delete_user(user_id: int):
    """Delete user via User Service"""
    logger.info(f"Deleting user: {user_id}")
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.delete(f"{USER_SERVICE_URL}/users/{user_id}")
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise HTTPException(status_code=404, detail="User not found")
        logger.error(f"User service returned error: {e.response.status_code}")
        raise HTTPException(status_code=e.response.status_code, detail="User service error")
    except Exception as e:
        logger.error(f"Failed to connect to user service: {str(e)}")
        raise HTTPException(status_code=503, detail="User service unavailable")


# ============================================
# Error Handlers
# ============================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Custom HTTP exception handler"""
    return JSONResponse(
        status_code=exc.status_code, #http_exception_handler
        content={
            "error": exc.detail,
            "status_code": exc.status_code
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
"""
User Service - Manages user data
Simple CRUD operations with in-memory storage
"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, EmailStr
from typing import Dict, List, Optional
import httpx
import os
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="User Service",
    version="1.0.0",
    description="Manages user data with CRUD operations"
)

# In-memory storage (intentionally simple for DevOps learning)
# TODO for DevOps intern: Replace with actual database (PostgreSQL, MongoDB)
users_db: Dict[int, dict] = {}
user_id_counter = 1

# Configuration from environment variables
NOTIFICATION_SERVICE_URL = os.getenv(
    "NOTIFICATION_SERVICE_URL", 
    "http://notification-service:8002"
)


class User(BaseModel):
    """User model for request validation"""
    name: str
    email: EmailStr

    class Config:
        json_schema_extra = {
            "example": {
                "name": "John Doe",
                "email": "john@example.com"
            }
        }


class UserResponse(BaseModel):
    """User response model"""
    id: int
    name: str
    email: str
    created_at: str
    updated_at: str


@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with service information"""
    return {
        "service": "user-service",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "health": "/health",
            "users": "/users",
            "docs": "/docs"
        }
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """
    Health check endpoint
    Used by Docker and Kubernetes to verify service health
    """
    return {
        "service": "user-service",
        "status": "healthy",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat(),
        "users_count": len(users_db)
    }


@app.get("/users", response_model=List[UserResponse], tags=["Users"])
async def get_users():
    """
    Get all users
    Returns a list of all users in the system
    """
    logger.info(f"Fetching all users - Total count: {len(users_db)}")
    
    users_list = list(users_db.values())
    
    return users_list


@app.get("/users/{user_id}", response_model=UserResponse, tags=["Users"])
async def get_user(user_id: int):
    """
    Get user by ID
    Returns a single user's details
    """
    logger.info(f"Fetching user with ID: {user_id}")
    
    if user_id not in users_db:
        logger.warning(f"User not found: {user_id}")
        raise HTTPException(
            status_code=404, 
            detail=f"User with ID {user_id} not found"
        )
    
    user = users_db[user_id]
    logger.info(f"User found: {user['name']} ({user['email']})")
    
    return user


@app.post("/users", response_model=UserResponse, status_code=201, tags=["Users"])
async def create_user(user: User):
    """
    Create a new user
    Creates a new user and sends a welcome notification
    """
    global user_id_counter
    
    logger.info(f"Creating new user: {user.name} ({user.email})")
    
    # Check if email already exists
    for existing_user in users_db.values():
        if existing_user["email"] == user.email:
            logger.warning(f"Email already exists: {user.email}")
            raise HTTPException(
                status_code=400,
                detail=f"User with email {user.email} already exists"
            )
    
    # Create user record
    timestamp = datetime.now().isoformat()
    user_data = {
        "id": user_id_counter,
        "name": user.name,
        "email": user.email,
        "created_at": timestamp,
        "updated_at": timestamp
    }
    
    users_db[user_id_counter] = user_data
    logger.info(f"User created successfully with ID: {user_id_counter}")
    
    # Increment counter for next user
    user_id_counter += 1
    
    # Send welcome notification (async, fire-and-forget)
    await send_notification(
        email=user_data["email"],
        subject=f"Welcome {user_data['name']}!",
        message=f"Your account has been created successfully. User ID: {user_data['id']}"
    )
    
    return user_data


@app.put("/users/{user_id}", response_model=UserResponse, tags=["Users"])
async def update_user(user_id: int, user: User):
    """
    Update existing user
    Updates user information and sends notification
    """
    logger.info(f"Updating user with ID: {user_id}")
    
    if user_id not in users_db:
        logger.warning(f"User not found for update: {user_id}")
        raise HTTPException(
            status_code=404,
            detail=f"User with ID {user_id} not found"
        )
    
    # Check if new email conflicts with another user
    for uid, existing_user in users_db.items():
        if uid != user_id and existing_user["email"] == user.email:
            logger.warning(f"Email already in use by another user: {user.email}")
            raise HTTPException(
                status_code=400,
                detail=f"Email {user.email} is already in use by another user"
            )
    
    # Update user data
    users_db[user_id]["name"] = user.name
    users_db[user_id]["email"] = user.email
    users_db[user_id]["updated_at"] = datetime.now().isoformat()
    
    logger.info(f"User updated successfully: {user_id}")
    
    # Send update notification
    await send_notification(
        email=user.email,
        subject="Profile Updated",
        message=f"Hi {user.name}, your profile has been updated successfully."
    )
    
    return users_db[user_id]


@app.delete("/users/{user_id}", tags=["Users"])
async def delete_user(user_id: int):
    """
    Delete user
    Removes user from system and sends goodbye notification
    """
    logger.info(f"Deleting user with ID: {user_id}")
    
    if user_id not in users_db:
        logger.warning(f"User not found for deletion: {user_id}")
        raise HTTPException(
            status_code=404,
            detail=f"User with ID {user_id} not found"
        )
    
    # Get user data before deletion
    user_data = users_db[user_id]
    
    # Remove from database
    del users_db[user_id]
    
    logger.info(f"User deleted successfully: {user_id} ({user_data['name']})")
    
    # Send goodbye notification
    await send_notification(
        email=user_data["email"],
        subject="Account Deleted",
        message=f"Goodbye {user_data['name']}, your account has been deleted. We're sorry to see you go!"
    )
    
    return {
        "success": True,
        "message": "User deleted successfully",
        "deleted_user": {
            "id": user_data["id"],
            "name": user_data["name"],
            "email": user_data["email"]
        }
    }


async def send_notification(email: str, subject: str, message: str):
    """
    Send notification via Notification Service
    
    This function calls the notification service to send emails.
    It's a fire-and-forget operation - errors are logged but don't fail the main operation.
    
    TODO for DevOps intern: Add retry logic with exponential backoff
    TODO for DevOps intern: Add circuit breaker pattern
    TODO for DevOps intern: Add distributed tracing
    """
    try:
        logger.info(f"Sending notification to {email}")
        
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(
                f"{NOTIFICATION_SERVICE_URL}/notify",
                json={
                    "email": email,
                    "subject": subject,
                    "message": message
                }
            )
            
            if response.status_code == 200:
                logger.info(f"✅ Notification sent successfully to {email}")
            else:
                logger.warning(
                    f"⚠️  Notification service returned status {response.status_code} "
                    f"for {email}"
                )
                
    except httpx.TimeoutException:
        logger.error(f"❌ Notification service timeout for {email}")
    except httpx.ConnectError:
        logger.error(
            f"❌ Cannot connect to notification service at {NOTIFICATION_SERVICE_URL}"
        )
    except Exception as e:
        # Don't fail the user operation if notification fails
        logger.error(f"❌ Failed to send notification to {email}: {str(e)}")


@app.on_event("startup")
async def startup_event():
    """
    Runs when the application starts
    Good place for initialization tasks
    """
    logger.info("=" * 50)
    logger.info("🚀 User Service Starting Up")
    logger.info(f"📍 Notification Service URL: {NOTIFICATION_SERVICE_URL}")
    logger.info("=" * 50)


@app.on_event("shutdown")
async def shutdown_event():
    """
    Runs when the application shuts down
    Good place for cleanup tasks
    """
    logger.info("=" * 50)
    logger.info("👋 User Service Shutting Down")
    logger.info(f"📊 Total users in database: {len(users_db)}")
    logger.info("=" * 50)


if __name__ == "__main__":
    import uvicorn
    
    # Run the application
    # In production, use gunicorn or similar WSGI server
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8001,
        log_level="info"
    )
"""
Notification Service - Handles notification sending
Simulates email/SMS notifications
"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, EmailStr
from typing import List, Optional
import logging
from datetime import datetime
import random

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Notification Service",
    version="1.0.0",
    description="Handles notification sending (email/SMS simulation)"
)

# In-memory notification history (for demonstration and debugging)
# TODO for DevOps intern: Replace with actual database or message queue
notification_history: List[dict] = []
notification_id_counter = 1


class NotificationRequest(BaseModel):
    """Notification request model"""
    email: EmailStr
    subject: str
    message: str
    priority: Optional[str] = "normal"  # low, normal, high

    class Config:
        json_schema_extra = {
            "example": {
                "email": "user@example.com",
                "subject": "Welcome!",
                "message": "Thank you for joining our platform.",
                "priority": "high"
            }
        }


class NotificationResponse(BaseModel):
    """Notification response model"""
    id: int
    email: str
    subject: str
    message: str
    priority: str
    status: str
    timestamp: str
    delivery_time_ms: int


@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with service information"""
    return {
        "service": "notification-service",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "health": "/health",
            "notify": "/notify (POST)",
            "notifications": "/notifications",
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
        "service": "notification-service",
        "status": "healthy",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat(),
        "notifications_sent": len(notification_history),
        "notifications_failed": sum(
            1 for n in notification_history if n["status"] == "failed"
        )
    }


@app.post("/notify", response_model=NotificationResponse, status_code=200, tags=["Notifications"])
async def send_notification(notification: NotificationRequest):
    """
    Send notification to user
    
    In a real system, this would integrate with:
    - Email providers (SendGrid, AWS SES, Mailgun)
    - SMS providers (Twilio, SNS)
    - Push notification services (Firebase, OneSignal)
    
    For learning purposes, we simulate the sending and store the notification.
    
    TODO for DevOps intern: Integrate with actual notification provider
    TODO for DevOps intern: Add message queue (RabbitMQ, Kafka)
    TODO for DevOps intern: Add retry mechanism
    """
    global notification_id_counter
    
    logger.info("=" * 60)
    logger.info(f"📧 Sending notification to: {notification.email}")
    logger.info(f"📋 Subject: {notification.subject}")
    logger.info(f"💬 Message: {notification.message}")
    logger.info(f"⚡ Priority: {notification.priority}")
    
    # Simulate notification sending with random delay
    # In real world, this would be actual API call to email/SMS provider
    delivery_time = random.randint(50, 300)  # Simulate 50-300ms delivery time
    
    # Simulate occasional failures (5% failure rate for realism)
    # This helps test error handling in dependent services
    is_successful = random.random() > 0.05
    
    status = "sent" if is_successful else "failed"
    
    # Create notification record
    notification_record = {
        "id": notification_id_counter,
        "email": notification.email,
        "subject": notification.subject,
        "message": notification.message,
        "priority": notification.priority,
        "status": status,
        "timestamp": datetime.now().isoformat(),
        "delivery_time_ms": delivery_time
    }
    
    # Store in history
    notification_history.append(notification_record)
    
    # Increment counter
    notification_id_counter += 1
    
    if is_successful:
        logger.info(f"✅ Notification sent successfully - ID: {notification_record['id']}")
        logger.info(f"⏱️  Delivery time: {delivery_time}ms")
    else:
        logger.error(f"❌ Notification failed - ID: {notification_record['id']}")
        # In production, you might want to raise an exception here
        # For learning purposes, we just log and continue
    
    logger.info("=" * 60)
    
    return notification_record


@app.get("/notifications", response_model=List[NotificationResponse], tags=["Notifications"])
async def get_notifications(
    limit: int = 100,
    status: Optional[str] = None,
    priority: Optional[str] = None
):
    """
    Get notification history
    
    Query parameters:
    - limit: Maximum number of notifications to return (default: 100)
    - status: Filter by status (sent/failed)
    - priority: Filter by priority (low/normal/high)
    
    This endpoint is useful for:
    - Debugging notification issues
    - Monitoring notification delivery
    - Auditing notification history
    """
    logger.info(f"Fetching notification history - Limit: {limit}")
    
    # Apply filters
    filtered_notifications = notification_history
    
    if status:
        filtered_notifications = [
            n for n in filtered_notifications if n["status"] == status
        ]
        logger.info(f"Filtered by status: {status}")
    
    if priority:
        filtered_notifications = [
            n for n in filtered_notifications if n["priority"] == priority
        ]
        logger.info(f"Filtered by priority: {priority}")
    
    # Apply limit
    result = filtered_notifications[-limit:] if limit else filtered_notifications
    
    logger.info(f"Returning {len(result)} notifications")
    
    return result


@app.get("/notifications/{notification_id}", response_model=NotificationResponse, tags=["Notifications"])
async def get_notification(notification_id: int):
    """
    Get specific notification by ID
    Useful for tracking individual notification status
    """
    logger.info(f"Fetching notification with ID: {notification_id}")
    
    # Find notification
    for notification in notification_history:
        if notification["id"] == notification_id:
            logger.info(f"Notification found: {notification['subject']}")
            return notification
    
    logger.warning(f"Notification not found: {notification_id}")
    raise HTTPException(
        status_code=404,
        detail=f"Notification with ID {notification_id} not found"
    )


@app.get("/notifications/stats", tags=["Statistics"])
async def get_notification_stats():
    """
    Get notification statistics
    
    Provides insights into:
    - Total notifications sent
    - Success/failure rates
    - Average delivery time
    - Priority distribution
    
    TODO for DevOps intern: Export these metrics to Prometheus
    """
    if not notification_history:
        return {
            "total_notifications": 0,
            "successful": 0,
            "failed": 0,
            "success_rate": 0,
            "average_delivery_time_ms": 0
        }
    
    total = len(notification_history)
    successful = sum(1 for n in notification_history if n["status"] == "sent")
    failed = sum(1 for n in notification_history if n["status"] == "failed")
    
    # Calculate average delivery time
    avg_delivery = sum(n["delivery_time_ms"] for n in notification_history) / total
    
    # Priority distribution
    priority_dist = {
        "low": sum(1 for n in notification_history if n["priority"] == "low"),
        "normal": sum(1 for n in notification_history if n["priority"] == "normal"),
        "high": sum(1 for n in notification_history if n["priority"] == "high")
    }
    
    stats = {
        "total_notifications": total,
        "successful": successful,
        "failed": failed,
        "success_rate": round((successful / total) * 100, 2),
        "average_delivery_time_ms": round(avg_delivery, 2),
        "priority_distribution": priority_dist
    }
    
    logger.info(f"Statistics calculated: {stats}")
    
    return stats


@app.delete("/notifications", tags=["Notifications"])
async def clear_notifications():
    """
    Clear notification history
    
    Useful for:
    - Testing and development
    - Resetting state
    - Cleanup operations
    
    ⚠️ WARNING: This will delete all notification history!
    """
    logger.warning("🗑️  Clearing all notification history")
    
    count = len(notification_history)
    notification_history.clear()
    
    logger.info(f"✅ Cleared {count} notifications")
    
    return {
        "success": True,
        "message": f"Notification history cleared. Deleted {count} notifications."
    }


@app.delete("/notifications/{notification_id}", tags=["Notifications"])
async def delete_notification(notification_id: int):
    """
    Delete specific notification
    Removes a single notification from history
    """
    logger.info(f"Deleting notification with ID: {notification_id}")
    
    # Find and remove notification
    for i, notification in enumerate(notification_history):
        if notification["id"] == notification_id:
            deleted = notification_history.pop(i)
            logger.info(f"✅ Notification deleted: {notification_id}")
            return {
                "success": True,
                "message": "Notification deleted",
                "deleted_notification": deleted
            }
    
    logger.warning(f"Notification not found for deletion: {notification_id}")
    raise HTTPException(
        status_code=404,
        detail=f"Notification with ID {notification_id} not found"
    )


@app.on_event("startup")
async def startup_event():
    """
    Runs when the application starts
    Good place for initialization tasks
    """
    logger.info("=" * 50)
    logger.info("🚀 Notification Service Starting Up")
    logger.info("📧 Email simulation mode active")
    logger.info("📱 SMS simulation mode active")
    logger.info("=" * 50)


@app.on_event("shutdown")
async def shutdown_event():
    """
    Runs when the application shuts down
    Good place for cleanup tasks
    """
    logger.info("=" * 50)
    logger.info("👋 Notification Service Shutting Down")
    logger.info(f"📊 Total notifications sent: {len(notification_history)}")
    logger.info("=" * 50)


if __name__ == "__main__":
    import uvicorn
    
    # Run the application
    # In production, use gunicorn or similar WSGI server
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8002,
        log_level="info"
    )
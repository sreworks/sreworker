"""WebSocket API for real-time communication with workers."""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from ..services.worker_manager import WorkerManager
from ..models.message import WebSocketMessage
from ..utils.logger import get_app_logger
import json

router = APIRouter(tags=["websocket"])

# Global worker manager instance (will be set by main.py)
worker_manager: WorkerManager = None
logger = get_app_logger()


@router.websocket("/ws/{worker_id}")
async def websocket_endpoint(websocket: WebSocket, worker_id: str):
    """
    WebSocket endpoint for communicating with a worker.

    Args:
        websocket: WebSocket connection
        worker_id: Worker ID to connect to
    """
    await websocket.accept()
    logger.info(f"WebSocket connection accepted for worker: {worker_id}")

    # Check if worker exists
    worker = worker_manager.get_worker(worker_id)
    if not worker:
        await websocket.send_json({
            "type": "error",
            "content": f"Worker not found: {worker_id}"
        })
        await websocket.close()
        return

    try:
        # Register WebSocket connection
        await worker_manager.register_websocket(worker_id, websocket)

        # Send connection confirmation
        await websocket.send_json({
            "type": "connected",
            "worker_id": worker_id,
            "worker_name": worker.name,
            "ai_cli_type": worker.ai_cli_type
        })

        # Send recent message history
        history = worker_manager.get_message_history(worker_id, limit=20)
        if history:
            await websocket.send_json({
                "type": "history",
                "messages": history
            })

        # Listen for messages from client
        while True:
            try:
                # Receive message from client
                data = await websocket.receive_text()
                message_data = json.loads(data)

                # Validate message
                message = WebSocketMessage(**message_data)

                if message.type == "message":
                    # Send message to worker
                    success = await worker_manager.send_message(worker_id, message.content)

                    if not success:
                        await websocket.send_json({
                            "type": "error",
                            "content": "Failed to send message to worker"
                        })

                elif message.type == "ping":
                    # Respond to ping with pong
                    await websocket.send_json({
                        "type": "pong"
                    })

                else:
                    await websocket.send_json({
                        "type": "error",
                        "content": f"Unknown message type: {message.type}"
                    })

            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "content": "Invalid JSON message"
                })

            except Exception as e:
                logger.error(f"Error processing WebSocket message: {e}")
                await websocket.send_json({
                    "type": "error",
                    "content": f"Error processing message: {str(e)}"
                })

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for worker: {worker_id}")

    except Exception as e:
        logger.error(f"WebSocket error for worker {worker_id}: {e}")

    finally:
        # Unregister WebSocket connection
        await worker_manager.unregister_websocket(worker_id, websocket)
        logger.info(f"WebSocket connection closed for worker: {worker_id}")

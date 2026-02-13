import json
from channels.generic.websocket import AsyncWebsocketConsumer

class AnalyzeConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.accept()
        await self.send_json({"type": "connected"})

    async def disconnect(self, close_code):
        pass

    async def receive(self, text_data=None, bytes_data=None):
        if text_data is not None:
            await self.handle_json(text_data)
            return

        if bytes_data is not None:
            await self.handle_frame(bytes_data)
            return

    async def handle_json(self, text_data: str):
        try:
            msg = json.loads(text_data)
        except json.JSONDecodeError:
            await self.send_json({"type": "error", "message": "invalid_json"})
            return

        msg_type = msg.get("type")

        if msg_type == "ping":
            await self.send_json({"type": "pong"})
            return

        if msg_type == "start":
            exercise = msg.get("exercise", "unknown")
            await self.send_json({"type": "started", "exercise": exercise})
            return

        if msg_type == "test":
            await self.send_json({
                "type": "result",
                "exercise": "pushup",
                "count": 5,
                "errors": ["knee_caving"],
                "feedback": "Keep knees over feet",
                "score": 85,
                "echo": msg
            })
            return

        await self.send_json({"type": "error", "message": "unknown_type", "echo": msg})

    async def handle_frame(self, frame_bytes: bytes):
        await self.send_json({"type": "frame_ack", "bytes": len(frame_bytes)})

    async def send_json(self, payload: dict):
        await self.send(text_data=json.dumps(payload))

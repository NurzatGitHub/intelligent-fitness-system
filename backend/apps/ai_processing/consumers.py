import json
from channels.generic.websocket import AsyncWebsocketConsumer

class TestConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.accept()
        print("✅ WebSocket connected")
    
    async def disconnect(self, close_code):
        print("❌ WebSocket disconnected")
    
    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            print(f"📨 Received: {data['type']}")
            
            # Эхо-ответ для теста
            await self.send(text_data=json.dumps({
                "exercise": "pushup",
                "count": 5,
                "errors": ["knee_caving"],
                "feedback": "Держите колени над стопами",
                "score": 85
            }))
            
        except Exception as e:
            print(f"❌ Error: {e}")
            await self.send(text_data=json.dumps({
                "error": str(e)
            }))
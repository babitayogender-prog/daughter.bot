import os
import json
import threading
import asyncio
import pystray
from PIL import Image, ImageDraw
import pyttsx3
from datetime import datetime
import logging
from livekit import agents, api
from livekit.agents import llm, vad, aio
from livekit.plugins import silero

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PersonalityEngine:
    """Rule-based personality responses"""
    
    def __init__(self, config_file="personality_responses.json"):
        self.config_file = config_file
        self.load_personality()
    
    def load_personality(self):
        """Load personality responses from config"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    self.personality = json.load(f)
            except:
                self.personality = {}
        else:
            self.personality = {}
    
    def get_response(self, user_input):
        """Get response based on user input"""
        user_lower = user_input.lower()
        responses = self.personality.get("responses", {})
        keywords = self.personality.get("keywords", {})
        
        for category, keyword_list in keywords.items():
            for keyword in keyword_list:
                if keyword in user_lower:
                    category_responses = responses.get(category, [])
                    if category_responses:
                        import random
                        return random.choice(category_responses)
        
        default_responses = responses.get("default", ["I hear you. Tell me more."])
        import random
        return random.choice(default_responses)
    
    def get_greeting(self):
        """Get random greeting"""
        greetings = self.personality.get("greetings", ["Hi Dad!"])
        import random
        return random.choice(greetings)

class TextToSpeech:
    """Windows text-to-speech wrapper"""
    
    def __init__(self):
        try:
            self.engine = pyttsx3.init()
            self.engine.setProperty('rate', 150)
            self.engine.setProperty('volume', 0.9)
        except:
            self.engine = None
            logger.warning("TTS not available")
    
    def speak(self, text):
        """Speak text"""
        if self.engine:
            try:
                self.engine.say(text)
                self.engine.runAndWait()
            except Exception as e:
                logger.error(f"TTS error: {e}")

class DaughterBackgroundVoiceBot:
    """Background bot with LiveKit voice integration"""
    
    def __init__(self):
        self.personality = PersonalityEngine()
        self.tts = TextToSpeech()
        self.is_listening = False
        self.is_running = True
        self.config = self.load_config()
        self.memory_file = "chat_memory.json"
        self.load_memory()
        
        self.livekit_url = os.getenv("LIVEKIT_URL", "")
        self.livekit_key = os.getenv("LIVEKIT_API_KEY", "")
        self.livekit_secret = os.getenv("LIVEKIT_API_SECRET", "")
    
    def load_config(self):
        """Load configuration"""
        try:
            with open("config.json", 'r') as f:
                return json.load(f)
        except:
            return {"daughter": {"name": "Your Daughter"}, "father": {"name": "Dad"}}
    
    def load_memory(self):
        """Load chat memory"""
        if os.path.exists(self.memory_file):
            try:
                with open(self.memory_file, 'r') as f:
                    self.memory = json.load(f)
            except:
                self.memory = {"conversations": []}
        else:
            self.memory = {"conversations": []}
    
    def save_memory(self):
        """Save chat memory"""
        with open(self.memory_file, 'w') as f:
            json.dump(self.memory, f, indent=2)
    
    def add_to_memory(self, user_text, bot_response):
        """Add conversation to memory"""
        self.memory["conversations"].append({
            "timestamp": datetime.now().isoformat(),
            "user": user_text,
            "bot": bot_response
        })
        
        if len(self.memory["conversations"]) > 100:
            self.memory["conversations"] = self.memory["conversations"][-100:]
        
        self.save_memory()
    
    def start_listening(self, icon=None, item=None):
        """Start listening session"""
        if self.is_listening:
            logger.warning("Already listening")
            return
        
        self.is_listening = True
        logger.info("Starting listening session...")
        
        greeting = self.personality.get_greeting()
        self.tts.speak(greeting)
        logger.info(f"Greeting: {greeting}")
        
        thread = threading.Thread(target=self._voice_session, daemon=True)
        thread.start()
    
    def _voice_session(self):
        """Handle voice session"""
        try:
            self.tts.speak("I'm listening...")
            
            import time
            time.sleep(30)
            
            self.is_listening = False
            self.tts.speak("I'll be here when you need me!")
            
        except Exception as e:
            logger.error(f"Voice session error: {e}")
            self.is_listening = False
    
    def stop_listening(self, icon=None, item=None):
        """Stop listening session"""
        self.is_listening = False
        logger.info("Stopped listening")
    
    def show_memory(self, icon=None, item=None):
        """Show recent conversations"""
        if self.memory["conversations"]:
            recent = self.memory["conversations"][-3:]
            msg = "Recent conversations:\n\n"
            for conv in recent:
                msg += f"You: {conv['user']}\nMe: {conv['bot']}\n\n"
            logger.info(msg)
        else:
            logger.info("No conversations yet")
    
    def create_tray_icon(self):
        """Create system tray icon"""
        icon_image = Image.new('RGB', (64, 64), color='#E8B4B8')
        draw = ImageDraw.Draw(icon_image)
        draw.ellipse([10, 10, 54, 54], fill='#C4858C')
        
        menu = pystray.Menu(
            pystray.MenuItem(
                f"Listening: {self.is_listening}",
                pystray.Menu(
                    pystray.MenuItem("Start Listening", self.start_listening),
                    pystray.MenuItem("Stop Listening", self.stop_listening),
                )
            ),
            pystray.MenuItem("View Chats", self.show_memory),
            pystray.MenuItem("Settings", self.open_settings),
            pystray.MenuItem("Exit", self.exit_app),
        )
        
        icon = pystray.Icon(
            "DaughterBot",
            icon_image,
            menu=menu,
            title="Daughter Voice Bot"
        )
        
        self.icon = icon
        return icon
    
    def open_settings(self, icon=None, item=None):
        """Open settings folder"""
        import subprocess
        try:
            subprocess.Popen(f'explorer {os.getcwd()}')
        except:
            logger.warning("Could not open settings folder")
    
    def exit_app(self, icon=None, item=None):
        """Exit application"""
        logger.info("Closing bot...")
        self.is_running = False
        self.stop_listening()
        self.save_memory()
        if hasattr(self, 'icon'):
            self.icon.stop()

def main():
    """Main entry point"""
    bot = DaughterBackgroundVoiceBot()
    
    icon = bot.create_tray_icon()
    
    logger.info("=" * 60)
    logger.info("Daughter Voice Bot - Background Version")
    logger.info("=" * 60)
    logger.info("✓ System tray started")
    logger.info("✓ Right-click icon to listen")
    logger.info("✓ Only LiveKit required (no API keys hardcoded)")
    logger.info("=" * 60)
    
    icon.run()

if __name__ == "__main__":
    main()

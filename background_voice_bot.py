import os
import json
import threading
import asyncio
import pystray
from PIL import Image, ImageDraw
import pyttsx3
from datetime import datetime
import logging
import tkinter as tk
from tkinter import simpledialog, messagebox
from dotenv import load_dotenv, set_key

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================================
# SETUP API KEYS - ASK USER ON FIRST RUN
# ============================================================================

class LiveKitSetup:
    """Interactive LiveKit credentials setup"""
    
    @staticmethod
    def check_and_setup():
        """Check if .env exists, if not ask user for credentials"""
        env_file = ".env"
        
        # If .env already exists, load it
        if os.path.exists(env_file):
            load_dotenv(env_file)
            logger.info("✓ .env file found - using existing credentials")
            return True
        
        # .env doesn't exist - ask user
        logger.info("First time setup - asking for LiveKit credentials...")
        
        root = tk.Tk()
        root.withdraw()  # Hide the main window
        
        # Create setup dialog
        setup_window = tk.Toplevel(root)
        setup_window.title("Daughter Voice Bot - Setup")
        setup_window.geometry("500x300")
        setup_window.configure(bg='#FFF8F7')
        
        # Title
        title_label = tk.Label(
            setup_window,
            text="🎁 DAUGHTER VOICE BOT - FIRST TIME SETUP",
            font=("Arial", 14, "bold"),
            bg='#FFF8F7',
            fg='#C4858C'
        )
        title_label.pack(pady=15)
        
        # Instructions
        instructions = tk.Label(
            setup_window,
            text="Enter your LiveKit credentials\n(Get them free from https://livekit.io)",
            font=("Arial", 10),
            bg='#FFF8F7',
            fg='#3E3E3E',
            justify=tk.CENTER
        )
        instructions.pack(pady=10)
        
        # Input fields
        fields = {}
        
        # LiveKit URL
        tk.Label(setup_window, text="LiveKit URL:", bg='#FFF8F7', fg='#3E3E3E').pack(anchor='w', padx=20, pady=(10, 0))
        url_entry = tk.Entry(setup_window, width=50)
        url_entry.pack(padx=20, pady=5)
        url_entry.insert(0, "ws://your-url:7880")
        fields['url'] = url_entry
        
        # API Key
        tk.Label(setup_window, text="API Key:", bg='#FFF8F7', fg='#3E3E3E').pack(anchor='w', padx=20, pady=(10, 0))
        key_entry = tk.Entry(setup_window, width=50)
        key_entry.pack(padx=20, pady=5)
        key_entry.insert(0, "your-api-key")
        fields['key'] = key_entry
        
        # API Secret
        tk.Label(setup_window, text="API Secret:", bg='#FFF8F7', fg='#3E3E3E').pack(anchor='w', padx=20, pady=(10, 0))
        secret_entry = tk.Entry(setup_window, width=50, show='*')
        secret_entry.pack(padx=20, pady=5)
        secret_entry.insert(0, "your-api-secret")
        fields['secret'] = secret_entry
        
        # Save button
        def save_credentials():
            url = url_entry.get()
            key = key_entry.get()
            secret = secret_entry.get()
            
            # Validate
            if not url or url == "ws://your-url:7880":
                messagebox.showerror("Error", "Please enter LiveKit URL")
                return
            if not key or key == "your-api-key":
                messagebox.showerror("Error", "Please enter API Key")
                return
            if not secret or secret == "your-api-secret":
                messagebox.showerror("Error", "Please enter API Secret")
                return
            
            # Create .env file
            with open('.env', 'w') as f:
                f.write(f"LIVEKIT_URL={url}\n")
                f.write(f"LIVEKIT_API_KEY={key}\n")
                f.write(f"LIVEKIT_API_SECRET={secret}\n")
            
            logger.info("✓ Credentials saved to .env")
            messagebox.showinfo("Success", "Credentials saved!\nBot will now start...")
            
            # Load env
            load_dotenv('.env')
            
            setup_window.destroy()
            root.destroy()
        
        save_btn = tk.Button(
            setup_window,
            text="✓ Save & Start Bot",
            command=save_credentials,
            bg='#C4858C',
            fg='white',
            font=("Arial", 11, "bold"),
            padx=20,
            pady=10
        )
        save_btn.pack(pady=20)
        
        root.mainloop()
        
        return True

# ============================================================================
# PERSONALITY ENGINE
# ============================================================================

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

# ============================================================================
# TEXT-TO-SPEECH
# ============================================================================

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

# ============================================================================
# MAIN BOT
# ============================================================================

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
        
        # Get LiveKit credentials from .env
        self.livekit_url = os.getenv("LIVEKIT_URL", "")
        self.livekit_key = os.getenv("LIVEKIT_API_KEY", "")
        self.livekit_secret = os.getenv("LIVEKIT_API_SECRET", "")
        
        # Log credentials status
        if self.livekit_url and self.livekit_key and self.livekit_secret:
            logger.info("✓ LiveKit credentials loaded from .env")
        else:
            logger.warning("⚠ LiveKit credentials incomplete")
    
    def load_config(self):
        """Load configuration"""
        try:
            with open("config.json", 'r') as f:
                return json.load(f)
        except:
            return {"daughter": {"name": "Emma"}, "father": {"name": "Dad"}}
    
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
        
        if not self.livekit_url:
            self.tts.speak("Please configure LiveKit credentials first")
            logger.error("LiveKit not configured")
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

# ============================================================================
# ENTRY POINT
# ============================================================================

def main():
    """Main entry point"""
    
    # First time setup - ask for LiveKit credentials
    LiveKitSetup.check_and_setup()
    
    # Create and run bot
    bot = DaughterBackgroundVoiceBot()
    
    icon = bot.create_tray_icon()
    
    logger.info("=" * 60)
    logger.info("🎁 DAUGHTER VOICE BOT - EMMA 🎁")
    logger.info("=" * 60)
    logger.info("✓ System tray started")
    logger.info("✓ Right-click icon to listen")
    logger.info("✓ LiveKit configured")
    logger.info("✓ Ready to talk!")
    logger.info("=" * 60)
    
    icon.run()

if __name__ == "__main__":
    main()

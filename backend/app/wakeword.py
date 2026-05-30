import numpy as np
from openwakeword.model import Model
from app.config import settings
from app.utils.logger import logger

class WakeWordDetector:
    def __init__(self):
        # OpenWakeWord expects 16khz, 16-bit PCM audio.
        self.owwModel = Model(wakeword_models=[settings.wakeword_model], inference_framework="onnx")
        self.threshold = settings.threshold
        self.debounce_frames = settings.debounce_frames
        self.cooldown = 0
        logger.info(f"Initialized WakeWordDetector with model: {settings.wakeword_model}")

    def process_audio(self, audio_data: bytes) -> bool:
        """
        Process incoming raw PCM audio bytes.
        Returns True if wake word is detected and cooldown has expired.
        """
        if self.cooldown > 0:
            self.cooldown -= 1
            
        # Convert bytes to numpy array (16-bit PCM)
        audio_array = np.frombuffer(audio_data, dtype=np.int16)
        
        # OpenWakeWord processes in chunks, but we can pass the array directly
        prediction = self.owwModel.predict(audio_array)
        
        # openWakeWord returns a dictionary with model names as keys and scores as values
        for model_name, score in prediction.items():
            if score > self.threshold:
                if self.cooldown == 0:
                    logger.info(f"Wake word detected! Model: {model_name}, Score: {score}")
                    self.cooldown = self.debounce_frames
                    return True
                else:
                    logger.debug("Wake word detected but in cooldown.")
                    
        return False

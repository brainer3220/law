import whisper
import threading

class WhisperModel:
    _instance = None
    _lock = threading.Lock()

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            # Ensure the model is loaded exactly once in multi-threaded environments.
            with cls._lock:
                if cls._instance is None:
                    # Load the model. 'base' is a good balance for testing.
                    cls._instance = whisper.load_model("base")
        return cls._instance

def preload_whisper_model() -> None:
    """Preload the Whisper model at application startup to avoid first-request latency."""
    WhisperModel.get_instance()
def transcribe_audio_file(audio_path: str) -> dict:
    """
    Transcribe audio file using OpenAI Whisper.
    """
    try:
        model = WhisperModel.get_instance()
        result = model.transcribe(audio_path)
        return {
            "text": result["text"],
            "segments": result["segments"],
            "language": result["language"],
        }
    except Exception as e:
        # In a real app, you might want to log the error here
        raise e

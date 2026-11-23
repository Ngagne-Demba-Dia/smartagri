"""WolofVoiceService — ASR Wolof (Whisper/Wav2Vec2), TTS Wolof (SpeechT5) et interprétation agricole."""

import base64
import io
import time
import wave
from pathlib import Path
from typing import Any, Dict, Optional

from .wolof_lexicon import interpret_wolof_text


DEFAULT_ASR_MODEL = "M9and2M/whisper-small-wolof"
DEFAULT_TTS_MODEL = "bilalfaye/speecht5_tts-wolof-v0.2"


class WolofVoiceService:
    """Service vocal Wolof pour les messages audio SmartAgri."""

    def __init__(
        self,
        asr_model_id: str = DEFAULT_ASR_MODEL,
        tts_model_id: str = DEFAULT_TTS_MODEL,
        asr_pipeline=None,
        tts_pipeline=None,
    ):
        self.asr_model_id = asr_model_id
        self.tts_model_id = tts_model_id
        self._asr = asr_pipeline
        self._tts = tts_pipeline
        self.load_error: Optional[str] = None

    def _ensure_asr(self) -> bool:
        if self._asr is not None:
            return True
        try:
            from transformers import pipeline

            self._asr = pipeline("automatic-speech-recognition", model=self.asr_model_id)
            return True
        except Exception as exc:
            self.load_error = f"ASR Wolof indisponible ({self.asr_model_id}): {exc}"
            return False

    def _ensure_tts(self) -> bool:
        if self._tts is not None:
            return True
        try:
            from transformers import pipeline

            self._tts = pipeline("text-to-speech", model=self.tts_model_id)
            return True
        except Exception as exc:
            self.load_error = f"TTS Wolof indisponible ({self.tts_model_id}): {exc}"
            return False

    @staticmethod
    def _wav_info(audio_bytes: bytes) -> Dict[str, Any]:
        try:
            with wave.open(io.BytesIO(audio_bytes), "rb") as wf:
                return {
                    "valid_wav": True,
                    "channels": wf.getnchannels(),
                    "sample_rate": wf.getframerate(),
                    "frames": wf.getnframes(),
                }
        except Exception:
            return {"valid_wav": False, "bytes": len(audio_bytes)}

    def transcribe(
        self,
        audio_bytes: bytes,
        content_type: str = "audio/wav",
        duration_s: float = 1.0,
        language_hint: str = "wo",
        load_model: bool = False,
    ) -> Dict[str, Any]:
        t0 = time.perf_counter()
        info = self._wav_info(audio_bytes)
        if self._asr is None and load_model:
            self._ensure_asr()

        if self._asr is None:
            return {
                "abstained": True,
                "reason": self.load_error or "Modèle ASR Wolof non préchargé (passer load_model=True pour télécharger ~970 Mo)",
                "text": "",
                "language": language_hint,
                "audio_info": info,
                "model_version": self.asr_model_id,
                "latency_ms": round((time.perf_counter() - t0) * 1000.0, 3),
            }

        asr_input: Any = audio_bytes
        if info.get("valid_wav"):
            import numpy as np

            with wave.open(io.BytesIO(audio_bytes), "rb") as wf:
                sr = wf.getframerate()
                pcm = np.frombuffer(wf.readframes(wf.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
                if wf.getnchannels() > 1:
                    pcm = pcm.reshape(-1, wf.getnchannels()).mean(axis=1)
                asr_input = {"array": pcm, "sampling_rate": sr}

        out = self._asr(asr_input)
        text = out.get("text", "").strip() if isinstance(out, dict) else str(out).strip()
        interp = interpret_wolof_text(text)
        return {
            "abstained": False,
            "text": text,
            "normalized_fr": interp["normalized_fr"],
            "detected_crop": interp["detected_crop"],
            "language": language_hint,
            "confidence": 0.85 if text else 0.0,
            "audio_info": info,
            "model_version": self.asr_model_id,
            "latency_ms": round((time.perf_counter() - t0) * 1000.0, 3),
        }

    def synthesize(self, text: str, load_model: bool = False) -> Dict[str, Any]:
        t0 = time.perf_counter()
        if self._tts is None and load_model:
            self._ensure_tts()
        if self._tts is None:
            return {
                "abstained": True,
                "reason": self.load_error or "Modèle TTS Wolof non préchargé",
                "audio_base64": "",
                "content_type": "audio/wav",
                "model_version": self.tts_model_id,
                "latency_ms": round((time.perf_counter() - t0) * 1000.0, 3),
            }
        import torch

        spk = torch.full((1, 512), 0.04, dtype=torch.float32)
        spk = spk / spk.norm(dim=-1, keepdim=True)
        try:
            out = self._tts(text, forward_params={"speaker_embeddings": spk})
        except TypeError:
            out = self._tts(text)
        import numpy as np

        audio = np.asarray(out["audio"], dtype=np.float32).ravel()
        sr = int(out.get("sampling_rate", 16000))
        pcm = (np.clip(audio, -1.0, 1.0) * 32767.0).astype(np.int16)
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sr)
            wf.writeframes(pcm.tobytes())
        return {
            "abstained": False,
            "audio_base64": base64.b64encode(buf.getvalue()).decode("ascii"),
            "content_type": "audio/wav",
            "sample_rate": sr,
            "model_version": self.tts_model_id,
            "latency_ms": round((time.perf_counter() - t0) * 1000.0, 3),
        }

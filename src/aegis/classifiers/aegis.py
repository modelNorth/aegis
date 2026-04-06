"""Aegis ML-based classifier using PyTorch."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

import torch
import torch.nn as nn

from aegis.classifiers.base import BaseClassifier, ClassifierResult

logger = logging.getLogger(__name__)

DEFAULT_MODEL_PATH = "/app/models/aegis_classifier.pt"
MAX_SEQ_LENGTH = 512


class AegisClassifierModel(nn.Module):
    """Neural network for prompt injection classification."""

    def __init__(self, vocab_size: int = 50000, embedding_dim: int = 256, hidden_dim: int = 128) -> None:
        super().__init__()
        self.embedding = nn.Embedding(vocab_size, embedding_dim, padding_idx=0)
        self.lstm = nn.LSTM(embedding_dim, hidden_dim, num_layers=2, batch_first=True, dropout=0.3)
        self.attention = nn.MultiheadAttention(hidden_dim, num_heads=4, batch_first=True)
        self.fc = nn.Sequential(
            nn.Linear(hidden_dim, 64),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(64, 2),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        embedded = self.embedding(x)
        lstm_out, _ = self.lstm(embedded)
        attn_out, _ = self.attention(lstm_out, lstm_out, lstm_out)
        pooled = torch.mean(attn_out, dim=1)
        return self.fc(pooled)


class AegisTokenizer:
    """Simple tokenizer for the Aegis classifier."""

    def __init__(self, vocab_size: int = 50000) -> None:
        self.vocab_size = vocab_size
        self.word_to_idx: dict[str, int] = {"<PAD>": 0, "<UNK>": 1}
        self.idx_to_word: dict[int, str] = {0: "<PAD>", 1: "<UNK>"}

    def encode(self, text: str, max_length: int = MAX_SEQ_LENGTH) -> list[int]:
        """Encode text to token indices."""
        words = text.lower().split()[:max_length]
        indices = []
        for word in words:
            if word not in self.word_to_idx:
                idx = len(self.word_to_idx)
                if idx < self.vocab_size:
                    self.word_to_idx[word] = idx
                    self.idx_to_word[idx] = word
            indices.append(self.word_to_idx.get(word, 1))  # 1 is <UNK>

        # Pad to max_length
        while len(indices) < max_length:
            indices.append(0)
        return indices


class AegisClassifier(BaseClassifier):
    """PyTorch-based classifier for prompt injection detection."""

    def __init__(
        self,
        model_path: str | None = None,
        device: str | None = None,
    ) -> None:
        self._model_path = model_path or os.getenv("AEGIS_MODEL_PATH", DEFAULT_MODEL_PATH) or ""
        self._device = self._resolve_device(device)
        self._model: nn.Module | None = None
        self._tokenizer = AegisTokenizer()
        self._loaded = False
        self._load_model()

    def _resolve_device(self, device: str | None) -> torch.device:
        """Resolve the compute device."""
        if device == "auto" or device is None:
            return torch.device("cuda" if torch.cuda.is_available() else "cpu")
        return torch.device(device)

    def _load_model(self) -> bool:
        """Lazy load the model."""
        if self._loaded:
            return self._model is not None

        self._loaded = True
        model_file = Path(self._model_path)

        if not model_file.exists():
            logger.warning("Aegis model file not found at %s", self._model_path)
            return False

        try:
            self._model = AegisClassifierModel()
            checkpoint: dict = torch.load(model_file, map_location=self._device, weights_only=True)  # type: ignore[no-any-return]
            self._model.load_state_dict(checkpoint)
            self._model.to(self._device)
            self._model.eval()
            logger.info("Aegis classifier loaded from %s on %s", self._model_path, self._device)
            return True
        except Exception as exc:
            logger.error("Failed to load Aegis model: %s", exc)
            self._model = None
            return False

    def is_available(self) -> bool:
        """Check if the classifier is available."""
        return self._load_model()

    def predict(self, text: str) -> ClassifierResult:
        """Predict using the neural classifier."""
        if not self._load_model() or self._model is None:
            # Return safe fallback if model unavailable
            return ClassifierResult(
                score=0.0,
                label="safe",
                confidence=0.5,
                matched_patterns=["model_unavailable"],
            )

        try:
            tokens = self._tokenizer.encode(text)
            input_tensor = torch.tensor([tokens], dtype=torch.long, device=self._device)

            with torch.no_grad():
                outputs = self._model(input_tensor)
                probs = torch.softmax(outputs, dim=1)
                injection_prob = float(probs[0][1].cpu())
                safe_prob = float(probs[0][0].cpu())

            label = "injection" if injection_prob > 0.5 else "safe"
            confidence = max(injection_prob, safe_prob)

            # Calculate score based on injection probability
            score = injection_prob

            patterns = []
            if injection_prob > 0.7:
                patterns.append(f"high_injection_probability:{injection_prob:.3f}")
            elif injection_prob > 0.5:
                patterns.append(f"moderate_injection_probability:{injection_prob:.3f}")

            return ClassifierResult(
                score=score,
                label=label,
                confidence=confidence,
                matched_patterns=patterns,
            )

        except Exception as exc:
            logger.error("Prediction failed: %s", exc)
            return ClassifierResult(
                score=0.0,
                label="safe",
                confidence=0.0,
                matched_patterns=["prediction_error"],
            )

    def health_check(self) -> dict[str, Any]:
        """Perform health check on the classifier."""
        available = self._load_model()
        return {
            "available": available,
            "type": "AegisClassifier",
            "model_path": self._model_path,
            "device": str(self._device),
            "model_loaded": self._model is not None,
            "vocab_size": self._tokenizer.vocab_size if hasattr(self, "_tokenizer") else None,
        }

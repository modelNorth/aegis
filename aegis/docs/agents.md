# Aegis Agent System Documentation

## Overview

Aegis uses a multi-agent CrewAI pipeline where each agent specializes in a specific detection strategy. All agents extend `BaseAegisAgent` and integrate with Mem0 for persistent memory.

---

## Agent Pipeline

```
Content → Processors → [Structural | Semantic | Intent | Visual | Behavioral] → Verdict → Memory
```

Each analysis agent runs independently and produces an `AgentFinding` with:
- `score`: 0.0-1.0 risk score
- `signals`: List of detected signal strings
- `explanation`: Human-readable description
- `metadata`: Agent-specific additional data

---

## Agents

### 1. Structural Agent (`structural`)

**Weight:** 20%

Detects hidden content and steganographic injection vectors:

- **HTML**: Hidden DOM elements (CSS display:none, visibility:hidden, aria-hidden), zero-width characters, suspicious HTML comments, CSS off-screen tricks, suspicious data attributes
- **PDF**: Embedded JavaScript, embedded files, suspicious PDF metadata keys
- **Image**: LSB steganography detection, suspicious EXIF/metadata
- **Text**: Zero-width characters, homoglyph detection, encoding tricks (RTL override, URL encoding)

### 2. Semantic Agent (`semantic`)

**Weight:** 35% (highest)

Rule-based classifier (Phase 2: ML integration point):

- Matches 20+ regex patterns for known injection phrases
- Detects special LLM tokens (`[INST]`, `<<SYS>>`, `<|system|>`)
- Identifies sequential instruction patterns
- Detects multilingual obfuscation
- Queries Mem0 for known patterns

**Phase 2 Integration:**
```python
# PHASE2: Replace RuleBasedClassifier with:
self._classifier = AegisClassifier(model_path=config.classifier_model_path)
```

### 3. Intent Agent (`intent`)

**Weight:** 25%

Semantic similarity using `all-MiniLM-L6-v2` embeddings:

- Computes cosine similarity against 10 known injection anchor phrases
- Threshold: 0.65 similarity triggers detection
- Multiple anchor matches increase confidence
- Cross-references Mem0 for memorized patterns

### 4. Visual Agent (`visual`)

**Weight:** 10%

Image and PDF visual content analysis:

- OCR-extracted text scanned for injection patterns
- Character substitution detection
- PDF visual metadata analysis
- Image LSB steganography and EXIF injection

### 5. Behavioral Agent (`behavioral`)

**Weight:** 10%

Social engineering and manipulation pattern detection:

- 8 behavioral pattern categories: exfiltration, system access, credential harvest, social engineering, authority impersonation, urgency manipulation, reward manipulation, threat coercion
- Session escalation detection (tracks repeated attempts)
- Linguistic feature analysis: imperative density, negation density, instruction length

### 6. Verdict Agent (`verdict`)

**Weight:** N/A (aggregator)

Score aggregation and final decision:

- Weighted average of all agent scores
- Contextual boosts for multi-agent agreement
- Confidence calibration based on score variance
- Maps aggregate score to risk level

### 7. Memory Agent (`memory`)

**Weight:** N/A (post-processing)

Persistent learning after each scan:

- Stores scan summary to session memory
- Stores high-risk patterns to threat database memory
- Updates feedback memory from human corrections

---

## Agent Weights

| Agent | Weight | Rationale |
|-------|--------|-----------|
| Semantic | 35% | Most reliable for explicit injection text |
| Intent | 25% | Catches paraphrased/obfuscated attempts |
| Structural | 20% | Critical for hidden content vectors |
| Visual | 10% | Image-based attacks are less common |
| Behavioral | 10% | Social engineering context |

---

## Memory Architecture

Each agent uses Mem0 with two memory pools:

1. **Session memory** (`user_id=session_id`): Per-session episodic memory
2. **System memory** (`user_id=aegis-system`): Global pattern memory
3. **Threat database** (`user_id=aegis-threat-db`): High-risk injection patterns
4. **Pattern database** (`user_id=aegis-pattern-db`): Agent-specific patterns
5. **Feedback database** (`user_id=aegis-feedback-db`): Human correction signals

---

## Adding a New Agent

1. Create `src/aegis/agents/myagent.py` extending `BaseAegisAgent`
2. Set `name`, `role`, `goal`, `backstory` class attributes
3. Implement `analyze(content, context) -> AgentFinding`
4. Add to `AGENT_WEIGHTS` in `verdict.py`
5. Instantiate in `AegisCrew.__init__()` and add to `_run_analysis_agents()`

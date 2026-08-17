# PICK Native Engine Architecture

```
User
  ↓
PICK Web
  ↓
Question Orchestrator
  ↓
Memory / Search / Coding Context
  ↓
Provider Router
  ├─ PICK Native Transformer
  └─ Ollama fallback
```

Native training:

```
Approved PICK conversations
  ↓
pick_training.jsonl
  ↓
Corpus builder
  ↓
SentencePiece tokenizer training
  ↓
ConversationDataset
  ↓
PICK Decoder-only Transformer
  ↓
AdamW deep learning
  ↓
model_latest.pt
  ↓
PICK Native Engine HTTP server
```

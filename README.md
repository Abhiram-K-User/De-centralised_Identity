# DID++ Decentralized Biometric Identity System

A fully decentralized multi-modal biometric identity system that eliminates local databases by utilizing **IPFS** for storage and **Ethereum Sepolia** for state management.

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    DID++ System Architecture                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐       │
│  │  Face Image  │    │ Voice Audio  │    │ ID Document  │       │
│  │   (~1.5MB)   │    │   (~1.5MB)   │    │   (~1MB)     │       │
│  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘       │
│         │                   │                   │                │
│         ▼                   ▼                   ▼                │
│  ┌─────────────────────────────────────────────────────┐        │
│  │              ML Processing Engine                    │        │
│  │  • ArcFace (512-D face embedding)                   │        │
│  │  • ECAPA-TDNN (192-D voice embedding)               │        │
│  │  • EasyOCR + ArcFace (640-D document embedding)     │        │
│  └─────────────────────────┬───────────────────────────┘        │
│                            │                                     │
│                            ▼                                     │
│  ┌─────────────────────────────────────────────────────┐        │
│  │           AES-256-CBC Encryption                     │        │
│  │  • Unique 16-byte IV per session                    │        │
│  │  • PKCS7 padding                                    │        │
│  └─────────────────────────┬───────────────────────────┘        │
│                            │                                     │
│                            ▼                                     │
│  ┌─────────────────────────────────────────────────────┐        │
│  │           Encrypted Metadata JSON (~5KB)             │        │
│  │  {                                                   │        │
│  │    "encrypted_face_embedding": "...",               │        │
│  │    "encrypted_voice_embedding": "...",              │        │
│  │    "encrypted_doc_data": "...",                     │        │
│  │    "identity_hash": "..."                           │        │
│  │  }                                                   │        │
│  └─────────────────────────┬───────────────────────────┘        │
│                            │                                     │
│              ┌─────────────┴─────────────┐                      │
│              ▼                           ▼                      │
│  ┌──────────────────────┐   ┌──────────────────────┐           │
│  │   IPFS (Pinata)      │   │  Ethereum Sepolia    │           │
│  │                      │   │                      │           │
│  │  Stores encrypted    │   │  Stores:             │           │
│  │  metadata (~5KB)     │   │  • DID → CID mapping │           │
│  │                      │   │  • Identity hash     │           │
│  │  Returns: CID        │   │    (32 bytes)        │           │
│  │  (Content ID)        │   │  • Verification logs │           │
│  └──────────────────────┘   └──────────────────────┘           │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘

Data Reduction Pipeline:
~4MB raw biometrics → ~5KB IPFS metadata → 32-byte blockchain hash
           ≈800x reduction        ≈150x reduction
                    Total: ~125,000x reduction
```

## 📋 Features

### Decentralized Storage
- **IPFS**: Encrypted biometric metadata stored on IPFS via Pinata
- **Ethereum Sepolia**: Immutable registry of DIDs, CIDs, and identity hashes
- **No Local Database**: All data is stored on decentralized infrastructure

### Multi-Modal Biometrics
- **Face Recognition**: 512-D ArcFace embeddings via InsightFace
- **Voice Recognition**: 192-D ECAPA-TDNN embeddings via SpeechBrain
- **Document Verification**: OCR + face extraction from ID documents

### Security
- **AES-256-CBC Encryption**: All biometric data encrypted before leaving the server
- **Unique IVs**: 16-byte initialization vector per session
- **In-Memory Processing**: Decrypted data never written to disk

### Smart Contracts
- **DIDRegistry**: Maps DIDs to IPFS CIDs and identity hashes
- **VerificationLog**: Immutable audit trail of verification events

## 🚀 Quick Start

### 1. Clone and Install

```bash
cd DID_Ishaan_Abhiram

# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
# Copy example config
copy .env.example .env  # Windows
# cp .env.example .env  # Linux/Mac

# Edit .env with your credentials:
# - ALCHEMY_KEY: Get from https://alchemy.com
# - PINATA_JWT: Get from https://pinata.cloud
# - MASTER_KEY: Generate with: python -c "import secrets; print(secrets.token_hex(32))"
# - PRIVATE_KEY: Your Sepolia wallet private key
```

### 3. Deploy Smart Contracts

Deploy the contracts in `contracts/` to Sepolia using Remix, Hardhat, or Foundry:

```solidity
// 1. Deploy DIDRegistry.sol first
// 2. Deploy VerificationLog.sol with DIDRegistry address
// 3. Update .env with contract addresses
```

### 4. Run the Backend

```bash
python -m app.main
# or
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 5. Run the Frontend

```bash
cd frontend
npm install
npm run dev
```

## 📡 API Endpoints

### Registration
```
POST /api/register
- Uploads: face (JPEG), voice (WAV/WebM), id_doc (JPEG)
- Returns: DID, IPFS CID, identity hash, blockchain TX
```

### Verification
```
POST /api/verify
- Form data: did, face, voice, id_doc (optional)
- Process: Blockchain → IPFS → Decrypt → Compare
- Returns: Verification scores, confidence level, blockchain TX
```

### History
```
GET /api/user/{did}
- Queries blockchain event logs
- Returns: Full timeline of registration and verification events
```

### Status
```
GET /api/health
GET /api/config
GET /api/status
```

## 🔐 Smart Contracts

### DIDRegistry.sol
```solidity
function registerDID(string did, string metadataCID, bytes32 identityHash)
function getMetadataCID(string did) returns (string)
function getDIDRecord(string did) returns (DIDRecord)
```

### VerificationLog.sol
```solidity
function logVerification(string did, bytes32 verificationHash, string metadataCID, uint8 confidenceLevel, bool success)
function getVerificationCount(string did) returns (uint256)
function getRecentVerifications(string did, uint256 limit) returns (VerificationRecord[])
```

## 📊 Data Reduction Pipeline

| Stage | Size | Reduction |
|-------|------|-----------|
| Raw Biometrics | ~4 MB | - |
| ML Embeddings | ~5 KB | 800x |
| Encrypted IPFS | ~5 KB | 800x |
| Blockchain Hash | 32 bytes | ~125,000x |

## 🔧 Configuration

### Biometric Weights
```env
FACE_WEIGHT=0.40    # 40% face contribution
VOICE_WEIGHT=0.35   # 35% voice contribution
DOC_WEIGHT=0.25     # 25% document contribution
```

### Verification Threshold
```env
VERIFICATION_THRESHOLD=0.75  # 75% minimum for successful verification
```

## 📁 Project Structure

```
DID_Ishaan_Abhiram/
├── app/
│   ├── __init__.py
│   ├── config.py           # Configuration management
│   ├── main.py             # FastAPI application
│   ├── routes/
│   │   ├── registration.py # Registration endpoint
│   │   ├── verification.py # Verification endpoint
│   │   └── history.py      # History endpoint
│   └── services/
│       ├── blockchain.py   # Ethereum integration
│       ├── encryption.py   # AES-256-CBC encryption
│       ├── ipfs.py         # Pinata IPFS integration
│       └── ml_engine.py    # Biometric processing
├── contracts/
│   ├── DIDRegistry.sol     # DID registry contract
│   └── VerificationLog.sol # Verification log contract
├── frontend/
│   └── src/
│       ├── App.jsx
│       ├── pages/
│       │   ├── RegisterPage.jsx
│       │   ├── VerifyPage.jsx
│       │   └── HistoryPage.jsx
│       └── components/
├── .env.example
├── requirements.txt
└── README.md
```

## 🛡️ Security Considerations

1. **Master Key**: Store securely, never commit to version control
2. **Private Key**: Use testnet wallets only, never mainnet keys
3. **IPFS Data**: All data encrypted before upload
4. **In-Memory Only**: Decrypted biometrics never touch disk

## 📜 License

MIT License - See LICENSE file for details.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Submit a pull request

---

**DID++ v2.0** - Fully Decentralized Biometric Identity
# DID_Ver3
# DID_Ver3

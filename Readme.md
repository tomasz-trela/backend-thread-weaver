# 🧵 Thread-Weaver

This backend application allows users to store spoken statements (e.g., interview or meeting transcripts) and later search them using both **semantic search** (meaning-based) and **full-text search** (exact words/phrases). It's designed to help quickly find relevant parts of conversations or spoken content.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 📚 Table of Contents

1. [About The Project](#about-the-project)
2. [Tech Stack](#tech-stack)
3. [Getting Started](#getting-started)
   - [Prerequisites](#prerequisites)
   - [Installation](#installation)
4. [API Documentation](#api-documentation)
5. [Running Tests](#running-tests)
6. [Project Structure](#project-structure)

## 🧠 About The Project

**Thread-Weaver** is a FastAPI-based Python backend that processes audio recordings and makes them searchable using AI. It's built to help users make sense of large volumes of spoken content—like meetings, interviews, or podcasts—by providing powerful search capabilities.

### 🔧 Core Features

- Accepts and processes audio uploads.
- Transcribes audio using [Whisper-turbo](https://github.com/WhisperTurbo).
- Performs speaker diarization with [pyannote-audio](https://github.com/pyannote/pyannote-audio).
- Embeds utterances using Google's Embedding API.
- Stores transcript embeddings in a PostgreSQL database with [pgvector](https://github.com/pgvector/pgvector).
- Supports:
  - ✅ **Semantic Search**
  - ✅ **Full-Text Search**
  - ✅ **Hybrid Search** (combined)

This monolithic app is ideal for AI-driven audio indexing and retrieval use cases.

## 🛠 Tech Stack

- **Language:** Python 3.12+
- **Framework:** FastAPI
- **Database:** PostgreSQL + pgvector
- **Transcription:** Whisper-turbo
- **Speaker Diarization:** pyannote-audio
- **Embeddings:** Google AI Studio
- **ORM:** SQLAlchemy
- **Testing:** Pytest
- **Containerization:** Docker

---

## 🚀 Getting Started

Follow these instructions to get a copy of the project up and running locally for development and testing.

### 📦 Prerequisites

Ensure you have the following installed:

- [Python 3.12+](https://www.python.org/)
- [PostgreSQL](https://www.postgresql.org/)
- [Docker](https://www.docker.com/) (Optional, for database & API containerization)
- [ffmpeg](https://ffmpeg.org/) (for audio processing)

---

### ⚙️ Installation

#### Clone the repository

```bash
git clone https://github.com/tomasz-trela/backend-thread-weaver.git
cd backend-thread-weaver
````

1. Create a new file named `.env` in the root directory.
2. Add the following content and fill in your secrets:

```env
DATABASE_URL=<your-database-url>
GOOGLE_AI_STUDIO_API_KEY=<your-google-ai-api-key>
SPEAKER_DIARIZATION_TOKEN=<your-diarization-api-key>
```

#### 🔄 Option 1: With Docker

```bash
docker-compose up --build
```

#### 🖥️ Option 2: Manual Setup

Install dependencies:

```bash
pip install -r requirements.txt
```

Install ffmpeg (platform-specific instructions required), then run the app:

```bash
python main.py
```

## 📖 API Documentation

Once the application is running, navigate to:

📎 [http://localhost:8000/docs](http://localhost:8000/docs)

This Swagger UI provides an interactive interface to explore and test all API endpoints.

## 🧪 Running Tests

> Coming soon (or describe how to run with pytest if already supported)

## 📝 License

Distributed under the MIT License. See [`LICENSE`](LICENSE) for more information.

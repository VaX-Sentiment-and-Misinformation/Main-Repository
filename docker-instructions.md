# Project Dockerization Blueprint & Reference Guide

This document serves as a complete reference guide for converting our full-stack application (FastAPI + Next.js) into an isolated, microservice-based Docker architecture. 

---

## 🐋 Core Conceptual Summary

Instead of running Python scripts, Node engines, and database systems directly on your physical operating system, **Docker isolates your components into distinct, independent "mini-computers" called Containers.**

### Why This Architecture Wins for Machine Learning:
1. **No Dependency Hell:** If Model 1 requires an old package (`protobuf==3.20`) and Model 2 requires a brand-new one (`protobuf==5.27`), they are sealed in separate containers. They can never conflict or crash your machine.
2. **Independent Scaling:** If an inference script consumes 100% CPU running a heavy prediction, only that specific model container slows down. Your core Web API container remains perfectly responsive to web traffic.
3. **"Works on My Machine" Guarantee:** Your local system stays clean. Your team doesn't need to manually install Python packages, C++ dependencies, or database binaries. Docker replicates the exact required Linux runtime environment instantly on any machine.

---

## 📂 Target Directory Structure

To deploy individual containers for each machine learning model, organize your project workspace into isolated sub-directories within the main `backend/` folder:

```text
my-app/
├── .gitignore               # Ignores .env, venv/, node_modules/, and cache folders
├── docker-compose.yml       # Central command orchestrator for all containers
├── README.md                # This reference guide
├── backend/
│   ├── main_api/            # Core Web Server (SQLModel, PostgreSQL connections, Auth)
│   │   ├── main.py
│   │   ├── requirements.txt
│   │   └── Dockerfile
│   └── model_sentiment/     # Dedicated Machine Learning Microservice
│       ├── app.py           # FastAPI wrapper pulling/serving the ML model
│       ├── requirements.txt # AI dependencies (torch, transformers, fastapi)
│       └── Dockerfile       # Instruction manual to build this specific model image
└── frontend/                # Next.js web application (Node.js engine)
```

---

## 📋 The 3 Blueprint Files to Initialize

### 1. The Model Microservice (`backend/model_sentiment/app.py`)
This script isolates your heavy machine learning logic from the main application. It uses a lifespan block to load your BERT model into system RAM **exactly once** on container startup.

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from pydantic import BaseModel
from transformers import pipeline

models = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Loads BERT model parameters directly into the container RAM on boot
    models["nlp_pipeline"] = pipeline("sentiment-analysis", model="bert-base-uncased")
    yield
    models.clear()

app = FastAPI(lifespan=lifespan)

class InferencePayload(BaseModel):
    text: str

@app.post("/predict")
def predict_sentiment(payload: InferencePayload):
    classifier = models["nlp_pipeline"]
    return {"prediction": classifier(payload.text)}
```

### 2. The Container Recipe (`backend/model_sentiment/Dockerfile`)
This script acts as the instruction manual telling Docker how to build the standalone environment for your sentiment model.

```dockerfile
# Step 1: Base the environment on a lightweight Linux with Python 3.11 pre-installed
FROM python:3.11-slim

# Step 2: Establish the folder workspace inside the container
WORKDIR /app

# Step 3: Copy the package manifests and execute installation internally
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Step 4: Snapshot your specific model python files into the container
COPY . .

# Step 5: Punch a hole through the container firewall to allow communication
EXPOSE 8001

# Step 6: Define the final runtime execution command
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8001"]
```

### 3. The Central Orchestrator (`my-app/docker-compose.yml`)
This file links your database, your web server, and your machine learning models together on a shared internal virtual network.

```yaml
version: '3.8'

services:
  # 1. Isolated Database Engine
  postgres_db:
    image: postgres:15-alpine
    container_name: postgres_db
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: securepassword123
      POSTGRES_DB: app_database
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  # 2. Main Web API Backend
  main_api:
    build: ./backend/main_api
    container_name: main_api
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://postgres:securepassword123@postgres_db:5432/app_database
      - SENTIMENT_MODEL_URL=http://model_sentiment:8001/predict
    depends_on:
      - postgres_db

  # 3. Dedicated ML Microservice
  model_sentiment:
    build: ./backend/model_sentiment
    container_name: model_sentiment
    ports:
      - "8001:8001"
    volumes:
      # Local volume caching ensures BERT weights stay on your local disk
      # Restarts take 2 seconds instead of downloading hundreds of megabytes repeatedly
      - hf_cache:/root/.cache/huggingface

volumes:
  postgres_data:
  hf_cache:
```

---

## 💻 Essential Terminal Commands

When you are ready to boot up, run your updates, or stop your development session, execute these commands from your root project folder (`my-app/`):

* **Build and boot all containers simultaneously:**
  ```bash
  docker compose up --build
  ```
* **Hot-reload changes to your Python ML scripts:**
  If you modify code inside `backend/model_sentiment/app.py`, you can tell Docker to update *only* that specific model container without interrupting your running database or frontend website:
  ```bash
  docker compose up -d --build model_sentiment
  ```
* **Gracefully shut down everything and clear system RAM:**
  ```bash
  docker compose down
  ```

# Full-Stack FastAPI + Next.js Project

Welcome to the project! This repository contains a split-architecture application featuring a Python FastAPI backend (configured with SQLModel and PostgreSQL) and a React Next.js frontend.

---

## 🚀 Quick Start Guide

Follow these steps to get the entire project running locally on your machine.

### Prerequisites
Ensure you have the following installed locally:
* **Python** (v3.10 or higher)
* **Node.js** (v18 or higher) & npm
* **PostgreSQL** instance running locally

---

## 🛠️ 1. Backend Setup (FastAPI)

Open a terminal window and navigate to the backend directory.

```bash
cd backend
```

### 1.1 Create and Activate Virtual Environment
```bash
# Windows
python -m venv venv
.\venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

### 1.2 Install Python Dependencies
```bash
pip install -r .\main_api\requirements.txt
```

### 1.3 Configure Environment Variables
Create a local `.env` file inside the `backend/` folder:
```bash
touch .env
```
Open `backend/.env` and add your local PostgreSQL connection configuration string:
```env
DATABASE_URL="postgresql://<your_username>:<your_password>@localhost:5432/<your_database_name>"
```
*(Note: Make sure your target database exists in your PostgreSQL instance before running the app).*

### 1.4 Start the Backend Server
```bash
uvicorn main:app --reload
```
* **API Endpoint:** http://127.0.0.1:8000
* **Interactive Interactive API Documentation:** http://127.0.0

---

## 💻 2. Frontend Setup (Next.js)

Open a **second terminal window**, return to the project root directory, and open the frontend workspace.

```bash
cd frontend
```

### 2.1 Install Node Dependencies
```bash
npm install
```

### 2.2 Start the Development Server
```bash
npm run dev
```
* **Frontend Web Application Interface:** http://localhost:3000

---

## 📦 3. Developer Guidelines & Git Rules

* **Installing Python Packages:** If you install a new backend package, make sure to export the updated list to git using:
  ```bash
  pip freeze > requirements.txt
  ```
* **Environment Files:** Never commit `.env` files. They are globally ignored via the root `.gitignore` configuration rule.

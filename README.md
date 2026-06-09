# Research Contracts Advisor - University of Auckland

## Overview

The **Research Contracts Advisor** is an intelligent agentic AI system designed to assist researchers at the University of Auckland in understanding, analyzing, and navigating complex research contract agreements. This tool leverages advanced AI models combined with Retrieval-Augmented Generation (RAG) to classify contracts into seven agreement types and provide detailed clause-level analysis and highlighting.

### Key Features

- **Intelligent Contract Classification**: Automatically classifies research agreements into seven distinct contract types
- **Clause Extraction & Highlighting**: Identifies and highlights critical clauses and terms within contracts using contextual rules
- **PDF Analysis**: Seamlessly extracts and processes text from research contract PDFs
- **Real-time Feedback**: Provides actionable insights on contract structure and content through a responsive web interface
- **Custom Data Preprocessing**: Adaptable data pipeline that can be modified based on contract structure, specific clauses, and agreement types

---

## ⚠️ Important Policy Notice

**Data Sensitivity & Privacy Compliance**: Research contracts handled by this system contain sensitive intellectual property and institutional agreements. In accordance with **University of Auckland Policy**, contracts **cannot be compromised or exposed**. 

The data preprocessing pipeline can be **customized and extended** to accommodate different contract structures, clause hierarchies, and specific agreement requirements while maintaining strict data integrity and confidentiality standards. All processing is performed locally, and no contract data is stored externally without explicit authorization.

---

## Project Architecture

```
Research-Contracts-Advisor-UoA/
├── backend/                    # FastAPI backend service
│   └── (API endpoints & business logic)
├── frontend-agent/             # React/Node.js frontend interface
│   └── (User-facing UI & components)
├── model_rag.py               # RAG model implementation
├── document_highlight.py       # FastAPI application entry point
├── highlight_fast_api.py      # API route definitions
├── highlight_rules.py         # Contract clause highlighting rules
├── pdf_highlighter.py         # PDF text extraction & processing
├── create_writer.py           # Contract document output generator
├── requirements.txt           # Python dependencies
└── instruction.txt            # Additional setup notes
```

---

# Getting Started

## Prerequisites

Before you begin, ensure you have the following installed on your system:

- **Python 3.9+** (for backend)
- **Node.js 16+ & npm** (for frontend)
- **Git** (for cloning the repository)
- **Visual Studio Code** (recommended IDE)
- **Uvicorn** (FastAPI server - installed via requirements)

---

## Installation & Setup

### Step 1: Fork the Repository

1. Navigate to the [Research-Contracts-Advisor-UoA repository](https://github.com/gokulprazath/Research-Contracts-Advisor-UoA)
2. Click the **Fork** button in the top-right corner
3. This creates your own copy of the repository under your GitHub account

### Step 2: Clone in VS Code

1. **Open VS Code** on your machine
2. Open the **Integrated Terminal** (Ctrl + ` or View → Terminal)
3. Navigate to your desired directory:
   ```bash
   cd path/to/your/projects
   ```
4. Clone your forked repository:
   ```bash
   git clone https://github.com/YOUR-USERNAME/Research-Contracts-Advisor-UoA.git
   ```
   *(Replace `YOUR-USERNAME` with your actual GitHub username)*

5. Open the cloned folder in VS Code:
   ```bash
   cd Research-Contracts-Advisor-UoA
   code .
   ```

### Step 3: Install Backend Dependencies

The backend requires Python packages specified in `requirements.txt`. These include FastAPI, Uvicorn, PDF processing libraries, and AI/ML dependencies.

1. **Open a new terminal in VS Code** (Terminal → New Terminal)
2. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```
   
   This command will:
   - Install FastAPI framework
   - Install Uvicorn ASGI server
   - Install PDF processing libraries (PyPDF2, pdfplumber, etc.)
   - Install LLM & RAG dependencies
   - Install other required Python packages

3. **Wait for installation to complete** (this may take 2-3 minutes depending on your internet speed)

### Step 4: Start the Backend Server

Once dependencies are installed, start the FastAPI backend using Uvicorn with auto-reload enabled:

```bash
uvicorn document_highlight:app --reload
```

**What this does:**
- `uvicorn` - ASGI server that runs your FastAPI application
- `document_highlight:app` - Loads the FastAPI `app` instance from `document_highlight.py`
- `--reload` - Enables hot-reload; the server automatically restarts when you modify code files

**Expected output:**
```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started server process [12345]
INFO:     Started reloader process [12346]
```

✅ **Backend is now running** on `http://localhost:8000`

You can access the **interactive API documentation** at:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Step 5: Install Frontend Dependencies

The frontend is built with React/Node.js and requires npm packages.

1. **Open a new terminal** in VS Code (do NOT close the backend terminal)
2. **Navigate to the frontend directory** (⚠️ This is important - all npm commands must be run inside the `frontend-agent` folder):
   ```bash
   cd frontend-agent
   ```
3. Install npm dependencies:
   ```bash
   npm install
   ```
   
   This command will:
   - Install React and core dependencies
   - Install UI component libraries
   - Install development tools and bundlers
   - Install other frontend packages from `package.json`

4. **Wait for installation to complete** (typically 2-5 minutes)

### Step 6: Start the Frontend Development Server

Once npm dependencies are installed, start the development server:

```bash
npm run dev
```

**What this does:**
- Starts the React development server with hot module reloading
- Compiles JSX and modern JavaScript for the browser
- Enables fast refresh so changes appear instantly without page reload

**Expected output:**
```
  VITE v4.x.x  ready in 234 ms

  ➜  Local:   http://localhost:5173/
  ➜  press h to show help
```

✅ **Frontend is now running** on `http://localhost:5173`

---

## Accessing the Application

Once both servers are running, you have:

| Component | URL | Purpose |
|-----------|-----|---------|
| **Frontend UI** | http://localhost:5173 | User interface for contract analysis |
| **Backend API** | http://localhost:8000 | FastAPI endpoints |
| **API Docs (Swagger)** | http://localhost:8000/docs | Interactive API documentation |
| **API Docs (ReDoc)** | http://localhost:8000/redoc | Alternative API documentation |

Open your browser and navigate to **http://localhost:5173** to start using the Research Contracts Advisor.

---

## Terminal Setup Workflow (Quick Reference)

Here's the complete terminal sequence for a fresh setup:

```bash
# Terminal 1: Backend
cd Research-Contracts-Advisor-UoA
pip install -r requirements.txt
uvicorn document_highlight:app --reload

# Terminal 2: Frontend (new terminal in VS Code)
cd Research-Contracts-Advisor-UoA/frontend-agent
npm install
npm run dev
```

**Keep both terminals open** while developing. Each server will continue running and auto-reload on file changes.

---

## Customizing Data Preprocessing

The contract analysis pipeline is **modular and extensible**. To customize preprocessing for specific contract structures or clauses:

1. **Review `highlight_rules.py`** - Contains clause detection and highlighting logic
2. **Modify `pdf_highlighter.py`** - Adjust text extraction and document parsing
3. **Update `model_rag.py`** - Fine-tune RAG prompts and contract classification logic
4. **Edit `create_writer.py`** - Customize output document formatting

Changes to any of these files will automatically reload in development mode (thanks to `--reload` and `npm run dev`).

---

## Common Issues & Troubleshooting

### Issue: `ModuleNotFoundError: No module named 'fastapi'`
**Solution**: Ensure you ran `pip install -r requirements.txt` in the correct directory

### Issue: `npm install` is slow or fails
**Solution**: Try clearing npm cache and retrying:
```bash
npm cache clean --force
npm install
```

### Issue: Port 8000 or 5173 already in use
**Solution**: Either close the process using that port or specify a different port:
```bash
# For backend (different port):
uvicorn document_highlight:app --reload --port 8001

# For frontend, edit package.json or use:
npm run dev -- --port 5174
```

### Issue: API calls failing from frontend
**Solution**: Ensure both backend and frontend servers are running, and check the API endpoint URLs in your frontend code

---

## Development Guidelines

### Adding New Features
1. Create a new branch: `git checkout -b feature/your-feature-name`
2. Make your changes and test thoroughly
3. Commit with clear messages: `git commit -m "Add detailed description of changes"`
4. Push to your fork and create a Pull Request

### Code Standards
- Follow PEP 8 for Python code
- Use meaningful variable and function names
- Add comments for complex logic
- Test contract processing with sample PDFs before committing

---

## Additional Resources

- **FastAPI Documentation**: https://fastapi.tiangolo.com
- **Uvicorn Documentation**: https://www.uvicorn.org
- **React/Vite Documentation**: https://vitejs.dev
- **University of Auckland Research Support**: [UoA Research Portal]

---

## Support & Contributions

For issues, questions, or suggestions:
1. Check existing GitHub Issues
2. Create a new Issue with detailed description
3. Contact the development team

---

## Contributors

**Core Development Team**: 
- Sri Gokul Prazath
- Moshiur Rahman Rimu
- Sifat Morshed
- Bryant
- Armandarma

**Special Thanks & Acknowledgments**:
- **Prof. Thomas Lacombe** (University of Auckland) - For invaluable guidance and academic oversight throughout this project
- **Chandima** (Account Strategist, Microsoft) - For technical guidance and strategic insights on cloud integration and AI/ML best practices

We deeply appreciate the mentorship, support, and expertise provided by these individuals in shaping this research project.

---

## License

This project is developed for the University of Auckland and follows institutional data governance policies. All research contracts processed by this tool are subject to UoA confidentiality requirements.

---

**Last Updated**: June 2026  
**Maintainer**: Gokul Prazath  
**Status**: Active Development
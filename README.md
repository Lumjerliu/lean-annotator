# Lean Prover Annotator

A web-based tool for formalizing mathematical problems in Lean 4 with AI assistance.

## Features

- **Problem Database**: SQLite database storing math problems and their formalizations
- **Lean Code Editor**: Monaco-based editor with full Lean 4 syntax highlighting
- **AI Formalization**: Generate Lean code from natural language problem descriptions
- **Edit & Save**: Edit generated code and save versions to the database
- **History**: Track all formalization versions for each problem

## Quick Start

### 1. Install Dependencies
```bash
cd lean-annotator
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure AI Provider

Copy the example config file and add your API key:
```bash
cp .env.example .env
```

Edit `.env` and add your API key:
```
LLM_PROVIDER=grok
XAI_API_KEY=your-api-key-here
```

**Supported providers:**
| Provider | Env Variable | Get API Key |
|----------|-------------|-------------|
| OpenGauss | `OPENGAUSS_PROJECT_PATH` | https://github.com/math-inc/OpenGauss |
| xAI Grok | `XAI_API_KEY` | https://console.x.ai/ |
| OpenAI | `OPENAI_API_KEY` | https://platform.openai.com/ |
| Anthropic | `ANTHROPIC_API_KEY` | https://console.anthropic.com/ |

**Without API key:** The app runs in "mock" mode with pre-written templates.

### Using OpenGauss (Recommended for Lean 4)

[OpenGauss](https://github.com/math-inc/OpenGauss) is a specialized Lean 4 workflow orchestrator that provides higher-quality formalizations through purpose-built agents.

1. **Install OpenGauss:**
   ```bash
   git clone https://github.com/math-inc/OpenGauss.git
   cd OpenGauss
   ./scripts/install.sh
   ```

2. **Create a Lean project:**
   ```bash
   gauss
   /project create ~/my-lean-project
   ```

3. **Configure the annotator:**
   ```bash
   # In your .env file:
   LLM_PROVIDER=opengauss
   OPENGAUSS_PROJECT_PATH=/path/to/your/lean/project
   ```

   Or simply create a `.gauss/project.yaml` in your project directory and the annotator will auto-detect it.

**OpenGauss benefits:**
- Purpose-built for Lean 4 formalization
- Multi-agent workflow with specialized proving strategies
- Better integration with Mathlib
- Project-scoped formalization context

### 3. Run the App
```bash
python3 app.py
```

Open http://127.0.0.1:5000 in your browser.

## Usage

1. **Select a Problem**: Click on any problem card in the left panel
2. **Generate Code**: Click "Generate Formalization" to get AI-generated Lean code
3. **Edit**: Modify the code directly in the editor (syntax highlighted)
4. **Save**: Click "Save" to store your version
5. **History**: Load previous versions from the history panel

### Keyboard Shortcuts
- `Ctrl+Enter` - Generate formalization
- `Ctrl+S` - Save code
- `Ctrl+Shift+Enter` - Check code with Lean

### Adding Custom Problems
Use the form at the bottom of the problem panel to add your own problems.

### Import/Export
- Import problems from CSV (columns: title, description, natural_language, difficulty)
- Export all problems to CSV

## Project Structure

```
lean-annotator/
├── app.py              # Flask backend with LLM integration
├── lean_annotator.db   # SQLite database (auto-created)
├── requirements.txt    # Python dependencies
├── static/
│   ├── css/style.css   # Dark theme styling
│   └── js/app.js       # Monaco editor + frontend logic
└── templates/
    └── index.html      # Main interface
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/problems` | GET | List all problems |
| `/api/problems` | POST | Add new problem |
| `/api/problem/<id>` | GET | Get problem with formalizations |
| `/api/formalize/<id>` | POST | Generate Lean code using LLM |
| `/api/formalization/<id>` | PUT | Save edited code |
| `/api/check_lean` | POST | Check Lean code (requires Lean 4) |

## Installing Lean 4 (Optional)

The "Check" button requires Lean 4 to be installed:

```bash
# Install elan (Lean version manager)
curl https://raw.githubusercontent.com/leanprover/elan/master/elan-init.sh -sSf | sh

# Restart your terminal, then verify
lean --version
```

## License

MIT License
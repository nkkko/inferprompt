# InferPrompt: ASP Framework for LLM Prompt Optimization

InferPrompt is a novel framework that combines Answer Set Programming (ASP) with LLMs to systematically optimize prompts for other language models. It uses ASP to decompose and formalize prompt engineering as a constraint satisfaction and optimization problem.

## Core Components

1. **Meta-LLM Analyzer**: Analyzes tasks and decomposes them into logical components
2. **ASP Prompt Optimizer**: Uses ASP to generate optimal prompt structures
3. **Prompt Template Generator**: Converts ASP output into concrete prompt templates
4. **Feedback Loop**: Refines ASP rules through reinforcement learning

## Getting Started

### Prerequisites

- Python 3.9+
- [uv](https://github.com/astral-sh/uv) (faster alternative to pip, recommended)
- Clingo (ASP solver)
- OpenAI API key or other LLM provider

This project uses modern Python packaging with `pyproject.toml` for dependency management and configuration.

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/inferprompt.git
cd inferprompt

# Option 1: Using uv (recommended)
# Install uv if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create virtual environment and install dependencies with uv
uv venv .venv
uv pip install -r requirements.txt
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Option 2: Using standard pip/venv
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env
# Edit .env file with your API keys
```

Alternatively, simply run the provided script which handles everything:

```bash
# Make the script executable
chmod +x run.sh

# Run the script (uses uv)
./run.sh
```

### Running the API

```bash
# Start the FastAPI server
uvicorn app.main:app --reload
```

Visit `http://localhost:8000/docs` to access the Swagger documentation.

## API Endpoints

### `/api/v1/optimize`

Optimize a prompt based on target tasks and behaviors.

```json
{
  "user_prompt": "Explain quantum computing to a 10-year-old",
  "target_tasks": ["deduction"],
  "target_behaviors": ["step_by_step", "conciseness"],
  "target_model": "gpt-4",
  "domain": "education"
}
```

### `/api/v1/analyze`

Analyze a prompt without optimizing it.

```json
{
  "text": "Explain quantum computing to a 10-year-old"
}
```

### `/api/v1/feedback`

Provide feedback to improve future optimizations.

```json
{
  "component_type": "instruction",
  "behavior_type": "precision",
  "effectiveness": 0.85
}
```

### `/api/v1/history`

Get history of optimized prompts with pagination and optional model filtering.

```
GET /api/v1/history?limit=10&offset=0&model=gpt-4
```

### `/api/v1/history/{prompt_id}`

Get a specific optimized prompt by ID, including all components.

```
GET /api/v1/history/1
```

## Database

The application uses SQLite by default with the database file stored at `./inferprompt.db`. This makes it easy to get started without any additional database setup.

If you prefer to use a different database like PostgreSQL, you can set the `DATABASE_URL` environment variable:

```
# For SQLite with custom path
DATABASE_URL=sqlite:///./custom_path.db

# For PostgreSQL
DATABASE_URL=postgresql://user:password@localhost/database 
```

## Examples

See the `examples` directory for sample use cases.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

# Khaniña

```
   ____  __.__                  .__
  |    |/ _|  |__ _____    ____ |__| ____ _____
  |      < |  |  \__   \  /    \|  |/    \__   \
  |    |  \|   Y  \/ __ \|   |  \  |   |  \/ __ \_
  |____|__ \___|  (____  /___|  /__|___|  (____  /
          \/    \/     \/     \/        \/     \/
```

A CLI tool for fuzzing LLM endpoints for prompt injection and jailbreaking vulnerabilities.

## Features

- **Two-Phase Operation**: Preparation phase for configuration, attack phase for execution
- **Excel-Based Prompts**: Reads prompts from Excel files in the `prompts/` directory
- **Flexible Configuration**: JSON-based headers and body configuration in `resources/`
- **JSON Pointer Extraction**: Specify extraction path for response values
- **Project Management**: Organize results by project with timestamped outputs
- **LLM Evaluation**: Optional evaluation of responses for jailbreak/prompt injection detection using external LLM providers
- **Colored Output**: Informative console output with color coding
- **Verbose Mode**: Detailed logging with `--verbose` flag

## Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd khanina
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### Preparation Phase

1. Copy example configuration files:
   ```bash
   cp resources/headers.json.example resources/headers.json
   cp resources/body.json.example resources/body.json
   ```

2. Edit `resources/headers.json` with your LLM endpoint details:
   ```json
   {
       "method": "POST",
       "base_url": "https://api.example.com",
       "endpoint": "/v1/chat/completions",
       "headers": {
           "Content-Type": "application/json",
           "Authorization": "Bearer YOUR_API_KEY"
       }
   }
   ```

3. Edit `resources/body.json` with your request template (leave empty for GET requests).

4. (Optional) For LLM evaluation, copy and configure evaluation files:
   ```bash
   cp resources/llm.json.example resources/llm.json
   cp resources/llm.purpose.example resources/llm.purpose
   ```
   Edit `resources/llm.json` with your evaluator LLM provider details and `resources/llm.purpose` with the purpose of the target LLM.

5. Place your prompt Excel files in the `prompts/` directory. Prompts should start from cell B2 and progress downwards.

### Attack Phase

Run the application:
```bash
python khanina.py [--help | -h] [--verbose | -v]
```

Follow the interactive prompts to:
- Confirm endpoint configuration
- (Optional) Enable LLM evaluation for jailbreak detection
- Select or create a project
- Specify JSON pointer for response extraction
- Choose prompt files to use

Results will be saved in `results/<project>/` as Excel files.

## Configuration

### Headers Configuration
- `method`: HTTP method (GET/POST/PUT/etc.)
- `base_url`: Target's base URL
- `endpoint`: Target's endpoint
- `headers`: HTTP headers as key-value pairs

### Body Configuration
JSON object representing the request body. For GET requests, this becomes query parameters.

### JSON Pointer
Use RFC 6901 JSON Pointer syntax to extract values from responses, e.g.:
- `/choices/0/message/content` for OpenAI-style responses

### LLM Evaluation Configuration
When enabled, responses are evaluated for jailbreak/prompt injection vulnerabilities.

- `llm.json`: Evaluator LLM configuration
  ```json
  {
      "provider": "openai",
      "api_key": "your_evaluator_api_key",
      "model": "gpt-4"
  }
  ```
  Supported providers: OpenAI, Cohere, Anthropic, Claude, Gemini, Deepseek, Ollama
- `llm.purpose`: Description of the target LLM's intended purpose
- `evaluate.prompt`: Template for evaluation prompts (uses Jinja2 templating)

## Output

Results are saved as Excel files with columns:
- Index
- Prompt
- Main (extracted value)
- Full Response
- Response Time (s)

When LLM evaluation is enabled, additional columns are added:
- Success (boolean indicating jailbreak detection)
- Confidence (percentage 0-100)
- Evaluator Response (full response from evaluator LLM)

## Requirements

- Python 3.12+
- Dependencies listed in `requirements.txt`

## License

MIT License - see LICENSE file for details.
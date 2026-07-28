# Penny Ice Cap GeoAgent 2017

An AI-powered geospatial assistant built on the Gemini API to analyze radar measurements of ice thickness and subglacial bedrock topography for the Penny Ice Cap (Baffin Island, Nunavut, Canada). The dataset consists of real measurements collected on April 28, 2017, during the NASA Operation IceBridge survey using the Multichannel Coherent Radar Depth Sounder (MCoRDS L2).

This project adapts the semantic layer and tool-use architecture of [arctic-geoagent](https://github.com/adamkashdan/arctic-geoagent) to work directly with point-based flight track CSV data (over 110,000 measurements) rather than raster GeoTIFF files.

---

## Architecture

```
User question (natural language)
       │
       ▼
FastAPI interface /ask endpoint (src/main.py)
       │
       ▼
Agent loop (src/agent.py) <──> Gemini API (Function Calling)
       │
       ▼
GIS tools (src/tools.py) <──> Pandas / Matplotlib analysis over CSV
       │
       ▼
Semantic layer (semantic_layer.yaml) <── Describes dataset schema to the LLM
```

---

## How to Run the Project

### 1. Activate the Virtual Environment
A virtual environment containing all required GIS and web libraries (`pandas`, `geopandas`, `shapely`, `rasterio`, `matplotlib`, `google-genai`, `fastapi`, `uvicorn`) is already set up in the `venv` directory.

Activate it by running:
```bash
source venv/bin/activate
```

*(To reinstall dependencies from scratch, run `pip install -r requirements.txt`)*

### 2. Set Up Your Gemini API Key
The agent loop uses Google's Gemini API for tool-use reasoning. Set your API key as an environment variable:
```bash
export GEMINI_API_KEY="your-api-key-here"
```
Or create a `.env` file in the root of the project:
```env
GEMINI_API_KEY="your-api-key-here"
```

### 3. Verify GIS Tools (Direct Python execution)
You can test the GIS query logic, stats computation, correlation coefficient, and map generation directly without invoking the LLM:
```bash
python verify_tools.py
```
This will generate a flight track map named `test_map.png` in the root folder.

### 4. Run the Agent in CLI Mode
You can ask the agent questions directly from the command line:
```bash
python src/agent.py "What is the average ice thickness on the Penny Ice Cap in the bounding box [-66.0, 67.0, -65.5, 67.5]?"
```

### 5. Start the FastAPI Service
Launch the development server:
```bash
uvicorn src.main:app --reload --port 8000
```
Open your browser and navigate to `http://localhost:8000/docs` to view the interactive API documentation.

### 6. Query the API using curl
Send a POST request containing a question to the agent:
```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "Calculate the average surface elevation and ice thickness in the bounding box [-66.0, 67.0, -65.5, 67.5]."}'
```
The API returns the textual `answer` and a base64-encoded PNG map (`image_base64`) if the agent generated a map for its answer.

---

## Example Questions to Ask:
- *"What is the ice thickness and bedrock elevation at the coordinates 67.0145 N, -64.4217 W?"*
- *"Show me a map of the ice thickness for the entire Penny Ice Cap survey area."*
- *"Calculate the zonal statistics of the surface elevation in the bounding box [-66.5, 67.0, -66.0, 67.2]."*
- *"Is there a correlation between surface elevation and ice thickness in the central part of the ice cap?"*

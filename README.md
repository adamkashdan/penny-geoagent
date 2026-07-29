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

## Data Setup

Raw scientific datasets are **not included** in this repository due to file size limits and NASA data distribution policies. You will need to obtain the datasets and place them under the `data/` directory.

### 1. Download Datasets from NSIDC
Download the datasets for April 28, 2017 (flight line `IRMCR2_20170428_03`):
*   **MCoRDS L2 Ice Thickness (`IRMCR2`)**: Download the raw flight line data from the [NSIDC MCoRDS L2 Landing Page](https://nsidc.org/data/irmcr2).
*   **Accumulation Radar L1B (`IRACC1B`)**: Download the radar profiles from the [NSIDC Accumulation Radar L1B Landing Page](https://nsidc.org/data/iracc1b).

### 2. Place Data in Directory Structure
Create a `data/` folder in the project root and place the files as follows:
```
penny-geoagent/
├── data/
│   ├── IRMCR2_20170428_03_raw_data.csv
│   └── IceBridge Accumulation Radar L1B Geolocated Radar Echo Strength Profiles, Version 2 (IRACC1B) 2017/
│       ├── 001_28166479/
│       └── ... (other 82 granules)
```
*(Note: A `.gitkeep` file is provided in `data/` to preserve the folder structure in Git. The actual dataset files are ignored and will not be committed).*

---

## Installation & Setup

### 1. Create and Activate the Virtual Environment
A virtual environment ensures clean and isolated dependency installation. Create and activate it by running:
```bash
python -m venv venv
source venv/bin/activate
```

### 2. Install Dependencies
Install all required GIS and web packages (`pandas`, `geopandas`, `shapely`, `rasterio`, `matplotlib`, `google-genai`, `fastapi`, `uvicorn`):
```bash
pip install -r requirements.txt
```

### 3. Set Up Your Gemini API Key
The agent loop uses Google's Gemini API for tool-use reasoning. Set your API key as an environment variable:
```bash
export GEMINI_API_KEY="your-api-key-here"
```
Or create a `.env` file in the root of the project:
```env
GEMINI_API_KEY="your-api-key-here"
```

### 4. Verify GIS Tools (Direct Python execution)
You can test the GIS query logic, stats computation, correlation coefficient, and map generation directly without invoking the LLM:
```bash
python verify_tools.py
```
This will generate a flight track map named `test_map.png` in the root folder.

### 5. Run the Agent in CLI Mode
You can ask the agent questions directly from the command line:
```bash
python src/agent.py "What is the average ice thickness on the Penny Ice Cap in the bounding box [-66.0, 67.0, -65.5, 67.5]?"
```

### 6. Start the FastAPI Service
Launch the development server:
```bash
uvicorn src.main:app --reload --port 8000
```
Open your browser and navigate to `http://localhost:8000/docs` to view the interactive API documentation.

### 7. Query the API using curl
Send a POST request containing a question to the agent:
```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "Calculate the average surface elevation and ice thickness in the bounding box [-66.0, 67.0, -65.5, 67.5]."}'
```
The API returns the textual `answer` and a base64-encoded PNG map (`image_base64`) if the agent generated a map for its answer.

---

## Pleistocene Ice Layer (PIL) Modeling

The project includes a physical glaciological modeling module for estimating the basal Pleistocene Ice Layer (PIL) thickness and its impact on glacier velocity:
- **PIL Thickness Estimation**: Evaluates the thickness of the basal soft ice layer along flight tracks: $H_p = \min(0.12 \times H, 80\text{ m})$ for deep zones ($H > 150\text{ m}$).
- **Ice Flow Modeling**: Solves the vertical velocity profile $u(z)$ under the Shallow Ice Approximation (SIA) using Glen's flow law. It incorporates a fluidity enhancement factor ($E = 3.5$) for the soft basal Pleistocene ice, demonstrating the concentration of shear deformation near the bed.

### Model Outputs
Run the modeling module directly using:
```bash
python src/pil_modeling.py
```
This generates two plots in the root directory:
1. **PIL Distribution Map** (`pil_distribution_map.png`): Spatial distribution of the estimated basal layer along the survey track.
2. **Basal Shear Velocity Profile** (`pil_velocity_profile.png`): Visualizes the normalized velocity profile $u(z)$ comparing Holocene-only ice ($E=1$) and ice with a soft basal PIL ($E=3.5$).

| PIL Spatial Distribution | Basal Shear Velocity Profile |
|:---:|:---:|
| ![PIL Distribution Map](pil_distribution_map.png) | ![Basal Shear Profile](pil_velocity_profile.png) |

---

## Example Questions to Ask:
- *"What is the ice thickness and bedrock elevation at the coordinates 67.0145 N, -64.4217 W?"*
- *"Show me a map of the ice thickness for the entire Penny Ice Cap survey area."*
- *"Calculate the zonal statistics of the surface elevation in the bounding box [-66.5, 67.0, -66.0, 67.2]."*
- *"Is there a correlation between surface elevation and ice thickness in the central part of the ice cap?"*

---

## License & Copyright

Copyright (c) 2026 Adam Kashdan. All rights reserved.

This repository contains draft source code associated with an upcoming scientific publication. The code is provided solely for reference and academic peer-review purposes. 

See the [LICENSE](LICENSE) file for full copyright terms and restrictions.

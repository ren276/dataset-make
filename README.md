# dataset-make

This repository is used to generate a high-quality, provenance-preserving, India-adapted, longitudinal synthetic clinical dataset and medical SLM/LLM training and evaluation datasets for the PHC SaMD project.

## Installation / Setup on a New PC

To set up this project on a new machine, you will need to install the dependencies for both the Python pipeline and the Synthea data generation component.

### Prerequisites
- **Python 3.8+**
- **Java 11+** (Required for running Synthea)
- **Git**

### 1. Clone the repository
```bash
git clone <repository_url>
cd dataset-make
```

### 2. Set up a Python Virtual Environment
It is recommended to use a virtual environment to manage dependencies:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows use: .venv\Scripts\activate
```

### 3. Install Python Dependencies
Install the required packages using `requirements.txt`:
```bash
pip install -r requirements.txt
```

### 4. Synthea Setup
The synthetic data generation relies on Synthea (located in `synthea` and `synthea-international` folders). Ensure Java is installed and accessible in your system's PATH.

If you need to rebuild Synthea:
```bash
cd synthea-international
./gradlew build
# Return to root
cd ..
```

## Running the Pipeline
Check the documentation in `new dataset making.md` or `DATASET_ARCHITECTURE_CURRENT.md` for detailed run instructions for specific pipelines.

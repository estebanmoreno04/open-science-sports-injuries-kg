FROM python:3.10-slim
 
# System dependencies required by torch, hdbscan and umap
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    git \
    && rm -rf /var/lib/apt/lists/*
 
# Set working directory
WORKDIR /app
 
# Copy requirements first to leverage Docker layer caching
COPY requirements.txt .
 
# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt
 
# Copy full project
COPY . .
 
# Create output directories in case they don't exist
RUN mkdir -p data/processed data/rdf results/similarity results/topics kg
 
# Expose Flask port
EXPOSE 5000
 
# Default: run the explorer
# Override with docker-compose for the pipeline
CMD ["python", "app.py", "--host", "0.0.0.0", "--port", "5000"]
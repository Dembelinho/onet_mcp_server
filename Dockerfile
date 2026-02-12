FROM python:3.11-slim

WORKDIR /app

# Installation des dépendances
COPY requirements.txt .
# On retire pywin32 qui est pour Windows uniquement
RUN sed -i '/pywin32/d' requirements.txt && \
    pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copie du code source
COPY . .

# Variables d'environnement par défaut
ENV PORT=8000

# Lancement via Python direct (car uvicorn est appelé dans main.py)
CMD ["python", "main.py"]
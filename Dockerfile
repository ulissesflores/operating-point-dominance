FROM python:3.11-slim
WORKDIR /work
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
# replicação completa (sem multiseed): python run_all.py
CMD ["pytest", "tests/", "-q"]

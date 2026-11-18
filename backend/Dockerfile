# Imagem "final" do backend — instala as dependências travadas em
# requirements.txt, copia o código, e ao subir aplica as migrations do
# Alembic automaticamente antes de iniciar o Uvicorn. Não substitui o dia a
# dia de desenvolvimento (isso continua sendo o `.venv` local com
# inteira integrada com um único comando (`docker compose up`).
FROM python:3.13-slim

WORKDIR /app

# Copiado antes do resto do código de propósito: o cache de camadas do Docker
# só reinstala as dependências quando requirements.txt muda, não a cada
# alteração de código.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# Sem curl/wget na imagem slim — usa o próprio Python (já instalado) pra
# checar o endpoint /health (ver app/main.py).
HEALTHCHECK --interval=10s --timeout=5s --start-period=15s --retries=5 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# "alembic upgrade head" é idempotente (só aplica o que ainda não foi
# aplicado) — seguro rodar em todo start do container, inclusive num banco já
# migrado.
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]

# CheckPronto

Sistema web para organizar as tarefas e os checklists de turno de uma cozinha de delivery. Fiz para o restaurante onde trabalho, onde a equipe usa no dia a dia.

Tem duas partes:

- **Área administrativa**: o gestor cadastra tarefas, setores e funcionários, agenda tarefas recorrentes, monta checklists por turno e acompanha um painel com produtividade e alertas.
- **Área operacional**: roda num tablet na cozinha. A equipe vê as tarefas do setor num Kanban e confirma cada ação com um PIN de 4 dígitos.

## Funcionalidades

- Tarefas com tempo estimado e cronômetro de execução
- Checklists por turno, com foto como comprovação
- Várias lojas no mesmo sistema, com os dados separados por loja
- Perfis de acesso: master, gestor, líder e operacional
- Login com JWT, PIN por ação e limite de tentativas
- Histórico de quem fez o quê e painel com gráficos

## Tecnologias

- **Back-end:** Python, FastAPI, SQLAlchemy, Alembic, PostgreSQL, Pytest
- **Front-end:** React, TypeScript, Tailwind CSS, TanStack Query, Recharts, Vitest
- **Infra:** Docker Compose

## Como rodar

Precisa de Docker instalado.

```bash
cp backend/.env.example backend/.env
# edite o backend/.env: SECRET_KEY, MASTER_USER_EMAIL e MASTER_USER_PASSWORD

docker compose up --build
docker compose exec backend python scripts/seed_master_user.py
```

- Front-end: http://localhost:5173
- API (Swagger): http://localhost:8000/docs

Entre com o e-mail e a senha que você colocou no `.env`.

## Testes

```bash
# back-end
cd backend && python -m pytest

# front-end
cd frontend && npm install && npm test
```

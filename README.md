# Warehouse Manager

Sistema de Otimização Espacial e Gêmeo Digital para Armazéns de Café operando em modelo **Shadow State**.

## Estrutura do Projeto

- **[`api/`](file:///c:/Users/luis.felipe/Desktop/MNSGeral/warehouse_manager/api)**: Backend em Python (FastAPI, Celery, SQLAlchemy 2.0, Redis, PostgreSQL).
- **[`web/`](file:///c:/Users/luis.felipe/Desktop/MNSGeral/warehouse_manager/web)**: Frontend Web & Digital Twin (Next.js 16, Babylon.js 3D, Zustand, TailwindCSS).

## Requisitos do Sistema

- Docker e Docker Compose
- Python >= 3.12 (para desenvolvimento local da API)
- Node.js >= 20 (para desenvolvimento local do Web)

## Executando com Docker Compose

Para subir a infraestrutura completa (PostgreSQL, Redis, API e Celery Worker):

```bash
docker compose up -d --build
```

Consulte a documentação em cada subpasta para instruções específicas de desenvolvimento:
- [Documentação da API](file:///c:/Users/luis.felipe/Desktop/MNSGeral/warehouse_manager/api/README.md)


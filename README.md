# LiveClipper

Fundação de um pipeline de clipes para transmissões ao vivo **capturadas com autorização** dos criadores. A captura audiovisual é feita pelo **OBS Studio**; o LiveClipper lê as gravações produzidas por ele, mantém o catálogo no banco e expõe uma API HTTP.

> **Uso responsável:** capture e reutilize somente conteúdo para o qual você possui autorização explícita de captura e reutilização. O cadastro de uma fonte exige uma referência de autorização e uma confirmação explícita. O sistema não baixa transmissões, não extrai URLs internas, não contorna DRM nem restrições de plataforma.

## Escopo da Fase 1

Implementado:

- Estrutura de pacotes por responsabilidade (`obs`, `capture`, `sources`, `detection`, `clipping`, `publishing`, `database`, `api`).
- Configuração por ambiente/`.env` com Pydantic Settings.
- SQLite + SQLAlchemy 2.0 com as tabelas `capture_sources` e `recordings`.
- Cadastro de fontes autorizadas com validação de diretório e extensões.
- Leitura exclusiva de arquivos locais gravados pelo OBS.
- Monitor periódico que só registra arquivos estáveis (gravação encerrada).
- API FastAPI com health check, fontes, gravações, captura e diagnóstico do OBS.
- Testes com Pytest/TestClient.

Fora do escopo desta fase:

- Download de transmissões ou acesso a URLs internas de plataformas.
- Buffer circular em memória e detecção de momentos.
- Recorte, conversão vertical, legendas e publicação no YouTube.
- Controle remoto do OBS via WebSocket (apenas configuração e diagnóstico).

O roadmap está em [`docs/roadmap.md`](docs/roadmap.md).

## Requisitos

- Python **3.12+**
- OBS Studio instalado e configurado para gravar em um diretório local
- FFmpeg, OpenCV, Faster-Whisper e YouTube Data API serão adicionados apenas nas fases que os utilizam

## Instalação

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"

cp .env.example .env
```

Ajuste o `.env`, principalmente:

```env
LIVECLIPPER_OBS_RECORDINGS_DIR=./data/obs
```

O diretório é criado automaticamente na inicialização. Configure o OBS para gravar nele (ou em um diretório por fonte). Veja [`docs/obs-setup.md`](docs/obs-setup.md).

## Executar

```bash
uvicorn app.main:app --reload
# ou
python -m app --reload
# ou
liveclipper --reload
```

- API: <http://127.0.0.1:8000>
- Swagger: <http://127.0.0.1:8000/docs>
- Health: <http://127.0.0.1:8000/health>

## Fluxo mínimo

1. Configure o OBS para gravar em `./data/obs` (formato `.mkv` é recomendado).
2. Cadastre uma fonte autorizada:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/sources \
  -H 'Content-Type: application/json' \
  -d '{
    "name": "canal-autorizado",
    "platform": "youtube",
    "creator_name": "Criador Autorizado",
    "authorization_reference": "contrato-2026-001",
    "authorization_notes": "Permissão de captura e reutilização confirmada por e-mail.",
    "authorization_confirmed": true,
    "watch_directory": "/caminho/para/saida-do-obs"
  }'
```

3. O monitor varre as fontes a cada `LIVECLIPPER_CAPTURE_POLL_INTERVAL_SECONDS`. Um arquivo só é registrado depois de ficar `LIVECLIPPER_CAPTURE_SETTLE_SECONDS` sem alteração. Também é possível forçar uma varredura:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/capture/scan
curl http://127.0.0.1:8000/api/v1/recordings
```

## Endpoints principais

| Método | Caminho | Descrição |
| --- | --- | --- |
| `GET` | `/` | Identificação da aplicação/fase |
| `GET` | `/health` | Banco + estado do monitor |
| `GET` | `/api/v1/obs/status` | Diagnóstico da configuração do OBS |
| `POST` | `/api/v1/sources` | Cadastrar fonte autorizada |
| `GET` | `/api/v1/sources` | Listar fontes |
| `GET` | `/api/v1/sources/{id}` | Detalhar fonte |
| `POST` | `/api/v1/capture/scan` | Varredura manual (opcional `?source_id=`) |
| `GET` | `/api/v1/capture/status` | Estado do monitor |
| `GET` | `/api/v1/recordings` | Listar gravações (`status`, `source_id`, `limit`, `offset`) |
| `GET` | `/api/v1/recordings/{id}` | Detalhar gravação |

## Testes

```bash
pytest
pytest --cov=app
```

Os testes usam banco SQLite temporário, diretórios temporários e desligam o monitor em background.

## Estrutura

```text
app/
├── api/           # FastAPI, dependências, routers e schemas HTTP
├── capture/       # scanner de arquivos, monitor periódico e schemas
├── obs/           # configuração e diagnóstico da integração OBS
├── sources/       # abstração de fontes, adaptador local e cadastro
├── detection/     # reservado para detecção (Fase 3)
├── clipping/      # reservado para recorte/edição (Fase 4)
├── publishing/    # reservado para YouTube (Fase 6)
├── database/      # modelos, sessão e repositórios SQLAlchemy
├── config.py      # Settings
└── main.py        # app factory + lifespan
data/              # banco e gravações locais (não versionados)
output/            # artefatos gerados futuramente
docs/
tests/
```

## Segurança

A Fase 1 não implementa autenticação na API: ela foi desenhada para execução local. Mantenha o servidor em `127.0.0.1` ou em uma rede confiável. Se precisar expor a API, coloque-a atrás de autenticação/reverse proxy antes de qualquer uso remoto.

## Decisões arquiteturais

- **Observação passiva do OBS:** a Fase 1 lê arquivos; não depende de WebSocket nem de plugins.
- **Estabilidade antes da ingestão:** evita registrar arquivos que o OBS ainda está escrevendo.
- **Autorização modelada:** `authorization_reference` e `authorization_notes` ficam persistidas junto da fonte.
- **Separação por responsabilidade:** scanner, adaptador de fonte, persistência e API não se conhecem além dos contratos necessários.
- **Dependências mínimas:** FFmpeg, OpenCV, Faster-Whisper e YouTube API entram somente quando suas fases forem implementadas.

Detalhes em [`docs/architecture.md`](docs/architecture.md).

## Licença

MIT. Consulte [`LICENSE`](LICENSE).

# LiveClipper

Sistema de **detecção de momentos interessantes em transmissões ao vivo autorizadas**.

O LiveClipper recebe áudio e vídeo de uma transmissão capturada pelo **OBS Studio**, analisa o conteúdo e registra os momentos que poderiam virar bons trechos. O resultado é uma tabela contendo exclusivamente:

| Início do corte | Fim do corte | Descrição simples do acontecimento |
| --- | --- | --- |
| segundos desde o início da sessão | segundos desde o início da sessão | texto curto gerado pela análise |

O sistema **não edita vídeos, não recorta arquivos, não gera Shorts, não adiciona legendas e não publica no YouTube**. A saída é uma lista de candidatos para revisão humana.

> **Uso responsável:** capture e analise somente conteúdo para o qual você possui autorização explícita. O cadastro de uma fonte exige uma referência de autorização e uma confirmação explícita. O sistema não baixa transmissões, não extrai URLs internas, não contorna DRM nem restrições de plataforma.

## Revisão de escopo 2.0

Esta revisão simplifica o produto sem descartar a fundação já implementada:

- **Mantido e reutilizado:** FastAPI, SQLite, SQLAlchemy, configurações Pydantic, cadastro de fontes autorizadas, `SourceAdapter`, monitor de gravações, endpoints existentes e testes.
- **Mantidos:** `app/obs`, `app/capture`, `app/sources` e `app/database`.
- **Novo foco:** `app/detection` será o principal módulo funcional.
- **Fora do projeto:** edição/recorte de vídeo, Shorts, conversão vertical, legendas e publicação.
- **Análise visual:** não é requisito do MVP; OpenCV não faz parte do escopo.
- **Preparação futura:** FFmpeg/FFprobe para áudio e Faster-Whisper para transcrição.
- **Ainda não implementado:** detector de picos, transcrição, tabelas novas e migrações.

A Fase 1 continua funcionando exatamente como antes. O detector será implementado em uma fase posterior.

## Estado atual

Implementado e preservado:

- Estrutura de pacotes por responsabilidade (`obs`, `capture`, `sources`, `detection`, `database`, `api`).
- Configuração por ambiente/`.env` com Pydantic Settings.
- SQLite + SQLAlchemy 2.0 com as tabelas `capture_sources` e `recordings`.
- Cadastro de fontes autorizadas com validação de diretório e extensões.
- Leitura exclusiva de arquivos locais gravados pelo OBS.
- Monitor periódico que só registra arquivos estáveis (gravação encerrada).
- API FastAPI com health check, fontes, gravações, captura e diagnóstico do OBS.
- Origem de vídeo substituível por contrato (`SourceAdapter` + registro de adaptadores).
- Testes com Pytest/TestClient.

Planejado, não implementado nesta revisão:

- Sessões explícitas de captura (`capture_sessions`) para preservar a continuidade temporal.
- Tabela `clip_candidates` para os momentos detectados.
- Extração e análise de áudio com FFmpeg/FFprobe.
- Análise incremental por segmentos, para acompanhar a transmissão com baixa latência.
- Transcrição com Faster-Whisper.
- Detector de picos e geração de descrições.
- Endpoint de consulta da tabela de candidatos.

## Escopo

### Dentro do escopo

- Ingestão de gravações autorizadas produzidas pelo OBS.
- Catálogo de gravações e monitoramento da pasta.
- Organização das gravações em sessões contínuas de captura.
- Análise de áudio e transcrição como foco do MVP; o vídeo é ingerido, mas a análise visual não é obrigatória.
- Persistência de candidatos com início, fim, descrição e pontuação interna.
- Consulta dos candidatos pela API, com saída enxuta para revisão humana.

### Fora do escopo — permanente

- Editar, recortar, renderizar ou converter vídeos.
- Gerar Shorts ou converter para 9:16.
- Adicionar, queimar ou sincronizar legendas.
- Publicar, agendar ou enviar conteúdo ao YouTube ou a qualquer plataforma.
- OAuth, upload e integração com APIs de publicação.
- OpenCV e processamento de imagem em tempo real.
- Download de transmissões, extração de URLs internas, contorno de DRM ou de restrições de plataforma.
- Interface gráfica.

### Fora desta entrega

- Detector de picos.
- Qualquer código executável em `app/detection`.
- Criação ou migração das tabelas propostas.
- Rotas de detecção ou de candidatos.
- Dependências de FFmpeg, Faster-Whisper ou OpenCV no `pyproject.toml`.

## Reaproveitamento obrigatório

| Recurso existente | Como é reutilizado |
| --- | --- |
| **FastAPI** | Mantém a API HTTP, health check, docs OpenAPI e o padrão de routers. |
| **SQLite + SQLAlchemy** | Mantém a persistência local; as novas tabelas serão evolutivas e não destrutivas. |
| **Pydantic Settings** | Recebe as futuras configurações de detecção sem alterar o carregamento atual. |
| **Cadastro de fontes autorizadas** | Continua sendo o pré-requisito para qualquer captura e análise. |
| **`SourceAdapter`** | Continua isolando a origem do vídeo; o detector recebe gravações catalogadas. |
| **Monitor de gravações** | Continua descobrindo arquivos estáveis e disparando a futura análise. |
| **Endpoints existentes** | Permanecem com o mesmo contrato; nenhuma rota foi removida. |
| **Testes existentes** | Continuam protegendo a fundação de ingestão e segurança. |

## Arquitetura

```text
OBS Studio
   │ grava segmentos .mkv/.mp4/... em diretório local
   ▼
app.sources ── SourceAdapter / cadastro autorizado
   │ candidatos: caminho, tamanho, mtime
   ▼
app.capture.scanner + monitor
   │ estabilidade, deduplicação, polling
   ▼
app.database
   │ capture_sources · recordings
   │ [planejado] capture_sessions · clip_candidates
   │
   ├── app.detection  ← módulo principal planejado
   │      ├── FFprobe/FFmpeg: metadados e áudio PCM
   │      ├── análise de energia/picos: futuro
   │      ├── Faster-Whisper: transcrição futura
   │      └── montagem de candidatos: futuro
   │
   └── app.api        ← endpoints existentes + futura tabela de candidatos
```

Os pacotes `app.clipping` e `app.publishing` permanecem vazios apenas como marcadores históricos. Eles **não fazem parte do produto**, não possuem código executável e não devem receber novas funcionalidades.

## Modelo de dados

As tabelas atuais são preservadas:

- `capture_sources`: fontes autorizadas.
- `recordings`: arquivos de gravação descobertos.

O modelo `recordings` atual **não é suficiente** para relacionar segmentos de uma mesma transmissão:

- cada linha representa um arquivo isolado;
- não existe vínculo entre arquivos da mesma captura;
- `modified_at` é o horário do arquivo, não o início da transmissão;
- não há duração nem deslocamento relativo ao início da sessão.

Por isso, a proposta é adicionar uma tabela de sessões de captura (`capture_sessions`) e complementar `recordings` com a referência temporal. Os tempos de `clip_candidates` serão relativos ao início da sessão, preservando a continuidade mesmo quando o OBS dividir a transmissão em vários arquivos.

### `capture_sessions` (proposta, ainda não criada)

Representa uma transmissão contínua e é a **referência temporal oficial** do sistema.

| Campo | Uso |
| --- | --- |
| `id` | Chave primária. |
| `source_id` | Fonte autorizada que originou a sessão. |
| `started_at` | Instante zero da linha do tempo. |
| `ended_at` | Fim da transmissão; nulo enquanto ativa. |
| `status` | `active`, `closed` ou `failed`. |
| `created_at` | Auditoria. |

### `recordings` (evolução aditiva)

Todos os campos existentes são preservados. Quando necessário, adicionar:

| Campo novo | Uso |
| --- | --- |
| `session_id` | Sessão à qual o arquivo pertence. |
| `duration_seconds` | Duração do arquivo, obtida por FFprobe. |
| `start_offset_seconds` | Segundo da sessão em que aquele arquivo começa. |

A ordem dos segmentos pode ser obtida por `start_offset_seconds`; não é necessário criar um campo separado de índice.

### `clip_candidates` (proposta, ainda não criada)

| Campo | Uso |
| --- | --- |
| `id` | Chave primária. |
| `session_id` | Sessão que define a linha do tempo. |
| `start_seconds` | Início do corte, relativo ao início da sessão. |
| `end_seconds` | Fim do corte, relativo ao início da sessão. |
| `description` | Descrição simples do acontecimento. |
| `score` | Pontuação interna (0..1). |
| `created_at` | Data de criação. |

Não há `recording_id` obrigatório no candidato: um acontecimento pode atravessar vários segmentos de gravação. A sessão é a referência temporal principal. A saída apresentada ao operador contém apenas **início, fim e descrição**; `id` e `score` são internos.

Detalhes completos, incluindo chaves estrangeiras, índices, restrições e estratégia de migração não destrutiva, estão em [`docs/PROJECT_SPEC.md`](docs/PROJECT_SPEC.md) e [`docs/architecture.md`](docs/architecture.md).

## Requisitos

- Python **3.12+**
- OBS Studio instalado e configurado para gravar em um diretório local
- Para a fase atual: nenhuma dependência de mídia
- Para a fase de detecção:
  - **FFmpeg e FFprobe** (binários externos) para metadados e extração de áudio;
  - **Faster-Whisper** (dependência Python opcional) para transcrição.
- **OpenCV não é necessário e não faz parte do MVP.**

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

A origem do vídeo é selecionada por `LIVECLIPPER_SOURCE_ADAPTER` (padrão `obs_directory`). Novos adaptadores podem ser registrados sem alterar o scanner; veja a seção 4.3 de [`docs/PROJECT_SPEC.md`](docs/PROJECT_SPEC.md).

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

## Fluxo mínimo atual

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

4. A análise de áudio e a geração de candidatos entram na fase de detecção. Até lá, o sistema apenas cataloga gravações.

## Endpoints principais

Endpoints atuais, preservados:

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

Planejados para a fase de detecção, **ainda não implementados**:

| Método | Caminho | Descrição |
| --- | --- | --- |
| `GET` | `/api/v1/clip-candidates` | Lista início, fim e descrição dos candidatos |
| `GET` | `/api/v1/detection/status` | Estado da análise de áudio/transcrição |

Nenhuma rota de edição, legenda ou publicação será adicionada.

## Testes

```bash
pytest
pytest --cov=app
```

Os testes usam banco SQLite temporário, diretórios temporários e desligam o monitor em background. A suíte atual continua cobrindo a ingestão, a autorização, o monitor, o OBS e o contrato `SourceAdapter`.

## Estrutura

```text
app/
├── api/           # FastAPI, dependências, routers e schemas HTTP
├── capture/       # scanner de arquivos, monitor periódico e schemas
├── obs/           # configuração e diagnóstico da integração OBS
├── sources/       # contrato de fonte, adaptador local, registro e cadastro
├── detection/     # principal módulo futuro: áudio, transcrição e candidatos
├── clipping/      # fora do escopo; sem código executável
├── publishing/    # fora do escopo; sem código executável
├── database/      # modelos, sessão e repositórios SQLAlchemy
├── config.py      # Settings
└── main.py        # app factory + lifespan
data/              # banco e gravações locais (não versionados)
output/            # artefatos de análise futuros (não versionados)
docs/
tests/
```

## Segurança

A API atual não implementa autenticação: ela foi desenhada para execução local. Mantenha o servidor em `127.0.0.1` ou em uma rede confiável. Se precisar expor a API, coloque-a atrás de autenticação/reverse proxy antes de qualquer uso remoto.

Nunca versione `.env`, gravações, bancos ou tokens. O sistema não publica conteúdo, não baixa transmissões e não acessa fontes protegidas. A política completa está em [`docs/SECURITY.md`](docs/SECURITY.md).

## Decisões arquiteturais

- **Observação passiva do OBS:** a captura atual lê arquivos; não depende de WebSocket nem de plugins.
- **Estabilidade antes da ingestão:** evita registrar arquivos que o OBS ainda está escrevendo.
- **Autorização modelada:** `authorization_reference` e `authorization_notes` ficam persistidas junto da fonte.
- **Detecção como núcleo:** `app/detection` concentrará a análise; os demais pacotes fornecem captura, persistência e API.
- **Sessões explícitas:** os tempos dos candidatos serão relativos à sessão de captura, não ao arquivo isolado.
- **Sem edição:** o produto entrega candidatos, não arquivos de vídeo.
- **Sem OpenCV:** a análise inicial usa FFmpeg/FFprobe e Faster-Whisper.
- **Dependências mínimas:** FFmpeg/FFprobe e Faster-Whisper entram somente quando a fase de detecção for implementada.
- **Migração não destrutiva:** nenhuma tabela ou coluna existente será removida ou alterada de forma incompatível.

Detalhes em [`docs/architecture.md`](docs/architecture.md).

## Documentação

| Documento | Conteúdo |
| --- | --- |
| [`docs/PROJECT_SPEC.md`](docs/PROJECT_SPEC.md) | Especificação, escopo, configuração, API, dados e fases. |
| [`docs/architecture.md`](docs/architecture.md) | Arquitetura, fluxo de ingestão, pipeline de detecção e decisões técnicas. |
| [`docs/roadmap.md`](docs/roadmap.md) | Fases do produto e limites permanentes. |
| [`docs/SECURITY.md`](docs/SECURITY.md) | Segurança, autorização, segredos e higiene do Git. |
| [`docs/obs-setup.md`](docs/obs-setup.md) | Como capturar a janela do navegador e o áudio no OBS. |
| [`docs/obs-websocket.md`](docs/obs-websocket.md) | Desenho da integração futura com o OBS WebSocket (não implementada). |
| [`docs/recordings-monitoring.md`](docs/recordings-monitoring.md) | Monitoramento atual da pasta de gravações e evoluções futuras. |

## Licença

MIT. Consulte [`LICENSE`](LICENSE).

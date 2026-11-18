# Especificação do Projeto — LiveClipper

> **Status:** Fase 1 concluída — fundação de ingestão de gravações autorizadas do OBS Studio.
>
> **Versão da aplicação:** `0.1.0` · **Python:** 3.12+ · **API:** FastAPI · **Banco:** SQLite + SQLAlchemy 2.x

## 1. Resumo

O LiveClipper é a fundação de um pipeline de clipes para transmissões ao vivo. A captura audiovisual é feita pelo **OBS Studio**, que grava a janela autorizada do navegador e o áudio correspondente em um diretório local. O LiveClipper observa esse diretório, registra as gravações estáveis em um banco SQLite e expõe um catálogo por API HTTP.

Esta fase **não** baixa transmissões, não acessa URLs internas de plataformas, não contorna DRM e não publica conteúdo. Ela prepara a base para detecção, recorte, legendas e publicação nas fases seguintes.

## 2. Objetivo e escopo

### 2.1 Dentro do escopo da Fase 1

- Ambiente Python reproduzível com `pyproject.toml` e dependências de desenvolvimento.
- API FastAPI com `GET /health` verificando banco e monitor de captura.
- Persistência SQLite via SQLAlchemy 2.x.
- Configuração centralizada por variáveis de ambiente e `.env`, validada com Pydantic Settings.
- Cadastro de fontes autorizadas com referência de autorização obrigatória.
- Leitura exclusiva de arquivos locais produzidos pelo OBS.
- Monitor periódico que registra apenas gravações consideradas estáveis.
- Catálogo de gravações consultável por API.
- Contrato de origem de vídeo substituível (`SourceAdapter` + registro de adaptadores).
- Testes automatizados com Pytest.
- Documentação em português, incluindo OBS, WebSocket futuro e monitoramento futuro.

### 2.2 Fora do escopo da Fase 1

| Item | Fase prevista |
| --- | --- |
| Metadados de mídia com FFprobe | 2 |
| Buffer circular de segmentos | 2 |
| Detector de picos e análise de áudio | 3 |
| Transcrição de áudio e leitura de chat | 3 |
| Recorte de vídeos e enquadramento vertical com FFmpeg/OpenCV | 4 |
| Legendas com Faster-Whisper | 5 |
| Publicação no YouTube com OAuth 2.0 | 6 |
| Captura ativa pelo OBS (gravação/replay buffer) e controle remoto via WebSocket | fase futura, ainda não iniciada |
| Interface gráfica | não planejada; a interface desta fase é a API HTTP |
| Autenticação na API | antes de qualquer exposição remota |

**Limite de implementação:** os pacotes reservados (`app.detection`, `app.clipping`, `app.publishing`) contêm somente documentação. Não crie funções fictícias, stubs executáveis, rotas ou dependências apenas para preencher módulos; cada fase adiciona código real quando for iniciada. O `Protocol` `ObsClient` é apenas um contrato de tipos e não executa chamadas.

## 3. Uso responsável e autorização

O projeto parte do princípio de que o operador possui **autorização explícita do criador** para capturar e reutilizar o conteúdo.

- O cadastro de uma fonte exige `authorization_reference` e `authorization_confirmed: true`.
- A varredura revalida a presença de referência e data de autorização antes de ingerir arquivos.
- O operador deve arquivar a evidência (contrato, e-mail, termo), limitar a captura ao período e conteúdo autorizados e remover dados quando a autorização expirar.
- O sistema registra a autorização; ele não decide se o uso é lícito nem substitui a análise jurídica.
- É proibido usar o projeto para burlar termos de plataforma, DRM, restrições de acesso ou direitos de terceiros.

## 4. Arquitetura

### 4.1 Componentes

```text
Navegador (conteúdo autorizado)
   │ janela + áudio
   ▼
OBS Studio
   │ grava .mkv/.mp4/.mov/.flv/.ts em diretório local
   ▼
app.sources  ── SourceAdapter / registro de adaptadores
   │ candidatos: caminho, tamanho, mtime
   ▼
app.capture.scanner
   │ estabilidade, tamanho > 0, deduplicação por caminho
   ▼
app.database (capture_sources, recordings)
   ├── app.capture.monitor → polling periódico em thread separada
   └── app.api             → FastAPI/REST, health e diagnóstico
```

| Pacote | Responsabilidade |
| --- | --- |
| `app.config` | `Settings` centralizadas, carregadas de `.env`/ambiente. |
| `app.database` | Base declarativa, tipos UTC, modelos, sessão, `create_all` e repositórios. |
| `app.sources` | Contrato `SourceAdapter`, adaptador de diretório local, registro de adaptadores, cadastro autorizado. |
| `app.capture` | Varredura, regra de estabilidade, deduplicação, monitor periódico e schemas. |
| `app.obs` | Diagnóstico local do OBS e contrato futuro `ObsClient` (WebSocket). |
| `app.api` | Rotas, dependências, schemas HTTP e mapeamento de erros. |
| `app.detection` | Reservado para áudio/transcrição/chat (Fase 3). |
| `app.clipping` | Reservado para FFmpeg/OpenCV (Fase 4). |
| `app.publishing` | Reservado para YouTube/OAuth (Fase 6). |

### 4.2 Fluxo de ingestão

1. O OBS grava a janela autorizada do navegador e seu áudio no diretório configurado.
2. Uma fonte autorizada é cadastrada via `POST /api/v1/sources`, apontando para esse diretório.
3. O `CaptureMonitor` executa a varredura a cada `LIVECLIPPER_CAPTURE_POLL_INTERVAL_SECONDS`.
4. O adaptador lista arquivos cuja extensão está na allowlist da fonte.
5. O scanner descarta arquivos vazios, arquivos ainda em escrita e caminhos já registrados.
6. Um arquivo estável vira um `Recording` com `status=ready`.
7. A API expõe o catálogo em `/api/v1/recordings`.

### 4.3 Abstração da origem do vídeo

A origem do vídeo é isolada pelo contrato `SourceAdapter` (`app/sources/base.py`):

```python
class SourceAdapter(ABC):
    source_id: int
    name: str

    @abstractmethod
    def availability_error(self) -> str | None: ...

    @abstractmethod
    def scan(self) -> Iterable[RecordingCandidate]: ...
```

O scanner **não conhece** OBS, filesystem ou qualquer detalhe concreto; ele recebe candidatos (`path`, `size_bytes`, `modified_at`). O adaptador ativo é escolhido por `LIVECLIPPER_SOURCE_ADAPTER` e resolvido em `app/sources/factory.py`.

Adaptadores disponíveis na Fase 1:

| Nome | Implementação | Descrição |
| --- | --- | --- |
| `obs_directory` | `LocalObsDirectorySource` | Lê gravações locais produzidas pelo OBS. |

Para adicionar uma nova origem:

```python
from app.sources.base import RecordingCandidate, SourceAdapter
from app.sources.factory import register_source_adapter


class MinhaFonte(SourceAdapter):
    def __init__(self, source):
        self.source_id = source.id
        self.name = source.name

    def availability_error(self) -> str | None:
        return None

    def scan(self):
        # Retorne caminhos locais acessíveis; não baixe conteúdo externo.
        yield RecordingCandidate(path=..., size_bytes=..., modified_at=...)


register_source_adapter("minha_fonte", MinhaFonte)
```

Depois, defina `LIVECLIPPER_SOURCE_ADAPTER=minha_fonte`. O monitor e o scanner continuam inalterados. Uma fase futura poderá persistir o tipo do adaptador **por fonte**; o contrato atual já suporta essa evolução.

## 5. Configuração

Todas as variáveis usam o prefixo `LIVECLIPPER_` e podem vir do ambiente ou de um arquivo `.env` na raiz. O modelo está em `app/config.py`; o exemplo versionado é `.env.example`.

| Variável | Padrão | Uso |
| --- | --- | --- |
| `LIVECLIPPER_APP_NAME` | `LiveClipper` | Nome exibido no OpenAPI. |
| `LIVECLIPPER_ENVIRONMENT` | `development` | Ambiente lógico (`development`, `test`, `production`). |
| `LIVECLIPPER_LOG_LEVEL` | `INFO` | Nível de log do processo. |
| `LIVECLIPPER_API_PREFIX` | `/api/v1` | Prefixo das rotas versionadas. |
| `LIVECLIPPER_DATA_DIR` | `./data` | Diretório de dados locais. |
| `LIVECLIPPER_OUTPUT_DIR` | `./output` | Diretório de artefatos futuros. |
| `LIVECLIPPER_DATABASE_URL` | `sqlite:///./data/liveclipper.db` | URL SQLAlchemy. |
| `LIVECLIPPER_OBS_RECORDINGS_DIR` | vazio | Diretório global de gravações do OBS; pode ser omitido se cada fonte informar `watch_directory`. |
| `LIVECLIPPER_OBS_WEBSOCKET_URL` | `ws://127.0.0.1:4455` | URL reservada para a integração futura. **Não é usada na Fase 1.** |
| `LIVECLIPPER_OBS_WEBSOCKET_PASSWORD` | vazio | Senha reservada para a integração futura, carregada como `SecretStr`. Nunca é serializada pela API. |
| `LIVECLIPPER_SOURCE_ADAPTER` | `obs_directory` | Adaptador de origem do vídeo. |
| `LIVECLIPPER_RECORDING_EXTENSIONS` | `.mkv,.mp4,.mov,.flv,.ts` | Allowlist global de extensões. |
| `LIVECLIPPER_CAPTURE_POLL_INTERVAL_SECONDS` | `5` | Intervalo entre varreduras. |
| `LIVECLIPPER_CAPTURE_SETTLE_SECONDS` | `20` | Tempo sem alteração para considerar a gravação encerrada. |
| `LIVECLIPPER_CAPTURE_AUTO_START` | `true` | Inicia o monitor junto com a aplicação. |

Diretórios operacionais são criados na inicialização. O `.env` é ignorado pelo Git; apenas `.env.example` é versionado.

## 6. Banco de dados

O banco padrão é SQLite (`data/liveclipper.db`). O engine habilita `foreign_keys=ON`, `busy_timeout=5000`, `check_same_thread=False` e `pool_pre_ping`. O schema inicial é criado com `create_all`; migrações com Alembic estão previstas para a Fase 2.

### 6.1 `capture_sources`

| Campo | Tipo | Regra |
| --- | --- | --- |
| `id` | inteiro | Chave primária. |
| `name` | texto(160) | Único, indexado. |
| `platform`, `creator_name` | texto | Rastreabilidade. |
| `authorization_reference` | texto(255) | Obrigatório. |
| `authorization_notes` | texto | Opcional. |
| `authorized_at` | UTC | Data do aceite da autorização. |
| `watch_directory` | texto(1024) | Diretório absoluto observado. |
| `file_extensions` | JSON | Allowlist normalizada. |
| `enabled` | booleano | Habilita a varredura. |
| `created_at`, `updated_at` | UTC | Auditoria. |

### 6.2 `recordings`

| Campo | Tipo | Regra |
| --- | --- | --- |
| `id` | inteiro | Chave primária. |
| `source_id` | FK | `ON DELETE CASCADE`, indexado. |
| `path` | texto(2048) | Único; identidade e idempotência. |
| `filename`, `size_bytes`, `modified_at` | — | Metadados do arquivo. |
| `status` | enum | `ready`, `processing`, `completed`, `failed`, `ignored`. |
| `discovered_at`, `ready_at` | UTC | Linha do tempo da ingestão. |
| `error_message` | texto | Diagnóstico futuro. |
| `created_at`, `updated_at` | UTC | Auditoria. |

Todos os timestamps são normalizados em UTC por `UTCDateTime`, inclusive no SQLite.

## 7. API HTTP

A API é servida por padrão em `127.0.0.1:8000`. OpenAPI em `/docs`.

| Método | Caminho | Descrição |
| --- | --- | --- |
| `GET` | `/` | Identificação da aplicação e da fase. |
| `GET` | `/health` | Banco + estado do monitor; `503` se o banco falhar. |
| `GET` | `/api/v1/obs/status` | Diagnóstico da configuração do OBS (sem conectar no WebSocket). |
| `POST` | `/api/v1/sources` | Cadastra fonte autorizada. |
| `GET` | `/api/v1/sources` | Lista fontes (`enabled_only`). |
| `GET` | `/api/v1/sources/{id}` | Detalha uma fonte. |
| `POST` | `/api/v1/capture/scan` | Varredura manual; aceita `?source_id=`. |
| `GET` | `/api/v1/capture/status` | Estado do monitor. |
| `GET` | `/api/v1/recordings` | Lista gravações (`status`, `source_id`, `limit`, `offset`). |
| `GET` | `/api/v1/recordings/{id}` | Detalha uma gravação. |

Exemplo de `/health`:

```json
{
  "status": "ok",
  "database": "ok",
  "version": "0.1.0",
  "environment": "development",
  "capture_monitor": {
    "running": true,
    "poll_interval_seconds": 5.0,
    "last_scan_at": "2026-11-17T12:00:00Z",
    "last_success_at": "2026-11-17T12:00:00Z",
    "last_error": null
  }
}
```

## 8. Captura de janela do navegador e áudio com OBS

O fluxo recomendado é:

1. Abrir no navegador o conteúdo para o qual existe autorização.
2. No OBS, criar uma fonte **Window Capture** (ou **macOS Screen Capture → Window** / **PipeWire** no Linux) apontando para a janela do navegador.
3. Capturar o áudio da aplicação (`Application Audio Capture`) ou da saída do sistema (`Desktop Audio`), conforme o sistema operacional.
4. Ajustar enquadramento, níveis de áudio e faixas de gravação.
5. Gravar em `.mkv` no diretório observado pelo LiveClipper.

O passo a passo detalhado, incluindo Windows, Linux, macOS, áudio por aplicativo, faixas múltiplas e solução de problemas, está em [`obs-setup.md`](obs-setup.md).

> A captura é sempre da janela visível e autorizada. Não use o projeto para contornar proteções da plataforma, DRM ou restrições de acesso.

## 9. Integração futura com o OBS WebSocket

**Não implementada na Fase 1.** Hoje existem apenas:

- as variáveis `LIVECLIPPER_OBS_WEBSOCKET_URL` e `LIVECLIPPER_OBS_WEBSOCKET_PASSWORD`;
- o contrato `ObsClient` em `app/obs/client.py`;
- o diagnóstico `GET /api/v1/obs/status`, que **não abre conexão**.

O WebSocket será usado futuramente para saber quando uma gravação começou/terminou, consultar o diretório de saída e, opcionalmente, controlar gravação e replay buffer. O desenho, os eventos, os comandos, a reconexão e os cuidados de segurança estão documentados em [`obs-websocket.md`](obs-websocket.md), sem implementação nesta fase.

## 10. Monitoramento da pasta de gravações

A Fase 1 já implementa **polling** da pasta de gravações: o monitor varre as fontes habilitadas, aplica a regra de estabilidade (`mtime` mais antigo que `now - settle`), ignora arquivos vazios e deduplica por caminho absoluto.

Evoluções futuras documentadas — notificação por evento do OBS, `watchdog`/inotify, metadados com FFprobe, retenção, remux e limites de armazenamento — estão em [`recordings-monitoring.md`](recordings-monitoring.md).

## 11. Fases do projeto

| Fase | Tema | Estado |
| --- | --- | --- |
| 0 | Estrutura, configuração, banco, health, testes e documentação | Concluída |
| 1 | Ingestão de gravações autorizadas do OBS + catálogo | Concluída |
| 2 | Metadados (FFprobe), buffer circular, retenção e Alembic | Planejada |
| 3 | Detecção por áudio/transcrição/chat e pontuação de candidatos | Planejada |
| 4 | Recorte e enquadramento vertical com FFmpeg/OpenCV | Planejada |
| 5 | Legendas com Faster-Whisper | Planejada |
| 6 | OAuth 2.0 e publicação no YouTube Data API v3 | Planejada |

O detalhamento está em [`roadmap.md`](roadmap.md).

## 12. Qualidade e testes

- `pytest` usa banco SQLite temporário, diretórios temporários e monitor em background desligado.
- Os testes cobrem health, cadastro autorizado, validação de diretório, ingestão, estabilidade, deduplicação, monitor, diagnóstico do OBS e registro de adaptadores.
- Comandos:

```bash
pytest
pytest --cov=app
```

- Configuração do Pytest em `pyproject.toml` (`testpaths`, `pythonpath`, avisos de depreciação da aplicação).

## 13. Segurança operacional

- A API não possui autenticação e pressupõe execução local/confiável.
- O servidor deve escutar em `127.0.0.1` ou em rede confiável; para exposição remota, use autenticação, TLS e controle de acesso.
- Nenhuma credencial é armazenada no código; segredos vêm do `.env` e a senha do OBS usa `SecretStr`.
- A senha do OBS WebSocket nunca é retornada pela API.
- O projeto lê apenas arquivos locais; não faz download de transmissões nem acessa URLs internas de plataformas.
- Permissões de leitura são verificadas pelo adaptador local.
- Symlinks que apontam para fora do diretório autorizado são ignorados.
- Publicação automática, OAuth e upload não existem nesta fase.

A política completa, os controles e o checklist de revisão estão em [`SECURITY.md`](SECURITY.md).

## 14. Decisões e limites

| Decisão | Motivo | Limite |
| --- | --- | --- |
| OBS como origem oficial | Captura autorizada e controle do operador | Requer OBS configurado localmente |
| Polling em vez de inotify | Portátil, previsível e sem dependências | Latência de até um intervalo |
| Estabilidade por `mtime` | Simples e sem dependências externas | Arquivo pausado pode parecer estável; ajuste o settle |
| Deduplicação por caminho | Idempotência | Um mesmo conteúdo em dois caminhos gera dois registros |
| SQLite | Simplicidade local | Avaliar PostgreSQL para múltiplos workers |
| `create_all` | Schema inicial pequeno | Migrações reais via Alembic na Fase 2 |
| Sem WebSocket na Fase 1 | Não é necessário para ingerir arquivos | Controle remoto fica para fase futura |
| Adaptador por configuração global | Permite trocar a origem sem alterar o scanner | Tipo por fonte exige evolução do schema |

## 15. Critérios de aceite da Fase 1

- [x] Diretório inspecionado antes de qualquer alteração.
- [x] Ambiente Python configurado (`pyproject.toml`, `.venv`, dependências de desenvolvimento).
- [x] FastAPI com `GET /health` verificando banco e monitor.
- [x] SQLite e SQLAlchemy configurados com modelos e repositórios.
- [x] Configuração centralizada por variáveis de ambiente.
- [x] `.env.example` versionado e `.env` ignorado.
- [x] `.gitignore` cobre ambiente virtual, dados, saídas e bancos.
- [x] Pytest configurado e suíte verde.
- [x] `README.md` em português.
- [x] `docs/PROJECT_SPEC.md` documentando o projeto e as fases.
- [x] Captura de janela do navegador e áudio documentada para OBS.
- [x] Integração futura com OBS WebSocket documentada, sem implementação.
- [x] Monitoramento futuro da pasta de gravações documentado.
- [x] Interfaces de origem de vídeo substituíveis (`SourceAdapter` + registro).
- [x] Requisitos de segurança, autorização e higiene do Git documentados e testados.
- [x] Nenhuma credencial armazenada no código-fonte; `.env.example` sem segredos.
- [x] Gravações, bancos, `.env` e tokens fora do Git.
- [x] Publicação automática ausente (sem OAuth, upload ou rotas de publicação).
- [x] Sem download de transmissões ou acesso a fontes privadas/protegidas; symlinks externos ignorados.

## 16. Documentos relacionados

- [`README.md`](../README.md) — instalação, execução e uso rápido.
- [`architecture.md`](architecture.md) — decisões técnicas e fluxo detalhado.
- [`SECURITY.md`](SECURITY.md) — segurança, autorização, segredos e publicação desativada.
- [`obs-setup.md`](obs-setup.md) — configuração do OBS para janela do navegador e áudio.
- [`obs-websocket.md`](obs-websocket.md) — desenho da integração futura, não implementada.
- [`recordings-monitoring.md`](recordings-monitoring.md) — monitoramento atual e evoluções futuras.
- [`roadmap.md`](roadmap.md) — fases do produto.

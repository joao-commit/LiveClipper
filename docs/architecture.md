# Arquitetura — Fase 1

## 1. Princípios

1. **Autorização primeiro:** nenhuma fonte pode ser cadastrada sem referência de autorização e confirmação explícita. O sistema registra a evidência; não a substitui.
2. **OBS é a origem oficial:** a captura audiovisual acontece no OBS Studio. O LiveClipper observa as gravações resultantes.
3. **Sem contorno de plataforma:** não há download de transmissão, extração de URL interna, DRM ou bypass de restrição.
4. **Fronteiras pequenas:** cada pacote tem uma responsabilidade clara e depende de contratos, não de detalhes de outros módulos.
5. **Evolução incremental:** as fases posteriores entram sem reescrever a ingestão.

## 2. Componentes

```text
OBS Studio
   │ grava .mkv/.mp4/... em um diretório local
   ▼
sources (LocalObsDirectorySource)
   │ lista arquivos suportados + tamanho + mtime
   ▼
capture.scanner
   │ descarta arquivos instáveis, vazios e duplicados
   ▼
database (capture_sources, recordings)
   │
   ├── capture.monitor  → varredura periódica em thread separada
   └── api              → FastAPI/REST + health
```

| Pacote | Responsabilidade na Fase 1 |
| --- | --- |
| `app.obs` | Configuração e diagnóstico do OBS. Contrato futuro para WebSocket. |
| `app.sources` | Abstração de fontes, adaptador de diretório local, registro de adaptadores, cadastro autorizado e normalização de extensões. |
| `app.capture` | Varredura, regra de estabilidade, deduplicação e monitor periódico. |
| `app.database` | Modelos SQLAlchemy, sessão, `create_all` e repositórios. |
| `app.api` | Routers, dependências, schemas Pydantic e tratamento HTTP. |
| `app.detection` | Reservado para áudio/transcrição/chat (Fase 3). |
| `app.clipping` | Reservado para FFmpeg/OpenCV (Fase 4). |
| `app.publishing` | Reservado para YouTube/OAuth (Fase 6). |

## 3. Fluxo de ingestão

1. A API cria uma `CaptureSource` com `authorization_reference`, `authorization_notes` e `authorized_at`.
2. O monitor (`CaptureMonitor`) executa a cada `CAPTURE_POLL_INTERVAL_SECONDS`.
3. Para cada fonte habilitada, o adaptador registrado em `app.sources.factory` lista arquivos cuja extensão está na allowlist da fonte. O adaptador ativo vem de `LIVECLIPPER_SOURCE_ADAPTER` (padrão `obs_directory`); o scanner só conhece o contrato `SourceAdapter`.
4. O scanner aplica:
   - **tamanho > 0** (caso contrário: `ignored`);
   - **mtime mais antigo que `now - CAPTURE_SETTLE_SECONDS`** (caso contrário: `unstable`);
   - **path ainda não persistido** (caso contrário: `duplicate`);
5. O arquivo estável vira um `Recording` com `status=ready`.
6. A API expõe o catálogo em `/api/v1/recordings`.

A deduplicação usa a restrição `UNIQUE(path)`. Se duas varreduras concorrerem, a segunda recebe `IntegrityError` e contabiliza duplicidade, sem quebrar o lote.

## 4. Modelo de dados

### `capture_sources`

| Campo | Uso |
| --- | --- |
| `name` | Identificador único da fonte |
| `platform`, `creator_name` | Metadados de rastreabilidade |
| `authorization_reference` | Contrato, e-mail, ticket ou termo que comprova a permissão |
| `authorization_notes` | Contexto adicional |
| `authorized_at` | Quando o cadastro autorizado foi aceito |
| `watch_directory` | Diretório absoluto observado |
| `file_extensions` | Allowlist JSON normalizada |
| `enabled` | Habilita/desabilita a varredura |

### `recordings`

| Campo | Uso |
| --- | --- |
| `source_id` | FK com `ON DELETE CASCADE` |
| `path` | Caminho absoluto único (idempotência) |
| `filename`, `size_bytes`, `modified_at` | Metadados do arquivo |
| `status` | `ready`, `processing`, `completed`, `failed`, `ignored` |
| `discovered_at`, `ready_at` | Linha do tempo da ingestão |
| `error_message` | Diagnóstico futuro |

Todos os timestamps são normalizados em UTC por um `TypeDecorator`, inclusive no SQLite (que não preserva offsets nativamente).

## 5. Concorrência e ciclo de vida

- O FastAPI usa `lifespan` para criar engine, tabelas, sessões e iniciar o monitor.
- O monitor roda no event loop, mas a varredura síncrona é executada com `asyncio.to_thread`.
- Um `asyncio.Lock` impede varreduras simultâneas do monitor.
- Cada requisição HTTP recebe uma sessão própria; a sessão sempre é fechada e sofre rollback em exceção.
- SQLite usa `check_same_thread=False`, `foreign_keys=ON` e `busy_timeout=5000`.
- No shutdown, o monitor é parado e o engine descartado.

### Segurança operacional

A API da Fase 1 não possui autenticação e pressupõe execução local/confiável. O bind padrão é `127.0.0.1`. Antes de expor remotamente, adicione autenticação, TLS e controle de acesso em um reverse proxy ou em uma camada própria. As senhas do OBS WebSocket usam `SecretStr` e nunca são serializadas nos endpoints de diagnóstico.

O adaptador local ignora symlinks e valida que cada arquivo resolvido permanece dentro do diretório autorizado. A Fase 1 não baixa transmissões, não acessa fontes protegidas e não publica conteúdo. Consulte [`SECURITY.md`](SECURITY.md).

## 6. Autorização e conformidade

O cadastro exige `authorization_confirmed: true`. Campos vazios são rejeitados. A varredura revalida a presença de `authorization_reference` e `authorized_at` — proteção contra registros inseridos manualmente no banco sem o fluxo da API.

Responsabilidades do operador:

- obter e arquivar a autorização de captura **e** de reutilização;
- limitar a captura ao conteúdo e período autorizados;
- respeitar termos da plataforma, direitos de terceiros (música, convidados) e legislação aplicável;
- remover dados quando a autorização expirar.

O LiveClipper não decide se o uso é lícito; ele registra a fonte autorizada e impede o cadastro sem confirmação.

## 7. Decisões e limites da Fase 1

| Decisão | Motivo | Limite |
| --- | --- | --- |
| Ler arquivos do OBS | Simples, robusto, sem depender de rede ou plugin | Requer que o OBS grave localmente |
| Polling em vez de inotify | Portátil e previsível | Latência de até um intervalo de polling |
| Heurística por `mtime` | Sem dependências externas | Um arquivo pausado pode ser considerado estável; ajuste o settle |
| `create_all` | Banco novo e schema pequeno | Migrações reais entram com Alembic quando o schema evoluir |
| SQLite | Desenvolvimento e execução local simples | Para múltiplos workers/alta concorrência, avaliar PostgreSQL |
| Sem WebSocket OBS | Não é necessário para ingerir arquivos | Controle de gravação/replay buffer fica para fase futura ([desenho](obs-websocket.md)) |

### 7.1 Limites explícitos desta fase

Não fazem parte desta fase e não devem receber código, rota, dependência ou stub:

- detector de picos ou qualquer análise de áudio;
- captura ativa pelo OBS (iniciar/parar gravação, replay buffer);
- buffer circular de segmentos;
- transcrição;
- recorte de vídeos;
- legendas;
- publicação no YouTube;
- interface gráfica.

Os pacotes `detection/`, `clipping/` e `publishing/` existem apenas como documentação de fronteira. Funções fictícias para “preencher” módulos são proibidas; a implementação entra junto com a fase correspondente. `app/obs/client.py` define um `Protocol` de tipos, sem implementação executável.

## 8. Próximas fases (visão)

- **Fase 2:** metadados com FFprobe, buffer circular de segmentos e política de retenção.
- **Fase 3:** detecção por áudio/transcrição e chat autorizado, com pontuação de candidatos.
- **Fase 4:** recorte e enquadramento vertical com FFmpeg/OpenCV.
- **Fase 5:** legendas com Faster-Whisper.
- **Fase 6:** OAuth 2.0 e publicação via YouTube Data API v3.

Cada fase deve adicionar dependências apenas quando necessárias e manter a origem em gravações autorizadas.

## 9. Documentos relacionados

- [`PROJECT_SPEC.md`](PROJECT_SPEC.md) — especificação funcional e critérios de aceite.
- [`SECURITY.md`](SECURITY.md) — requisitos de segurança e autorização.
- [`obs-setup.md`](obs-setup.md) — captura de janela do navegador e áudio.
- [`obs-websocket.md`](obs-websocket.md) — integração futura não implementada.
- [`recordings-monitoring.md`](recordings-monitoring.md) — monitoramento atual e futuro da pasta.
- [`roadmap.md`](roadmap.md) — fases do produto.

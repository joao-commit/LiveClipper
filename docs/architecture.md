# Arquitetura — LiveClipper 2.0

## 1. Princípios

1. **Autorização primeiro:** nenhuma fonte pode ser cadastrada sem referência de autorização e confirmação explícita. O sistema registra a evidência; não a substitui.
2. **OBS é a origem oficial:** a captura audiovisual acontece no OBS Studio. O LiveClipper observa as gravações resultantes.
3. **Detecção, não edição:** o produto identifica momentos e entrega uma tabela de candidatos. Ele não recorta, renderiza, legenda ou publica.
4. **Sem contorno de plataforma:** não há download de transmissão, extração de URL interna, DRM ou bypass de restrição.
5. **Fronteiras pequenas:** cada pacote tem uma responsabilidade clara e depende de contratos, não de detalhes de outros módulos.
6. **Evolução incremental:** a fundação de ingestão é preservada; a detecção entra por cima dela, sem reescrever o que já funciona.
7. **Dependências sob demanda:** FFmpeg/FFprobe e Faster-Whisper entram somente na fase que os utiliza. OpenCV não entra.

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
   ├── detection        → módulo principal planejado
   │     ├── audio.py/ffmpeg (futuro)
   │     ├── transcription.py (futuro)
   │     └── candidates.py (futuro)
   └── api              → FastAPI/REST + health + futura tabela
```

| Pacote | Responsabilidade atual | Evolução |
| --- | --- | --- |
| `app.obs` | Configuração e diagnóstico do OBS. Contrato futuro para WebSocket. | Abrir/fechar sessões com precisão, se necessário. |
| `app.sources` | Abstração de fontes, adaptador de diretório local, registro, cadastro autorizado e normalização de extensões. | Mantido sem alteração estrutural. |
| `app.capture` | Varredura, regra de estabilidade, deduplicação e monitor periódico. | Associar gravações a sessões. |
| `app.database` | Modelos SQLAlchemy, sessão, `create_all` e repositórios. | Novas tabelas e migração aditiva. |
| `app.detection` | Nesta revisão, apenas documentação do escopo. | **Núcleo funcional:** áudio, transcrição, evidências e candidatos. |
| `app.api` | Routers, dependências, schemas Pydantic e tratamento HTTP. | Nova rota de consulta de candidatos. |
| `app.clipping` | Fora do escopo; vazio. | Não desenvolver. |
| `app.publishing` | Fora do escopo; vazio. | Não desenvolver. |

## 3. Fluxo de ingestão atual

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

## 4. Modelo de dados e continuidade temporal

### 4.1 Tabelas existentes

`capture_sources` guarda a fonte autorizada, o diretório observado, a allowlist e a evidência de autorização.

`recordings` guarda um arquivo por linha:

| Campo | Uso |
| --- | --- |
| `source_id` | FK com `ON DELETE CASCADE` |
| `path` | Caminho absoluto único (idempotência) |
| `filename`, `size_bytes`, `modified_at` | Metadados do arquivo |
| `status` | `ready`, `processing`, `completed`, `failed`, `ignored` |
| `discovered_at`, `ready_at` | Linha do tempo da ingestão |
| `error_message` | Diagnóstico |

### 4.2 Por que `recordings` não basta

O modelo é orientado a **arquivo**, não a **transmissão**:

- o OBS pode dividir uma transmissão em vários arquivos;
- não há vínculo entre esses arquivos;
- `modified_at` não é o início da captura;
- não há duração nem deslocamento relativo;
- portanto, não é possível calcular tempos relativos à transmissão nem saber se dois segmentos são contínuos.

Consequência: os tempos de `clip_candidates` não podem ser confiáveis se forem relativos apenas a um `recording` isolado. É necessária uma **sessão de captura**.

### 4.3 `capture_sessions` (proposta)

| Campo | Uso |
| --- | --- |
| `id` | Identidade da sessão. |
| `source_id` | Fonte autorizada dona da sessão. |
| `started_at` | Instante zero da linha do tempo. |
| `ended_at` | Fim da captura, nulo enquanto ativa. |
| `status` | `active`, `closed`, `incomplete`, `failed`. |
| `external_reference` | Referência opcional do OBS/arquivo inicial. |
| `created_at`, `updated_at` | Auditoria. |

`recordings` recebe, de forma aditiva:

- `session_id` (FK anulável para dados legados);
- `segment_index`;
- `start_offset_seconds`;
- `duration_seconds`.

A sessão pode ser criada de duas formas:

1. **Com OBS WebSocket (futuro):** evento de início/parada abre e fecha a sessão com precisão.
2. **Sem WebSocket (transição):** o coordenador infere a sessão pela ordem dos arquivos, proximidade temporal e duração obtida por FFprobe. O `started_at` é aproximado e deve ser tratado como tal.

Uma sessão não é necessariamente a transmissão inteira: quedas, pausas longas e reinícios podem abrir uma nova sessão. O importante é que cada sessão tenha um instante zero estável e que os arquivos estejam ordenados dentro dela.

### 4.4 `clip_candidates` (proposta)

| Campo | Uso |
| --- | --- |
| `id` | Chave primária. |
| `source_id` | FK da fonte autorizada. |
| `session_id` | FK da sessão; âncora temporal. |
| `recording_id` | FK do arquivo onde o trecho começa (anulável após retenção). |
| `start_seconds` | Início relativo ao início da sessão. |
| `end_seconds` | Fim relativo ao início da sessão. |
| `description` | Descrição simples do acontecimento. |
| `score` | Pontuação interna (0..1). |
| `created_at` | Criação. |

Regras:

- `0 <= start_seconds < end_seconds`.
- `0 <= score <= 1`.
- Índice por `(session_id, start_seconds)` para consultas por sessão.
- A saída para o operador expõe apenas início, fim e descrição.
- `recording_id` identifica o arquivo inicial; se o trecho atravessar arquivos, a sessão mantém a continuidade.

### 4.5 Migração

A revisão atual **não altera o banco**. A evolução será não destrutiva:

- novas tabelas são aditivas;
- `recordings.session_id` exige migração real com Alembic, pois `create_all` não altera tabelas existentes;
- nenhuma coluna existente será removida ou renomeada;
- registros legados podem permanecer com `session_id` nulo;
- backfill é opcional e não deve inventar precisão temporal.

## 5. Pipeline de detecção planejado

```text
recordings estáveis
        │
        ▼
capture_sessions
        │ instante zero
        ▼
FFprobe ── valida faixa de áudio, duração e codecs
        │
        ▼
FFmpeg ── extrai PCM mono 16 kHz em janelas
        │
        ├── análise de energia/picos (futuro)
        └── Faster-Whisper (futuro)
        │
        ▼
evidências com timestamps relativos à sessão
        │
        ▼
montagem de candidatos
        │ duração mínima/máxima, score, descrição
        ▼
clip_candidates
        │
        ▼
API: início, fim, descrição
```

### 5.1 FFmpeg/FFprobe

- Binários externos, não dependências Python.
- FFprobe obtém duração, codecs e faixas de áudio.
- FFmpeg extrai áudio mono em PCM 16 kHz para análise e transcrição.
- Invocação com lista de argumentos (sem `shell=True`), timeout e caminhos catalogados.
- Arquivos temporários ficam em `data/` ou diretório de trabalho controlado.
- Falhas são registradas em `error_message` e não derrubam o monitor.

### 5.2 Faster-Whisper

- Dependência Python opcional, adicionada somente na fase de transcrição.
- Modelo carregado de forma preguiçosa e configurável.
- Transcrição produz texto e timestamps; o offset da janela é somado ao offset do arquivo e ao início da sessão.
- Em CPU, o padrão sugerido é `int8`; GPU é opcional.
- O modelo não deve ser baixado automaticamente em CI; testes usarão um duplo de teste.

### 5.3 Detector de picos

Não implementado nesta revisão. A próxima fase definirá:

- janela de análise e suavização;
- limiar relativo ao ruído de fundo;
- duração mínima/máxima do candidato;
- fusão de picos próximos;
- uso da transcrição para descrição e priorização;
- escala e calibração do score.

### 5.4 Vídeo

O vídeo é ingerido e catalogado. A análise inicial é centrada em áudio/fala, sem OpenCV. FFprobe pode fornecer metadados visuais; qualquer análise visual futura deve usar FFmpeg ou outra abordagem que não introduza OpenCV sem justificativa.

### 5.5 Tempo real e latência

A ingestão atual é orientada a arquivos estáveis. Para a detecção acompanhar a transmissão, a estratégia planejada é gravar em segmentos curtos, registrar cada segmento ao estabilizar e enfileirá-lo para análise. A latência será a soma do `settle`, da extração de áudio e da análise.

Isso não é streaming frame a frame: não há buffer circular nem captura ativa nesta revisão. A vantagem é reaproveitar o monitor, a deduplicação e o catálogo existentes, mantendo a análise incremental e tolerante a falhas.

## 6. Concorrência e ciclo de vida

- O FastAPI usa `lifespan` para criar engine, tabelas, sessões e iniciar o monitor.
- O monitor roda no event loop, mas a varredura síncrona é executada com `asyncio.to_thread`.
- Um `asyncio.Lock` impede varreduras simultâneas do monitor.
- Cada requisição HTTP recebe uma sessão própria; a sessão sempre é fechada e sofre rollback em exceção.
- SQLite usa `check_same_thread=False`, `foreign_keys=ON` e `busy_timeout=5000`.
- No shutdown, o monitor é parado e o engine descartado.
- A futura detecção deve rodar em worker separado do monitor para não bloquear a ingestão; a fila e o paralelismo serão definidos na fase de detecção.

## 7. Segurança operacional

A API atual não possui autenticação e pressupõe execução local/confiável. O bind padrão é `127.0.0.1`. Antes de expor remotamente, adicione autenticação, TLS e controle de acesso em um reverse proxy ou em uma camada própria. As senhas do OBS WebSocket usam `SecretStr` e nunca são serializadas nos endpoints de diagnóstico.

O adaptador local ignora symlinks e valida que cada arquivo resolvido permanece dentro do diretório autorizado. O sistema não baixa transmissões, não acessa fontes protegidas e não publica conteúdo. Consulte [`SECURITY.md`](SECURITY.md).

Novos cuidados da detecção:

- invocar FFmpeg/FFprobe sem shell;
- limitar tempo e tamanho de saída;
- não expor transcrições completas em logs;
- tratar descrições e transcrições como dados privados;
- não permitir caminhos arbitrários fornecidos por usuários da API.

## 8. Autorização e conformidade

O cadastro exige `authorization_confirmed: true`. Campos vazios são rejeitados. A varredura revalida a presença de `authorization_reference` e `authorized_at` — proteção contra registros inseridos manualmente no banco sem o fluxo da API.

Responsabilidades do operador:

- obter e arquivar a autorização de captura, análise e reutilização;
- limitar a captura ao conteúdo e período autorizados;
- respeitar termos da plataforma, direitos de terceiros (música, convidados) e legislação aplicável;
- revisar os candidatos antes de qualquer uso externo;
- remover dados quando a autorização expirar.

O LiveClipper não decide se o uso é lícito; ele registra a fonte autorizada e impede o cadastro sem confirmação.

## 9. Decisões e limites

| Decisão | Motivo | Limite |
| --- | --- | --- |
| Ler arquivos do OBS | Simples, robusto, sem depender de rede ou plugin | Requer que o OBS grave localmente |
| Polling em vez de inotify | Portátil e previsível | Latência de até um intervalo de polling |
| Heurística por `mtime` | Sem dependências externas | Um arquivo pausado pode ser considerado estável; ajuste o settle |
| Sessões explícitas | Preservar continuidade entre arquivos | Exatidão depende do WebSocket ou de inferência |
| Tempos relativos à sessão | Não quebram quando o OBS divide arquivos | Sessão aproximada gera timestamps aproximados |
| `create_all` no schema atual | Banco novo e schema pequeno | Evolução de colunas exige Alembic |
| SQLite | Desenvolvimento e execução local simples | Para múltiplos workers/alta concorrência, avaliar PostgreSQL |
| Sem OpenCV | Não é necessário para análise inicial de áudio | Análise visual avançada fica fora do escopo |
| Sem edição/publicação | O produto entrega candidatos para revisão humana | Nenhum vídeo é gerado ou enviado |

### 9.1 Limites explícitos

Não fazem parte do projeto e não devem receber código, rota, dependência ou stub:

- edição, recorte ou renderização de vídeo;
- Shorts e conversão vertical 9:16;
- legendas;
- publicação no YouTube ou em qualquer plataforma;
- OAuth, upload e agendamento;
- OpenCV;
- interface gráfica.

Nesta revisão também não entram:

- detector de picos;
- transcrição executável;
- tabelas e migrações;
- rotas de detecção/candidatos.

`app.detection` contém apenas a documentação do escopo futuro. `app.clipping` e `app.publishing` permanecem vazios como marcadores históricos, sem funções executáveis.

## 10. Próximas fases (visão)

- **Fase 3:** sessões de captura, evolução aditiva de `recordings`, tabela `clip_candidates`, FFprobe e migração com Alembic.
- **Fase 4:** extração de áudio com FFmpeg, detector de picos, Faster-Whisper, descrição e pontuação.
- **Fase 5:** calibração, retenção, robustez, observabilidade e testes de carga.

Cada fase adiciona dependências apenas quando necessárias e mantém a origem em gravações autorizadas.

## 11. Documentos relacionados

- [`PROJECT_SPEC.md`](PROJECT_SPEC.md) — especificação funcional e critérios de aceite.
- [`SECURITY.md`](SECURITY.md) — requisitos de segurança e autorização.
- [`obs-setup.md`](obs-setup.md) — captura de janela do navegador e áudio.
- [`obs-websocket.md`](obs-websocket.md) — integração futura não implementada.
- [`recordings-monitoring.md`](recordings-monitoring.md) — monitoramento atual e futuro da pasta.
- [`roadmap.md`](roadmap.md) — fases do produto.

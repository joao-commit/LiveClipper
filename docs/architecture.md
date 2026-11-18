# Arquitetura — LiveClipper 2.0

## 1. Princípios

1. **Autorização primeiro:** nenhuma fonte pode ser capturada ou analisada sem referência de autorização e confirmação explícita.
2. **OBS é a fonte oficial:** a captura audiovisual acontece no OBS Studio; o LiveClipper observa as gravações resultantes.
3. **Detecção, não edição:** o produto identifica momentos e entrega uma tabela de candidatos. Ele não recorta, renderiza, legenda ou publica.
4. **Sessão é a linha do tempo:** os tempos são relativos ao início da sessão de captura, não a um arquivo isolado.
5. **Áudio e transcrição primeiro:** o MVP prioriza intensidade sonora e fala. Análise visual não é obrigatória.
6. **Fronteiras pequenas:** captura, persistência, detecção e API se comunicam por contratos claros.
7. **Evolução incremental:** a fundação existente é preservada; as novas tabelas e o detector entram em fases posteriores.
8. **Dependências sob demanda:** FFmpeg/FFprobe e Faster-Whisper entram somente quando suas fases forem implementadas.

## 2. Componentes

```text
OBS Studio
   │ grava segmentos em diretório local
   ▼
app.sources ── SourceAdapter / cadastro autorizado
   │ caminho, tamanho, mtime
   ▼
app.capture.scanner + monitor
   │ estabilidade, deduplicação, polling
   ▼
app.database (SQLite + SQLAlchemy)
   │ capture_sources · recordings
   │ [planejado] capture_sessions · clip_candidates
   │
   ├── app.detection  ← núcleo planejado
   │      ├── FFmpeg/FFprobe
   │      ├── análise de intensidade
   │      ├── Faster-Whisper
   │      └── candidatos
   │
   └── app.api (FastAPI)
          ├── endpoints existentes
          └── [planejado] consulta de candidatos
```

| Pacote | Responsabilidade |
| --- | --- |
| `app.config` | Configuração por ambiente e `.env` com Pydantic Settings. |
| `app.database` | Modelos SQLAlchemy, sessão, `create_all` e repositórios. |
| `app.sources` | Cadastro autorizado, contrato `SourceAdapter`, adaptador local e registro. |
| `app.capture` | Varredura, estabilidade, deduplicação e monitor periódico. |
| `app.obs` | Diagnóstico do OBS e contrato futuro `ObsClient`. |
| `app.detection` | Núcleo planejado: sessões, áudio, transcrição, delimitação e candidatos. Nesta revisão, apenas documentação. |
| `app.api` | Rotas, dependências, schemas HTTP e tratamento de erros. |
| `app.clipping` | Fora do escopo; vazio, sem código executável. |
| `app.publishing` | Fora do escopo; vazio, sem código executável. |

## 3. Ingestão atual

1. O OBS grava a janela autorizada e o áudio em um diretório local.
2. O operador cadastra uma fonte via `POST /api/v1/sources`, com `authorization_reference` e `watch_directory`.
3. O `CaptureMonitor` executa a varredura a cada `LIVECLIPPER_CAPTURE_POLL_INTERVAL_SECONDS`.
4. O `SourceAdapter` lista arquivos cuja extensão está na allowlist.
5. O scanner descarta arquivos vazios, arquivos ainda em escrita e caminhos já registrados.
6. Um arquivo estável vira um `Recording` com `status=ready`.
7. A API expõe o catálogo em `/api/v1/recordings`.

A deduplicação usa `UNIQUE(path)`. O scanner não conhece OBS nem filesystem concreto: ele recebe `RecordingCandidate` com `path`, `size_bytes` e `modified_at`.

O mecanismo atual é orientado a arquivos estáveis. A captura segmentada e o processamento contínuo são a Fase 2 do roadmap e **não** estão implementados.

## 4. Modelo temporal

### 4.1 Limitação de `recordings`

`recordings` é orientado a arquivo:

- não relaciona dois arquivos da mesma transmissão;
- `modified_at` não é o início da transmissão;
- não há duração nem deslocamento relativo;
- um acontecimento pode atravessar vários arquivos;
- os tempos de um candidato não podem ser calculados apenas com `recordings`.

Conclusão: `recordings` não é suficiente como referência temporal. É necessária uma sessão de captura.

### 4.2 `capture_sessions` (proposta)

Representa uma transmissão contínua e é a **referência temporal oficial**.

| Campo | Uso |
| --- | --- |
| `id` | Chave primária. |
| `source_id` | FK para `capture_sources.id`, `ON DELETE CASCADE`. |
| `started_at` | Instante zero da linha do tempo. |
| `ended_at` | Fim da transmissão; nulo enquanto ativa. |
| `status` | `active`, `closed` ou `failed`. |
| `created_at` | Auditoria. |

Restrições e índices:

- `ended_at` é nulo ou maior/igual a `started_at`.
- Índice `(source_id, started_at)`.
- Várias sessões podem existir para a mesma fonte ao longo do tempo.
- Reinícios, quedas e lacunas relevantes podem abrir uma nova sessão.
- Sem OBS WebSocket, a sessão pode ser inferida pela ordem e proximidade dos arquivos; o `started_at` é aproximado.

### 4.3 Evolução de `recordings`

Todos os campos existentes são preservados. Adicionar, quando necessário:

| Campo novo | Uso |
| --- | --- |
| `session_id` | FK para `capture_sessions.id`, `ON DELETE SET NULL`, anulável para dados legados. |
| `duration_seconds` | Duração do arquivo, obtida por FFprobe. |
| `start_offset_seconds` | Segundo da sessão em que aquele arquivo começa. |

- `start_offset_seconds` ordena os segmentos; não é necessário um campo separado de índice.
- Índice `(session_id, start_offset_seconds)`.
- Registros legados permanecem válidos com `session_id` nulo.
- Nenhuma coluna existente é removida ou renomeada.

### 4.4 `clip_candidates` (proposta)

| Campo | Uso |
| --- | --- |
| `id` | Chave primária. |
| `session_id` | FK para `capture_sessions.id`, `ON DELETE CASCADE`. |
| `start_seconds` | Início relativo ao início da sessão. |
| `end_seconds` | Fim relativo ao início da sessão. |
| `description` | Descrição simples do acontecimento. |
| `score` | Pontuação interna entre 0 e 1. |
| `created_at` | Data de criação. |

Restrições e índices:

- `CHECK (start_seconds >= 0)`.
- `CHECK (end_seconds > start_seconds)`.
- `CHECK (score >= 0 AND score <= 1)`.
- Índice `(session_id, start_seconds)`.
- **Sem `recording_id` obrigatório:** o acontecimento pode atravessar vários segmentos. A sessão é a referência temporal principal.
- `source_id` não é necessário no candidato; é obtido pela sessão.
- A saída para o operador contém apenas início, fim e descrição.

### 4.5 Migração não destrutiva

A correção atual não altera o banco. A evolução será aditiva:

- novas tabelas são criadas sem afetar as existentes;
- `recordings.session_id` exige migração real com Alembic;
- nenhuma coluna existente é removida ou renomeada;
- dados legados podem permanecer com `session_id` nulo;
- backfill é opcional e não deve inventar precisão temporal.

## 5. Processamento contínuo e detecção

### 5.1 Sequência do MVP

1. Receber segmentos do OBS.
2. Extrair áudio com FFmpeg.
3. Analisar intensidade e variações sonoras.
4. Transcrever fala com Faster-Whisper.
5. Identificar acontecimentos interessantes.
6. Delimitar início e fim.
7. Gerar descrição.
8. Salvar candidatos no SQLite.

Nenhuma dessas etapas está implementada nesta tarefa.

### 5.2 Extração de áudio

- FFprobe valida duração, codecs e faixa de áudio.
- FFmpeg extrai PCM mono 16 kHz em janelas configuráveis.
- A invocação usa lista de argumentos, sem shell, com timeout e caminhos catalogados.
- O offset do arquivo (`start_offset_seconds`) é somado ao timestamp local para produzir o tempo oficial da sessão.

### 5.3 Análise sonora

A análise mede energia e variações de intensidade para localizar falas exaltadas, risadas, gritos, pausas e transições. O detector de picos será implementado na fase própria, com:

- janela de análise e suavização;
- limiar relativo ao ruído de fundo;
- duração mínima e máxima;
- fusão de eventos próximos;
- calibração do score.

### 5.4 Transcrição

- Faster-Whisper será dependência opcional da fase de transcrição.
- O modelo é carregado de forma preguiçosa e configurável.
- A transcrição fornece texto e timestamps.
- Timestamps locais são convertidos para o tempo da sessão.
- Em CI, usa-se um duplo de teste; o modelo não é baixado automaticamente.

### 5.5 Identificação, delimitação e descrição

A combinação de energia, variações sonoras e transcrição produz evidências. O sistema deverá:

- identificar acontecimentos interessantes;
- delimitar `start_seconds` e `end_seconds` relativos à sessão;
- evitar candidatos sobrepostos ou curtos demais;
- gerar descrição simples e objetiva;
- calcular `score` interno para ordenação.

### 5.6 Chat opcional

O chat do YouTube poderá ser integrado futuramente como fonte complementar, por acesso oficial e autorizado. Ele não é obrigatório, não substitui áudio/transcrição e não deve ser obtido por scraping ou contorno de restrições.

### 5.7 Análise visual opcional

O vídeo é ingerido e catalogado, mas a análise visual **não é obrigatória**. O MVP prioriza áudio e transcrição. OpenCV não faz parte do escopo atual e não deve ser adicionado sem justificativa e fase própria.

## 6. Processamento contínuo por segmentos

O objetivo é registrar candidatos enquanto a transmissão acontece. A fundação atual espera o arquivo ficar estável (`settle`). A evolução planejada:

1. OBS grava segmentos curtos.
2. O monitor registra cada segmento estabilizado.
3. O segmento entra em uma fila de análise.
4. FFmpeg/FFprobe extraem áudio e metadados.
5. A análise e a transcrição geram evidências.
6. Os tempos são convertidos para a sessão.
7. Candidatos são persistidos sem esperar o fim da transmissão.

A latência será a soma do `settle`, da extração e da análise. **Não há captura segmentada, buffer circular ou análise frame a frame nesta tarefa.**

## 7. Persistência e consulta

- `clip_candidates` será persistido no SQLite.
- A consulta será exposta por FastAPI.
- A resposta terá apenas `start_seconds`, `end_seconds` e `description`.
- `id` e `score` permanecem internos.
- Nenhuma rota de edição, legenda ou publicação será adicionada.
- Os endpoints existentes de fontes, gravações, captura, OBS e health são preservados.

## 8. Concorrência e ciclo de vida

- O FastAPI usa `lifespan` para criar engine, tabelas, sessões e iniciar o monitor.
- O monitor roda no event loop; a varredura síncrona usa `asyncio.to_thread`.
- Um `asyncio.Lock` impede varreduras simultâneas.
- Cada requisição HTTP recebe uma sessão própria, com rollback em exceção.
- SQLite usa `check_same_thread=False`, `foreign_keys=ON` e `busy_timeout=5000`.
- No shutdown, o monitor é parado e o engine descartado.
- A futura detecção deve rodar em worker separado para não bloquear a ingestão.

## 9. Segurança operacional

A API atual não possui autenticação e pressupõe execução local/confiável. O bind padrão é `127.0.0.1`. Antes de expor remotamente, adicione autenticação, TLS e controle de acesso.

O adaptador local ignora symlinks para fora do diretório autorizado. O sistema não baixa transmissões, não acessa fontes protegidas e não publica conteúdo.

Cuidados futuros:

- invocar FFmpeg/FFprobe sem shell;
- limitar tempo e tamanho de saída;
- não registrar transcrições completas em logs;
- tratar descrições e transcrições como dados privados;
- não aceitar caminhos arbitrários fornecidos pela API.

Consulte [`SECURITY.md`](SECURITY.md).

## 10. Decisões e limites

| Decisão | Motivo | Limite |
| --- | --- | --- |
| Ler arquivos do OBS | Simples e robusto | Requer gravação local |
| Polling em vez de inotify | Portátil e previsível | Latência de até um intervalo |
| Heurística por `mtime` | Sem dependências externas | Arquivo pausado pode parecer estável |
| Sessão como referência temporal | Preserva continuidade entre arquivos | Exatidão depende do WebSocket ou de inferência |
| Tempos relativos à sessão | Não quebram quando o OBS divide arquivos | Sessão aproximada gera timestamps aproximados |
| Sem `recording_id` obrigatório | Um evento pode atravessar segmentos | Rastreio do arquivo é metadado opcional |
| Áudio e transcrição primeiro | MVP simples e útil | Análise visual não é obrigatória |
| Sem edição/publicação | O produto entrega candidatos | Nenhum vídeo é gerado ou enviado |

### 10.1 Fora do escopo — permanente

Não são fases futuras e não devem receber código, rota, dependência ou stub:

- editor de vídeo;
- recorte físico ou renderização;
- Shorts e conversão vertical 9:16;
- legendas;
- publicação no YouTube ou em qualquer plataforma;
- OAuth, upload e agendamento;
- interface gráfica.

Nesta tarefa também não entram detector, captura segmentada, transcrição, tabelas, migrações ou rotas de candidatos.

## 11. Roadmap resumido

| Fase | Tema | Estado |
| --- | --- | --- |
| 1 | Fundação e catálogo de gravações | Concluída |
| 2 | Sessões, segmentos e processamento contínuo | Planejada |
| 3 | Análise de áudio e transcrição | Planejada |
| 4 | Identificação de momentos, delimitação e descrição | Planejada |
| 5 | Persistência, API de consulta e validação do resultado | Planejada |

Detalhes em [`roadmap.md`](roadmap.md).

## 12. Documentos relacionados

- [`README.md`](../README.md) — visão geral e escopo.
- [`PROJECT_SPEC.md`](PROJECT_SPEC.md) — especificação funcional.
- [`roadmap.md`](roadmap.md) — fases 1 a 5.
- [`SECURITY.md`](SECURITY.md) — segurança e autorização.
- [`obs-setup.md`](obs-setup.md) — configuração do OBS.
- [`obs-websocket.md`](obs-websocket.md) — integração futura.
- [`recordings-monitoring.md`](recordings-monitoring.md) — monitoramento da pasta.

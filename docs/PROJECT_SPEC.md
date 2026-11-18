# Especificação do Projeto — LiveClipper

> **Status:** Fase 1 concluída. Esta é uma correção documental e arquitetural da revisão de escopo 2.0. O detector, a captura segmentada, as tabelas novas e as migrações **não** foram implementados.
>
> **Versão da aplicação:** `0.1.0` · **Python:** 3.12+ · **API:** FastAPI · **Banco:** SQLite + SQLAlchemy 2.x

## 1. Resumo

O LiveClipper é um sistema de **detecção de momentos interessantes em transmissões ao vivo autorizadas**. O OBS Studio é a fonte de captura: ele grava o áudio e o vídeo da transmissão em arquivos locais, e o LiveClipper cataloga esses arquivos, organiza a linha do tempo e identifica os momentos que merecem revisão.

O resultado é uma tabela contendo exclusivamente:

| Campo | Significado |
| --- | --- |
| **Início do corte** | Início do momento candidato, em segundos desde o início da sessão. |
| **Fim do corte** | Fim do momento candidato, em segundos desde o início da sessão. |
| **Descrição simples** | Texto curto que explica o acontecimento. |

O produto **não** edita vídeos, não recorta arquivos, não gera Shorts, não converte para 9:16, não adiciona legendas e não publica no YouTube. A decisão de cortar, publicar ou reutilizar o trecho é humana e externa ao LiveClipper.

## 2. Objetivo e escopo

### 2.1 Dentro do escopo

- OBS Studio como fonte oficial de captura autorizada.
- API FastAPI e persistência SQLite + SQLAlchemy já existentes.
- Cadastro de fontes autorizadas com referência de autorização.
- Monitoramento das gravações produzidas pelo OBS.
- Organização das gravações em sessões de captura contínuas.
- Processamento contínuo por segmentos.
- Extração de áudio com FFmpeg.
- Análise de intensidade e variações sonoras.
- Transcrição de fala com Faster-Whisper.
- Identificação de acontecimentos interessantes.
- Delimitação temporal do início e do fim de cada candidato.
- Geração de descrição simples.
- Persistência e consulta dos candidatos no SQLite.

### 2.2 Fora do escopo — permanente

Estes itens **não são fases futuras** e não devem ser implementados:

| Item | Situação |
| --- | --- |
| Editor de vídeo | Fora do projeto. |
| Recorte físico ou renderização | Fora do projeto. |
| Shorts e conversão vertical 9:16 | Fora do projeto. |
| Legendas, queima ou sincronização de texto | Fora do projeto. |
| Publicação no YouTube ou em qualquer plataforma | Fora do projeto. |
| OAuth, upload e agendamento | Fora do projeto. |
| Interface gráfica | Fora do projeto; a interface é a API HTTP. |
| Download de transmissões, URLs internas ou DRM | Fora do projeto. |

### 2.3 Fora desta entrega

- Implementação do detector de momentos.
- Implementação da captura segmentada.
- Implementação da transcrição.
- Criação das tabelas `capture_sessions` e `clip_candidates`.
- Migrações Alembic.
- Rotas de candidatos.
- Novas dependências.

**Limite de implementação:** esta tarefa altera apenas documentação e a descrição arquitetural. Nenhum modelo, endpoint, banco, dependência ou comportamento existente é alterado.

## 3. Uso responsável e autorização

O projeto parte do princípio de que o operador possui **autorização explícita do criador** para capturar, analisar e reutilizar o conteúdo.

- O cadastro de uma fonte exige `authorization_reference` e `authorization_confirmed: true`.
- A varredura revalida a referência e a data de autorização antes de ingerir arquivos.
- O operador deve arquivar a evidência (contrato, e-mail, termo), limitar a captura ao período e conteúdo autorizados e remover dados quando a autorização expirar.
- A análise gera apenas candidatos; nenhum conteúdo é publicado ou redistribuído pelo sistema.
- O sistema registra a autorização; não decide se o uso é lícito nem substitui análise jurídica.
- É proibido burlar termos de plataforma, DRM, restrições de acesso ou direitos de terceiros.

## 4. Arquitetura

### 4.1 Visão geral

```text
Navegador (conteúdo autorizado)
   │ janela + áudio
   ▼
OBS Studio
   │ grava segmentos .mkv/.mp4/.mov/.flv/.ts
   ▼
app.sources ── SourceAdapter / cadastro autorizado
   │ candidatos: caminho, tamanho, mtime
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
   │      ├── análise de áudio
   │      ├── Faster-Whisper
   │      └── candidatos
   │
   └── app.api (FastAPI)
          ├── endpoints existentes
          └── [planejado] consulta de candidatos
```

### 4.2 Componentes

| Pacote | Responsabilidade |
| --- | --- |
| `app.config` | Configuração central por ambiente e `.env` com Pydantic Settings. |
| `app.database` | Base declarativa, sessão, modelos, `create_all` e repositórios SQLAlchemy. |
| `app.sources` | Cadastro autorizado, contrato `SourceAdapter` e adaptador de diretório local. |
| `app.capture` | Varredura, estabilidade, deduplicação, monitor periódico e schemas. |
| `app.obs` | Diagnóstico local do OBS e contrato futuro `ObsClient`. |
| `app.detection` | Núcleo planejado: sessões, áudio, transcrição, delimitação e candidatos. Nesta revisão, apenas documentação. |
| `app.api` | Rotas, dependências, schemas HTTP e tratamento de erros. |
| `app.clipping` | Fora do escopo; vazio, sem código executável. |
| `app.publishing` | Fora do escopo; vazio, sem código executável. |

### 4.3 Ingestão atual

1. O OBS grava a janela autorizada e o áudio no diretório configurado.
2. Uma fonte autorizada é cadastrada via `POST /api/v1/sources`.
3. O `CaptureMonitor` varre as fontes a cada `LIVECLIPPER_CAPTURE_POLL_INTERVAL_SECONDS`.
4. O `SourceAdapter` lista arquivos com extensão permitida.
5. O scanner descarta arquivos vazios, arquivos em escrita e caminhos já registrados.
6. Um arquivo estável vira um `Recording` com `status=ready`.
7. A API expõe o catálogo em `/api/v1/recordings`.

O mecanismo atual é orientado a arquivos estáveis. A captura segmentada e o processamento contínuo pertencem à Fase 2 do roadmap e **não** são implementados agora.

### 4.4 Abstração da origem

A origem é isolada pelo contrato `SourceAdapter`:

```python
class SourceAdapter(ABC):
    source_id: int
    name: str

    @abstractmethod
    def availability_error(self) -> str | None: ...

    @abstractmethod
    def scan(self) -> Iterable[RecordingCandidate]: ...
```

O scanner não conhece OBS, filesystem ou detalhes concretos; recebe candidatos com `path`, `size_bytes` e `modified_at`. O adaptador ativo é escolhido por `LIVECLIPPER_SOURCE_ADAPTER` e resolvido em `app/sources/factory.py`.

## 5. Processamento futuro

### 5.1 Sequência do MVP

A sequência planejada, priorizando áudio e transcrição, é:

1. **Receber segmentos do OBS.**
2. **Extrair áudio com FFmpeg.**
3. **Analisar intensidade e variações sonoras.**
4. **Transcrever fala com Faster-Whisper.**
5. **Identificar acontecimentos interessantes.**
6. **Delimitar início e fim.**
7. **Gerar descrição.**
8. **Salvar candidatos no SQLite.**

Nenhuma dessas etapas está implementada nesta tarefa.

### 5.2 Extração de áudio com FFmpeg

- FFmpeg e FFprobe são binários externos, não dependências Python desta etapa.
- FFprobe valida duração, codecs e faixa de áudio.
- FFmpeg extrai áudio mono em PCM 16 kHz, em janelas configuráveis.
- A chamada usa lista de argumentos, sem `shell=True`, com timeout e caminhos catalogados.
- O offset do arquivo dentro da sessão é somado ao timestamp local para produzir o tempo oficial do candidato.

### 5.3 Análise de intensidade e variações sonoras

A análise inicial mede energia e mudanças de intensidade para localizar falas exaltadas, risadas, gritos, pausas e transições relevantes. O detector de picos não faz parte desta tarefa; a fase futura definirá:

- janela de análise e suavização;
- limiar relativo ao ruído de fundo;
- duração mínima e máxima de um candidato;
- fusão de eventos próximos;
- calibração do score.

### 5.4 Transcrição com Faster-Whisper

- Faster-Whisper será dependência opcional da fase de transcrição.
- O modelo será carregado de forma preguiçosa e configurável.
- A transcrição fornece texto e timestamps.
- Timestamps locais são convertidos para o tempo relativo à sessão.
- O modelo não deve ser baixado automaticamente em CI; testes usarão um duplo de teste.
- A transcrição ajuda a identificar acontecimentos e a gerar descrições simples.

### 5.5 Identificação, delimitação e descrição

A combinação de energia, variações sonoras e transcrição produz evidências. A partir delas, o sistema deverá:

- identificar acontecimentos interessantes;
- delimitar `start_seconds` e `end_seconds` relativos à sessão;
- evitar candidatos sobrepostos ou curtos demais;
- gerar uma descrição simples e objetiva;
- calcular um score interno para ordenação.

A saída para o operador continua sendo apenas início, fim e descrição.

### 5.6 Chat como fonte complementar opcional

O chat do YouTube poderá ser integrado futuramente como fonte complementar, sempre por acesso oficial e autorizado. O chat:

- não é obrigatório para o MVP;
- não substitui áudio e transcrição;
- não deve ser obtido por scraping ou contorno de restrições;
- pode ajudar a pontuar ou descrever acontecimentos quando disponível.

### 5.7 Análise visual opcional

O vídeo é ingerido e catalogado, mas a análise visual **não é obrigatória**. O MVP prioriza áudio e transcrição. OpenCV não faz parte do escopo atual e não deve ser adicionado sem justificativa e sem uma fase própria.

### 5.8 Persistência e consulta

Os candidatos serão persistidos em `clip_candidates` e consultados pela API. A saída terá apenas:

```json
{
  "items": [
    {
      "start_seconds": 123.4,
      "end_seconds": 158.9,
      "description": "Reação intensa do apresentador após uma jogada decisiva."
    }
  ]
}
```

`score` e `id` são internos. Nenhuma rota de edição, legenda ou publicação será adicionada.

## 6. Configuração

### 6.1 Configuração atual

Todas as variáveis usam o prefixo `LIVECLIPPER_` e podem vir do ambiente ou de `.env`.

| Variável | Padrão | Uso |
| --- | --- | --- |
| `LIVECLIPPER_APP_NAME` | `LiveClipper` | Nome no OpenAPI. |
| `LIVECLIPPER_ENVIRONMENT` | `development` | Ambiente lógico. |
| `LIVECLIPPER_LOG_LEVEL` | `INFO` | Nível de log. |
| `LIVECLIPPER_API_PREFIX` | `/api/v1` | Prefixo das rotas. |
| `LIVECLIPPER_DATA_DIR` | `./data` | Dados locais. |
| `LIVECLIPPER_OUTPUT_DIR` | `./output` | Artefatos de análise futuros; não contém vídeos editados. |
| `LIVECLIPPER_DATABASE_URL` | `sqlite:///./data/liveclipper.db` | URL SQLAlchemy. |
| `LIVECLIPPER_OBS_RECORDINGS_DIR` | vazio | Diretório global de gravações do OBS. |
| `LIVECLIPPER_OBS_WEBSOCKET_URL` | `ws://127.0.0.1:4455` | Reservada; não usada atualmente. |
| `LIVECLIPPER_OBS_WEBSOCKET_PASSWORD` | vazio | `SecretStr`; nunca serializada. |
| `LIVECLIPPER_SOURCE_ADAPTER` | `obs_directory` | Adaptador de origem. |
| `LIVECLIPPER_RECORDING_EXTENSIONS` | `.mkv,.mp4,.mov,.flv,.ts` | Allowlist global. |
| `LIVECLIPPER_CAPTURE_POLL_INTERVAL_SECONDS` | `5` | Intervalo entre varreduras. |
| `LIVECLIPPER_CAPTURE_SETTLE_SECONDS` | `20` | Tempo sem alteração para considerar a gravação encerrada. |
| `LIVECLIPPER_CAPTURE_AUTO_START` | `true` | Inicia o monitor com a aplicação. |

### 6.2 Configuração planejada

As variáveis abaixo são **proposta**. Elas ainda não existem em `app/config.py` e não devem ser tratadas como implementadas.

| Variável proposta | Padrão sugerido | Uso |
| --- | --- | --- |
| `LIVECLIPPER_FFMPEG_BINARY` | `ffmpeg` | Binário FFmpeg. |
| `LIVECLIPPER_FFPROBE_BINARY` | `ffprobe` | Binário FFprobe. |
| `LIVECLIPPER_AUDIO_SAMPLE_RATE` | `16000` | Taxa de amostragem. |
| `LIVECLIPPER_AUDIO_CHANNELS` | `1` | Canais extraídos. |
| `LIVECLIPPER_DETECTION_CHUNK_SECONDS` | `30` | Janela de análise. |
| `LIVECLIPPER_CANDIDATE_MIN_SECONDS` | `10` | Duração mínima. |
| `LIVECLIPPER_CANDIDATE_MAX_SECONDS` | `120` | Duração máxima. |
| `LIVECLIPPER_CANDIDATE_SCORE_THRESHOLD` | `0.5` | Score mínimo. |
| `LIVECLIPPER_WHISPER_MODEL` | `small` | Modelo Faster-Whisper. |
| `LIVECLIPPER_WHISPER_DEVICE` | `cpu` | `cpu` ou `cuda`. |
| `LIVECLIPPER_WHISPER_COMPUTE_TYPE` | `int8` | Precisão de cálculo. |
| `LIVECLIPPER_WHISPER_LANGUAGE` | `pt` | Idioma esperado ou `auto`. |

## 7. Banco de dados

O banco padrão é SQLite (`data/liveclipper.db`). O engine habilita `foreign_keys=ON`, `busy_timeout=5000`, `check_same_thread=False` e `pool_pre_ping`. O schema atual é criado com `create_all`.

**Esta tarefa não altera o banco.** As tabelas e colunas abaixo são proposta para as próximas fases.

### 7.1 `capture_sources` (existente)

| Campo | Tipo | Regra |
| --- | --- | --- |
| `id` | inteiro | Chave primária. |
| `name` | texto(160) | Único, indexado. |
| `platform`, `creator_name` | texto | Rastreabilidade. |
| `authorization_reference` | texto(255) | Obrigatório. |
| `authorization_notes` | texto | Opcional. |
| `authorized_at` | UTC | Data do aceite. |
| `watch_directory` | texto(1024) | Diretório observado. |
| `file_extensions` | JSON | Allowlist normalizada. |
| `enabled` | booleano | Habilita a varredura. |
| `created_at`, `updated_at` | UTC | Auditoria. |

### 7.2 `recordings` (existente)

| Campo | Tipo | Regra |
| --- | --- | --- |
| `id` | inteiro | Chave primária. |
| `source_id` | FK | `capture_sources.id`, `ON DELETE CASCADE`, indexado. |
| `path` | texto(2048) | Único; identidade e idempotência. |
| `filename`, `size_bytes`, `modified_at` | — | Metadados do arquivo. |
| `status` | enum | `ready`, `processing`, `completed`, `failed`, `ignored`. |
| `discovered_at`, `ready_at` | UTC | Linha do tempo da ingestão. |
| `error_message` | texto | Diagnóstico. |
| `created_at`, `updated_at` | UTC | Auditoria. |

### 7.3 Por que `recordings` não basta

O modelo atual é orientado a arquivo:

- não relaciona dois arquivos da mesma transmissão;
- `modified_at` não é o início da transmissão;
- não há duração nem deslocamento relativo ao início;
- um acontecimento pode atravessar vários arquivos;
- os tempos de um candidato não podem ser calculados apenas com `recordings`.

**Conclusão:** a sessão (`capture_sessions`) deve ser a referência temporal oficial. `recordings` apenas descreve os arquivos que compõem a sessão.

### 7.4 `capture_sessions` (proposta)

Representa uma transmissão contínua.

| Campo | Tipo | Regra |
| --- | --- | --- |
| `id` | inteiro | Chave primária. |
| `source_id` | FK | `capture_sources.id`, `ON DELETE CASCADE`, indexado, obrigatório. |
| `started_at` | UTC | Instante zero da linha do tempo; obrigatório. |
| `ended_at` | UTC | Fim da transmissão; nulo enquanto ativa. |
| `status` | enum | `active`, `closed`, `failed`. |
| `created_at` | UTC | Data de criação. |

Restrições e índices:

- `ended_at` é nulo ou maior/igual a `started_at`.
- Índice `(source_id, started_at)` para localizar a sessão de uma fonte.
- Várias sessões podem existir para a mesma fonte ao longo do tempo.
- Reinícios, quedas e lacunas relevantes podem abrir uma nova sessão.
- Enquanto não houver OBS WebSocket, a sessão pode ser inferida pela ordem e proximidade dos arquivos; nesse caso, `started_at` é aproximado.

### 7.5 Evolução aditiva de `recordings`

Todos os campos existentes são preservados. Adicionar, quando necessário:

| Campo novo | Tipo | Regra |
| --- | --- | --- |
| `session_id` | FK | `capture_sessions.id`, `ON DELETE SET NULL`, indexado, anulável para dados legados. |
| `duration_seconds` | numérico | Duração obtida por FFprobe; anulável. |
| `start_offset_seconds` | numérico | Segundo da sessão em que o arquivo começa; `>= 0`, anulável. |

- `start_offset_seconds` é a referência para ordenar os segmentos; não é necessário um campo separado de índice.
- Índice `(session_id, start_offset_seconds)`.
- Registros legados permanecem válidos com `session_id` nulo.
- Nenhuma coluna existente é removida ou renomeada.

### 7.6 `clip_candidates` (proposta)

| Campo | Tipo | Regra |
| --- | --- | --- |
| `id` | inteiro | Chave primária. |
| `session_id` | FK | `capture_sessions.id`, `ON DELETE CASCADE`, indexado, obrigatório. |
| `start_seconds` | numérico | Início relativo à sessão; `>= 0`. |
| `end_seconds` | numérico | Fim relativo à sessão; `> start_seconds`. |
| `description` | texto | Descrição simples do acontecimento; obrigatório. |
| `score` | numérico | Pontuação interna entre `0` e `1`; obrigatório. |
| `created_at` | UTC | Data de criação. |

Restrições e índices:

- `CHECK (end_seconds > start_seconds)`.
- `CHECK (start_seconds >= 0)`.
- `CHECK (score >= 0 AND score <= 1)`.
- Índice `(session_id, start_seconds)` para consultar candidatos por sessão e ordenar por tempo.
- `session_id` é a referência temporal oficial.
- **Não há `recording_id` obrigatório**: o acontecimento pode atravessar vários segmentos. Se no futuro for necessário rastrear o arquivo de origem, isso pode ser um metadado opcional, nunca a referência temporal principal.
- `source_id` não é necessário no candidato; ele é obtido pela sessão.
- `id` e `score` são internos; a tabela apresentada ao operador contém apenas início, fim e descrição.

### 7.7 Migração não destrutiva

- A criação de novas tabelas é aditiva.
- A coluna `recordings.session_id` exige migração real com Alembic, pois `create_all` não altera tabelas existentes.
- Não haverá `DROP TABLE`, `DROP COLUMN` ou renomeação incompatível.
- Dados legados podem ficar com `session_id` nulo; uma backfill opcional pode criar sessões sintéticas sem inventar precisão temporal.

## 8. API HTTP

A API é servida por padrão em `127.0.0.1:8000`. OpenAPI em `/docs`.

### 8.1 Endpoints existentes (preservados)

| Método | Caminho | Descrição |
| --- | --- | --- |
| `GET` | `/` | Identificação da aplicação/fase. |
| `GET` | `/health` | Banco + estado do monitor. |
| `GET` | `/api/v1/obs/status` | Diagnóstico do OBS, sem abrir WebSocket. |
| `POST` | `/api/v1/sources` | Cadastra fonte autorizada. |
| `GET` | `/api/v1/sources` | Lista fontes. |
| `GET` | `/api/v1/sources/{id}` | Detalha fonte. |
| `POST` | `/api/v1/capture/scan` | Varredura manual. |
| `GET` | `/api/v1/capture/status` | Estado do monitor. |
| `GET` | `/api/v1/recordings` | Lista gravações. |
| `GET` | `/api/v1/recordings/{id}` | Detalha gravação. |

Nenhum endpoint foi removido ou alterado nesta tarefa.

### 8.2 Endpoints planejados (não implementados)

| Método | Caminho | Descrição |
| --- | --- | --- |
| `GET` | `/api/v1/clip-candidates` | Lista início, fim e descrição dos candidatos. |
| `GET` | `/api/v1/detection/status` | Estado da análise de áudio/transcrição. |

A resposta de candidatos expõe apenas início, fim e descrição. Filtros por `session_id` e período podem existir, mas não alteram as colunas da tabela.

## 9. Captura, segmentação e latência

O objetivo é acompanhar a transmissão e registrar candidatos enquanto ela acontece. A fundação atual só registra arquivos depois que ficam estáveis (`settle`). A evolução planejada é:

1. configurar o OBS para gravar em segmentos curtos;
2. registrar cada segmento ao estabilizar;
3. enfileirar o segmento para extração e análise;
4. converter timestamps locais para o tempo da sessão;
5. persistir candidatos sem esperar o fim da transmissão.

A latência será a soma do `settle`, da extração de áudio e da análise. **A captura segmentada não é implementada nesta tarefa**, e não há buffer circular nem análise frame a frame.

## 10. Fases do projeto

| Fase | Tema | Estado |
| --- | --- | --- |
| 1 | Fundação e catálogo de gravações | Concluída |
| 2 | Sessões, segmentos e processamento contínuo | Planejada |
| 3 | Análise de áudio e transcrição | Planejada |
| 4 | Identificação de momentos, delimitação e descrição | Planejada |
| 5 | Persistência, API de consulta e validação do resultado | Planejada |

O detalhamento está em [`roadmap.md`](roadmap.md).

## 11. Qualidade e testes

- `pytest` usa banco SQLite temporário, diretórios temporários e monitor em background desligado.
- Os testes existentes cobrem health, cadastro autorizado, validação de diretório, ingestão, estabilidade, deduplicação, monitor, diagnóstico do OBS e registro de adaptadores.
- Esta correção documental não altera o comportamento testado.
- Comandos:

```bash
pytest
pytest --cov=app
```

Testes planejados para as próximas fases:

- sessão criada e reutilizada para segmentos contínuos;
- recusa de candidato com `end_seconds <= start_seconds`;
- tempos relativos à sessão, não ao arquivo;
- extração de áudio com FFmpeg usando lista de argumentos;
- transcrição com modelo falso em CI;
- falha de FFmpeg/FFprobe sem derrubar o monitor;
- resposta da API contendo apenas início, fim e descrição.

## 12. Segurança operacional

- A API não possui autenticação e pressupõe execução local/confiável.
- O servidor deve escutar em `127.0.0.1` ou em rede confiável; para exposição remota, use autenticação, TLS e controle de acesso.
- Nenhuma credencial é armazenada no código; segredos vêm do `.env` e a senha do OBS usa `SecretStr`.
- A senha do OBS WebSocket nunca é retornada pela API.
- O projeto lê apenas arquivos locais; não baixa transmissões nem acessa URLs internas de plataformas.
- Symlinks para fora do diretório autorizado são ignorados.
- FFmpeg/FFprobe serão invocados sem shell, com timeout e apenas sobre caminhos catalogados.
- Transcrições e descrições são dados privados; trate banco e logs com cuidado.
- Não existe publicação automática, OAuth ou upload.

A política completa está em [`SECURITY.md`](SECURITY.md).

## 13. Decisões e limites

| Decisão | Motivo | Limite |
| --- | --- | --- |
| OBS como origem oficial | Captura autorizada e controle do operador | Requer OBS configurado localmente |
| Polling em vez de inotify | Portátil e previsível | Latência de até um intervalo |
| Estabilidade por `mtime` | Simples e sem dependências externas | Arquivo pausado pode parecer estável |
| Deduplicação por caminho | Idempotência | Mesmo conteúdo em dois caminhos gera dois registros |
| SQLite | Simplicidade local | Avaliar PostgreSQL para múltiplos workers |
| `create_all` no schema atual | Schema pequeno | Evolução de colunas exige Alembic |
| Sessão como referência temporal | Preserva continuidade entre arquivos | Exatidão depende do WebSocket ou de inferência |
| Tempos relativos à sessão | Não quebram quando o OBS divide arquivos | Sessão aproximada gera timestamps aproximados |
| Sem `recording_id` obrigatório | Um evento pode atravessar segmentos | Rastreio do arquivo é metadado opcional |
| Áudio e transcrição primeiro | MVP simples e útil | Análise visual não é obrigatória |
| Sem edição/publicação | O produto entrega candidatos | Nenhum vídeo é gerado ou enviado |

## 14. Critérios de aceite desta correção

- [x] Quatro documentos consistentes: README, PROJECT_SPEC, architecture e roadmap.
- [x] OBS descrito como fonte de captura.
- [x] FastAPI, SQLite, fontes autorizadas e monitoramento preservados.
- [x] Processamento contínuo por segmentos descrito.
- [x] Extração de áudio, análise sonora, transcrição, identificação, delimitação e descrição descritas.
- [x] Persistência e consulta dos candidatos descritas.
- [x] `capture_sessions` com `id`, `source_id`, `started_at`, `ended_at`, `status` e `created_at`.
- [x] `recordings` preservado e complementado com `session_id`, `duration_seconds` e `start_offset_seconds`.
- [x] `clip_candidates` com `id`, `session_id`, `start_seconds`, `end_seconds`, `description`, `score` e `created_at`.
- [x] Sessão definida como referência temporal oficial; `recording_id` não é obrigatório.
- [x] FKs, índices e restrições avaliados.
- [x] Nenhuma tabela, modelo, endpoint ou dependência alterado.
- [x] Nenhum detector ou captura segmentada implementado.
- [x] Referências a clipping, Shorts, legendas e publicação aparecem apenas como exclusões.
- [x] Testes existentes executados.

## 15. Documentos relacionados

- [`README.md`](../README.md) — visão geral, instalação e uso.
- [`architecture.md`](architecture.md) — decisões técnicas e modelo temporal.
- [`roadmap.md`](roadmap.md) — fases 1 a 5.
- [`SECURITY.md`](SECURITY.md) — segurança e autorização.
- [`obs-setup.md`](obs-setup.md) — configuração do OBS.
- [`obs-websocket.md`](obs-websocket.md) — integração futura não implementada.
- [`recordings-monitoring.md`](recordings-monitoring.md) — monitoramento da pasta.

# Especificação do Projeto — LiveClipper

> **Status:** Fase 1 concluída e revisão de escopo 2.0 aplicada. O detector ainda **não** foi implementado.
>
> **Versão da aplicação:** `0.1.0` · **Python:** 3.12+ · **API:** FastAPI · **Banco:** SQLite + SQLAlchemy 2.x

## 1. Resumo

O LiveClipper é um sistema de **detecção de momentos interessantes em transmissões ao vivo autorizadas**. O OBS Studio captura o áudio e o vídeo da transmissão em arquivos locais; o LiveClipper cataloga essas gravações, analisa o conteúdo e registra os momentos que poderiam virar bons clipes.

O resultado é uma tabela contendo exclusivamente:

| Campo | Significado |
| --- | --- |
| **Início do corte** | Início do momento candidato, em segundos desde o início da sessão de captura. |
| **Fim do corte** | Fim do momento candidato, em segundos desde o início da sessão de captura. |
| **Descrição simples do acontecimento** | Texto curto que explica por que o trecho é interessante. |

O sistema **não** edita vídeos, não recorta arquivos, não gera Shorts, não converte para formato vertical, não adiciona legendas e não publica no YouTube. A decisão de cortar, publicar ou reutilizar o trecho é humana e externa ao LiveClipper.

## 2. Objetivo e escopo

### 2.1 Dentro do escopo

- Ambiente Python reproduzível com `pyproject.toml` e dependências de desenvolvimento.
- API FastAPI com `GET /health` verificando banco e monitor de captura.
- Persistência SQLite via SQLAlchemy 2.x.
- Configuração centralizada por variáveis de ambiente e `.env`, validada com Pydantic Settings.
- Cadastro de fontes autorizadas com referência de autorização obrigatória.
- Leitura exclusiva de arquivos locais produzidos pelo OBS.
- Monitor periódico que registra apenas gravações consideradas estáveis.
- Catálogo de gravações consultável por API.
- Contrato de origem de vídeo substituível (`SourceAdapter` + registro de adaptadores).
- Organização das gravações em **sessões de captura** para preservar a continuidade temporal.
- Persistência de **candidatos a clipe** com início, fim, descrição e pontuação interna.
- Análise de áudio com FFmpeg/FFprobe.
- Transcrição com Faster-Whisper.
- Consulta da tabela de candidatos pela API.
- Testes automatizados com Pytest.
- Documentação em português, incluindo OBS, WebSocket futuro e monitoramento futuro.

### 2.2 Fora do escopo — permanente

| Item | Situação |
| --- | --- |
| Edição, recorte ou renderização de vídeo | Fora do projeto. |
| Geração de Shorts ou conversão para 9:16 | Fora do projeto. |
| Legendas, sincronização ou queima de texto | Fora do projeto. |
| Publicação no YouTube ou em qualquer plataforma | Fora do projeto. |
| OAuth 2.0, upload e agendamento de publicação | Fora do projeto. |
| OpenCV e processamento de imagem em tempo real | Fora do projeto; não será adicionado. |
| Download de transmissões, URLs internas, DRM ou bypass de plataforma | Fora do projeto. |
| Interface gráfica | Fora do projeto; a interface é a API HTTP. |
| Autenticação na API | Necessária antes de qualquer exposição remota; não implementada agora. |

### 2.3 Fora desta entrega

- Detector de picos e qualquer análise de áudio executável.
- Transcrição executável.
- Criação das tabelas `capture_sessions` e `clip_candidates`.
- Migrações Alembic.
- Rotas de detecção ou de candidatos.
- Dependências de FFmpeg, Faster-Whisper ou OpenCV no `pyproject.toml`.

**Limite de implementação:** os pacotes `app.detection`, `app.clipping` e `app.publishing` não contêm funções executáveis nesta revisão. `app.detection` é o módulo principal **planejado**; `app.clipping` e `app.publishing` estão fora do escopo e permanecem vazios apenas como marcadores históricos. Não crie funções fictícias, stubs executáveis, rotas ou dependências para preencher módulos; cada fase adiciona código real quando for iniciada.

## 3. Uso responsável e autorização

O projeto parte do princípio de que o operador possui **autorização explícita do criador** para capturar, analisar e reutilizar o conteúdo.

- O cadastro de uma fonte exige `authorization_reference` e `authorization_confirmed: true`.
- A varredura revalida a presença de referência e data de autorização antes de ingerir arquivos.
- O operador deve arquivar a evidência (contrato, e-mail, termo), limitar a captura ao período e conteúdo autorizados e remover dados quando a autorização expirar.
- A análise gera apenas candidatos; nenhum conteúdo é publicado ou redistribuído pelo sistema.
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
   ├── app.detection       → módulo principal planejado
   │      ├── FFprobe/FFmpeg
   │      ├── análise de áudio (futuro)
   │      ├── Faster-Whisper (futuro)
   │      └── candidatos (futuro)
   └── app.api             → FastAPI/REST, health, catálogo e futura tabela
```

| Pacote | Responsabilidade |
| --- | --- |
| `app.config` | `Settings` centralizadas, carregadas de `.env`/ambiente. |
| `app.database` | Base declarativa, tipos UTC, modelos, sessão, `create_all` e repositórios. |
| `app.sources` | Contrato `SourceAdapter`, adaptador de diretório local, registro de adaptadores, cadastro autorizado. |
| `app.capture` | Varredura, regra de estabilidade, deduplicação, monitor periódico e schemas. |
| `app.obs` | Diagnóstico local do OBS e contrato futuro `ObsClient` (WebSocket). |
| `app.detection` | Núcleo funcional planejado: sessões, áudio, transcrição e candidatos. Nesta revisão, apenas documentação. |
| `app.api` | Rotas, dependências, schemas HTTP e mapeamento de erros. |
| `app.clipping` | Fora do escopo. Vazio, sem código executável. |
| `app.publishing` | Fora do escopo. Vazio, sem código executável. |

### 4.2 Fluxo de ingestão atual

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

Adaptadores disponíveis:

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

Depois, defina `LIVECLIPPER_SOURCE_ADAPTER=minha_fonte`. O monitor, o scanner e o futuro detector continuam isolados dos detalhes da origem.

### 4.4 Fluxo planejado de detecção

```text
recordings (status=ready)
   │
   ▼
sessão de captura (capture_sessions)
   │ define o instante zero da linha do tempo
   ▼
FFprobe
   │ valida faixa de áudio, duração e codecs
   ▼
FFmpeg
   │ extrai PCM mono 16 kHz em janelas (ex.: 30 s)
   ▼
análise de energia/picos + Faster-Whisper
   │ produz evidências com timestamps
   ▼
montagem de candidatos
   │ mescla evidências, aplica duração mínima/máxima e score
   ▼
clip_candidates
   │ tempos relativos ao início da sessão
   ▼
GET /api/v1/clip-candidates
   │ início, fim e descrição
   ▼
revisão humana
```

O detector de picos **não** é implementado nesta revisão. O fluxo acima é o desenho que orienta a próxima fase.

## 5. Configuração

Todas as variáveis atuais usam o prefixo `LIVECLIPPER_` e podem vir do ambiente ou de um arquivo `.env` na raiz. O modelo está em `app/config.py`; o exemplo versionado é `.env.example`.

### 5.1 Configuração atual

| Variável | Padrão | Uso |
| --- | --- | --- |
| `LIVECLIPPER_APP_NAME` | `LiveClipper` | Nome exibido no OpenAPI. |
| `LIVECLIPPER_ENVIRONMENT` | `development` | Ambiente lógico (`development`, `test`, `production`). |
| `LIVECLIPPER_LOG_LEVEL` | `INFO` | Nível de log do processo. |
| `LIVECLIPPER_API_PREFIX` | `/api/v1` | Prefixo das rotas versionadas. |
| `LIVECLIPPER_DATA_DIR` | `./data` | Diretório de dados locais. |
| `LIVECLIPPER_OUTPUT_DIR` | `./output` | Diretório de artefatos de análise futuros. Não contém vídeos editados. |
| `LIVECLIPPER_DATABASE_URL` | `sqlite:///./data/liveclipper.db` | URL SQLAlchemy. |
| `LIVECLIPPER_OBS_RECORDINGS_DIR` | vazio | Diretório global de gravações do OBS; pode ser omitido se cada fonte informar `watch_directory`. |
| `LIVECLIPPER_OBS_WEBSOCKET_URL` | `ws://127.0.0.1:4455` | URL reservada para a integração futura. **Não é usada atualmente.** |
| `LIVECLIPPER_OBS_WEBSOCKET_PASSWORD` | vazio | Senha reservada para a integração futura, carregada como `SecretStr`. Nunca é serializada pela API. |
| `LIVECLIPPER_SOURCE_ADAPTER` | `obs_directory` | Adaptador de origem do vídeo. |
| `LIVECLIPPER_RECORDING_EXTENSIONS` | `.mkv,.mp4,.mov,.flv,.ts` | Allowlist global de extensões. |
| `LIVECLIPPER_CAPTURE_POLL_INTERVAL_SECONDS` | `5` | Intervalo entre varreduras. |
| `LIVECLIPPER_CAPTURE_SETTLE_SECONDS` | `20` | Tempo sem alteração para considerar a gravação encerrada. |
| `LIVECLIPPER_CAPTURE_AUTO_START` | `true` | Inicia o monitor junto com a aplicação. |

### 5.2 Configuração planejada para detecção

As variáveis abaixo são **proposta de desenho**. Elas ainda não existem em `app/config.py` e não devem ser usadas como se estivessem implementadas.

| Variável proposta | Padrão sugerido | Uso |
| --- | --- | --- |
| `LIVECLIPPER_FFMPEG_BINARY` | `ffmpeg` | Caminho ou nome do binário FFmpeg. |
| `LIVECLIPPER_FFPROBE_BINARY` | `ffprobe` | Caminho ou nome do binário FFprobe. |
| `LIVECLIPPER_AUDIO_SAMPLE_RATE` | `16000` | Taxa de amostragem para análise e transcrição. |
| `LIVECLIPPER_AUDIO_CHANNELS` | `1` | Canais extraídos (mono). |
| `LIVECLIPPER_DETECTION_CHUNK_SECONDS` | `30` | Tamanho da janela de áudio analisada. |
| `LIVECLIPPER_CANDIDATE_MIN_SECONDS` | `10` | Duração mínima de um candidato. |
| `LIVECLIPPER_CANDIDATE_MAX_SECONDS` | `120` | Duração máxima de um candidato. |
| `LIVECLIPPER_CANDIDATE_SCORE_THRESHOLD` | `0.5` | Score mínimo para persistir/apresentar. |
| `LIVECLIPPER_WHISPER_MODEL` | `small` | Modelo Faster-Whisper. |
| `LIVECLIPPER_WHISPER_DEVICE` | `cpu` | `cpu` ou `cuda`, conforme disponibilidade. |
| `LIVECLIPPER_WHISPER_COMPUTE_TYPE` | `int8` | Precisão de cálculo (ex.: `int8` em CPU). |
| `LIVECLIPPER_WHISPER_LANGUAGE` | `pt` | Idioma esperado; `auto` para detecção automática. |

Diretórios operacionais são criados na inicialização. O `.env` é ignorado pelo Git; apenas `.env.example` é versionado.

## 6. Banco de dados

O banco padrão é SQLite (`data/liveclipper.db`). O engine habilita `foreign_keys=ON`, `busy_timeout=5000`, `check_same_thread=False` e `pool_pre_ping`. O schema atual é criado com `create_all`.

**Esta revisão não altera o banco.** As tabelas abaixo são proposta para a próxima fase e exigem migração não destrutiva.

### 6.1 `capture_sources` (existente)

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

### 6.2 `recordings` (existente)

| Campo | Tipo | Regra |
| --- | --- | --- |
| `id` | inteiro | Chave primária. |
| `source_id` | FK | `ON DELETE CASCADE`, indexado. |
| `path` | texto(2048) | Único; identidade e idempotência. |
| `filename`, `size_bytes`, `modified_at` | — | Metadados do arquivo. |
| `status` | enum | `ready`, `processing`, `completed`, `failed`, `ignored`. |
| `discovered_at`, `ready_at` | UTC | Linha do tempo da ingestão. |
| `error_message` | texto | Diagnóstico. |
| `created_at`, `updated_at` | UTC | Auditoria. |

### 6.3 Análise: `recordings` não basta para relacionar segmentos

O modelo atual é **por arquivo** e não preserva a continuidade temporal de uma transmissão:

- não existe vínculo entre dois arquivos gravados na mesma transmissão;
- `modified_at` é o horário de modificação do arquivo, não o início da sessão;
- não há duração, ordem de segmento ou deslocamento relativo ao início;
- se o OBS dividir a transmissão em vários arquivos, não é possível saber se há continuidade, sobreposição ou lacuna;
- os tempos de um candidato não podem ser calculados de forma confiável apenas com `recordings`.

**Conclusão:** é necessária uma tabela de sessões de captura (`capture_sessions`) para representar uma execução contínua de captura e servir de âncora temporal. Cada `Recording` passa a apontar para uma sessão. Os tempos de `clip_candidates` são relativos ao início da sessão.

### 6.4 `capture_sessions` (proposta, não criada)

| Campo | Tipo | Regra |
| --- | --- | --- |
| `id` | inteiro | Chave primária. |
| `source_id` | FK | `capture_sources.id`, `ON DELETE CASCADE`, indexado, obrigatório. |
| `started_at` | UTC | Instante zero da linha do tempo da sessão. Obrigatório. |
| `ended_at` | UTC | Fim da captura; nulo enquanto ativa. |
| `status` | enum | `active`, `closed`, `incomplete`, `failed`. |
| `external_reference` | texto(255) | Referência opcional do OBS/arquivo inicial. |
| `created_at`, `updated_at` | UTC | Auditoria. |

Regras:

- `ended_at` deve ser nulo ou maior/igual a `started_at`.
- Índice composto por `(source_id, started_at)`.
- Uma sessão representa uma execução contínua. Reinícios, quedas e novas gravações podem abrir uma nova sessão.
- Enquanto não houver integração com o OBS WebSocket, a sessão pode ser **inferida** a partir da ordem e da proximidade temporal dos arquivos; nesse caso, `started_at` é aproximado e deve ser marcado como tal.
- A sessão não substitui a autorização da fonte; ela apenas organiza a linha do tempo.

### 6.5 Evolução de `recordings` (proposta aditiva)

| Campo novo | Tipo | Regra |
| --- | --- | --- |
| `session_id` | FK | `capture_sessions.id`, `ON DELETE SET NULL`, indexado, anulável para dados legados. |
| `segment_index` | inteiro | Ordem do arquivo dentro da sessão; anulável. |
| `start_offset_seconds` | numérico | Início do arquivo relativo ao início da sessão; anulável. |
| `duration_seconds` | numérico | Duração obtida por FFprobe; anulável. |

Nenhuma coluna existente é removida ou alterada de forma incompatível. Registros legados permanecem válidos com `session_id` nulo até uma backfill opcional.

### 6.6 `clip_candidates` (proposta, não criada)

| Campo | Tipo | Regra |
| --- | --- | --- |
| `id` | inteiro | Chave primária. |
| `source_id` | FK | `capture_sources.id`, `ON DELETE CASCADE`, indexado, obrigatório. |
| `session_id` | FK | `capture_sessions.id`, `ON DELETE CASCADE`, indexado, obrigatório. |
| `recording_id` | FK | `recordings.id`, `ON DELETE SET NULL`, indexado, anulável; identifica o arquivo onde o trecho começa. |
| `start_seconds` | numérico | Início relativo ao início da sessão; `>= 0`. |
| `end_seconds` | numérico | Fim relativo ao início da sessão; `> start_seconds`. |
| `description` | texto | Descrição simples do acontecimento. Obrigatório. |
| `score` | numérico | Pontuação interna entre `0` e `1`. |
| `created_at` | UTC | Data de criação. |

Regras e índices:

- `end_seconds > start_seconds`.
- `0 <= score <= 1`.
- Índices por `(source_id, start_seconds)` e `(session_id, start_seconds)`.
- `recording_id` é o arquivo de **início** do candidato. Se o momento atravessar vários arquivos, a sessão preserva a continuidade.
- `session_id` é um acréscimo ao modelo proposto originalmente; sem ele, os tempos relativos à transmissão não teriam uma âncora persistente.
- `score` e `id` são internos. A tabela apresentada ao operador contém apenas início, fim e descrição.

### 6.7 Migração não destrutiva

- A criação de novas tabelas é aditiva.
- A coluna `recordings.session_id` exige migração real (Alembic) porque `create_all` não altera tabelas existentes.
- Não renomear nem remover colunas existentes.
- Dados legados podem ficar com `session_id` nulo; uma backfill opcional pode criar sessões sintéticas sem inventar precisão temporal.
- Nenhum `DROP TABLE`, `DROP COLUMN` ou alteração incompatível faz parte do plano.

## 7. API HTTP

A API é servida por padrão em `127.0.0.1:8000`. OpenAPI em `/docs`.

### 7.1 Endpoints atuais (preservados)

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

### 7.2 Endpoints planejados (não implementados)

| Método | Caminho | Descrição |
| --- | --- | --- |
| `GET` | `/api/v1/clip-candidates` | Lista a tabela de candidatos. |
| `GET` | `/api/v1/detection/status` | Estado da análise de áudio/transcrição. |

Formato de saída planejado para `GET /api/v1/clip-candidates`:

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

A resposta expõe apenas início, fim e descrição. Filtros por `source_id`, `session_id` e período podem existir, mas não alteram as colunas da tabela. Nenhuma rota de edição, legenda ou publicação será adicionada.

## 8. Captura com OBS

O fluxo recomendado é:

1. Abrir no navegador o conteúdo para o qual existe autorização.
2. No OBS, criar uma fonte **Window Capture** (ou **macOS Screen Capture → Window** / **PipeWire** no Linux) apontando para a janela do navegador.
3. Capturar o áudio da aplicação (`Application Audio Capture`) ou da saída do sistema (`Desktop Audio`), conforme o sistema operacional.
4. Ajustar enquadramento, níveis de áudio e faixas de gravação.
5. Gravar em `.mkv` no diretório observado pelo LiveClipper.

Para reduzir a latência da análise, a configuração futura pode gravar em segmentos curtos (por exemplo, 30–60 s). O monitor registra cada segmento estável e o detector o processa em seguida. O sistema atual não implementa buffer circular nem captura ativa.

O passo a passo detalhado, incluindo Windows, Linux, macOS, áudio por aplicativo, faixas múltiplas e solução de problemas, está em [`obs-setup.md`](obs-setup.md).

> A captura é sempre da janela visível e autorizada. Não use o projeto para contornar proteções da plataforma, DRM ou restrições de acesso.

### 8.1 Latência e análise em tempo real

O objetivo é analisar a transmissão enquanto ela acontece, mas a fundação atual só registra um arquivo depois que ele fica estável (`settle`). A estratégia planejada para a detecção é:

1. configurar o OBS para gravar em segmentos curtos (por exemplo, 30–60 s);
2. registrar cada segmento assim que estabilizar;
3. enfileirar o segmento para extração de áudio e análise;
4. converter os timestamps locais para o tempo relativo à sessão;
5. persistir os candidatos sem esperar o fim da transmissão.

A latência será a soma do `settle`, do tempo de extração e do tempo de análise. Não há promessa de análise frame a frame nem de buffer circular nesta revisão. O buffer e a captura ativa pelo OBS continuam fora desta entrega.

## 9. Integração futura com OBS WebSocket

**Não implementada.** Hoje existem apenas:

- as variáveis `LIVECLIPPER_OBS_WEBSOCKET_URL` e `LIVECLIPPER_OBS_WEBSOCKET_PASSWORD`;
- o contrato `ObsClient` em `app/obs/client.py`;
- o diagnóstico `GET /api/v1/obs/status`, que **não abre conexão**.

O WebSocket poderá ser usado futuramente para saber quando uma captura começou/terminou, abrir e fechar sessões com precisão e, opcionalmente, controlar gravação. O desenho, os eventos, os comandos, a reconexão e os cuidados de segurança estão documentados em [`obs-websocket.md`](obs-websocket.md), sem implementação.

## 10. Monitoramento da pasta de gravações

O sistema já implementa **polling** da pasta de gravações: o monitor varre as fontes habilitadas, aplica a regra de estabilidade (`mtime` mais antigo que `now - settle`), ignora arquivos vazios e deduplica por caminho absoluto.

A evolução planejada inclui associar cada gravação a uma sessão, validar metadados com FFprobe e disparar a análise de detecção. Notificação por evento do OBS, `watchdog`/inotify, retenção e limites de armazenamento continuam documentados em [`recordings-monitoring.md`](recordings-monitoring.md).

## 11. Fases do projeto

| Fase | Tema | Estado |
| --- | --- | --- |
| 0 | Estrutura, configuração, banco, health, testes e documentação | Concluída |
| 1 | Ingestão de gravações autorizadas do OBS + catálogo | Concluída |
| 2 | Revisão de escopo 2.0 e preparação documental da detecção | Concluída |
| 3 | Sessões de captura, esquema de candidatos, FFprobe e migração aditiva | Planejada |
| 4 | Análise de áudio, Faster-Whisper, descrição e pontuação de candidatos | Planejada |
| 5 | Operação, calibração, retenção e robustez | Planejada |

O detalhamento está em [`roadmap.md`](roadmap.md).

## 12. Qualidade e testes

- `pytest` usa banco SQLite temporário, diretórios temporários e monitor em background desligado.
- Os testes cobrem health, cadastro autorizado, validação de diretório, ingestão, estabilidade, deduplicação, monitor, diagnóstico do OBS e registro de adaptadores.
- A revisão de escopo não altera o comportamento testado.
- Comandos:

```bash
pytest
pytest --cov=app
```

- Configuração do Pytest em `pyproject.toml` (`testpaths`, `pythonpath`, avisos de depreciação da aplicação).

Testes planejados para a fase de detecção:

- sessão criada e reutilizada para segmentos contínuos;
- recusa de candidato com `end_seconds <= start_seconds`;
- tempos relativos à sessão, não ao arquivo;
- extração de áudio com FFmpeg usando lista de argumentos (sem shell);
- transcrição com modelo falso/stub de teste, sem baixar modelo em CI;
- falha de FFmpeg/FFprobe reportada sem derrubar o monitor;
- resposta da API contendo apenas início, fim e descrição.

## 13. Segurança operacional

- A API não possui autenticação e pressupõe execução local/confiável.
- O servidor deve escutar em `127.0.0.1` ou em rede confiável; para exposição remota, use autenticação, TLS e controle de acesso.
- Nenhuma credencial é armazenada no código; segredos vêm do `.env` e a senha do OBS usa `SecretStr`.
- A senha do OBS WebSocket nunca é retornada pela API.
- O projeto lê apenas arquivos locais; não faz download de transmissões nem acessa URLs internas de plataformas.
- Permissões de leitura são verificadas pelo adaptador local.
- Symlinks que apontam para fora do diretório autorizado são ignorados.
- FFmpeg/FFprobe serão invocados com lista de argumentos, sem shell, com timeout e apenas sobre caminhos catalogados.
- Transcrições e descrições podem conter conteúdo sensível; trate o banco e os logs como dados privados.
- Não existe publicação automática, OAuth ou upload.

A política completa, os controles e o checklist de revisão estão em [`SECURITY.md`](SECURITY.md).

## 14. Decisões e limites

| Decisão | Motivo | Limite |
| --- | --- | --- |
| OBS como origem oficial | Captura autorizada e controle do operador | Requer OBS configurado localmente |
| Polling em vez de inotify | Portátil, previsível e sem dependências | Latência de até um intervalo |
| Estabilidade por `mtime` | Simples e sem dependências externas | Arquivo pausado pode parecer estável; ajuste o settle |
| Deduplicação por caminho | Idempotência | Um mesmo conteúdo em dois caminhos gera dois registros |
| SQLite | Simplicidade local | Avaliar PostgreSQL para múltiplos workers |
| `create_all` no schema atual | Schema inicial pequeno | Evolução de colunas exige Alembic |
| Sessões explícitas | Preservar continuidade entre arquivos | Exatidão depende do OBS WebSocket ou de inferência |
| Tempos relativos à sessão | Estável mesmo com arquivos divididos | Sessão sem `started_at` confiável gera aproximação |
| Sem OpenCV | Não é necessário para detectar áudio/fala | Análise visual avançada fica fora do escopo |
| Detecção antes de edição | O produto entrega candidatos, não vídeos | Nenhum recorte é gerado |
| `app.clipping`/`app.publishing` vazios | Marcadores históricos, sem funcionalidade | Fora do escopo; não recebem código |

## 15. Critérios de aceite da revisão de escopo

- [x] Repositório inteiro inspecionado antes das alterações.
- [x] FastAPI, SQLite, SQLAlchemy, Pydantic Settings, fontes, `SourceAdapter`, monitor, endpoints e testes preservados.
- [x] `app/obs`, `app/capture`, `app/sources` e `app/database` mantidos.
- [x] `app/detection` definido como módulo principal planejado, ainda sem detector.
- [x] `app/clipping` e `app/publishing` marcados como fora do escopo, sem código executável.
- [x] OpenCV explicitamente excluído.
- [x] FFmpeg/FFprobe e Faster-Whisper documentados como preparação futura.
- [x] Tabela `clip_candidates` planejada com início, fim, descrição, score e vínculos.
- [x] Tabela `capture_sessions` proposta para preservar a continuidade temporal.
- [x] Limitação do modelo `recordings` analisada.
- [x] Nenhuma alteração destrutiva no banco.
- [x] Nenhum detector de picos implementado.
- [x] Edição, legendas, publicação e conversão vertical removidas dos objetivos futuros.
- [x] `README.md`, `docs/PROJECT_SPEC.md`, `docs/architecture.md` e `docs/roadmap.md` atualizados.
- [x] Suíte de testes existente verde.

## 16. Documentos relacionados

- [`README.md`](../README.md) — instalação, execução e uso rápido.
- [`architecture.md`](architecture.md) — decisões técnicas e fluxo detalhado.
- [`SECURITY.md`](SECURITY.md) — segurança, autorização e higiene do Git.
- [`obs-setup.md`](obs-setup.md) — configuração do OBS para janela do navegador e áudio.
- [`obs-websocket.md`](obs-websocket.md) — desenho da integração futura, não implementada.
- [`recordings-monitoring.md`](recordings-monitoring.md) — monitoramento atual e evoluções futuras.
- [`roadmap.md`](roadmap.md) — fases do produto.

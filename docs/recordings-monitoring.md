# Monitoramento da pasta de gravações

> **Estado atual:** o monitoramento por polling já está implementado. Este documento registra o comportamento atual e as evoluções futuras planejadas.

## 1. Visão geral

O OBS grava em um diretório local. O LiveClipper não copia, não baixa e não altera o conteúdo: ele **observa** a pasta de cada fonte autorizada e registra arquivos que já terminaram de ser escritos.

```text
OBS grava em ./data/obs (ou diretório por fonte)
        │
        ▼
CaptureMonitor (a cada N segundos)
        │
        ▼
SourceAdapter.scan()  → candidatos (path, tamanho, mtime)
        │
        ▼
scanner: tamanho > 0 · estável · não duplicado
        │
        ▼
recordings (status=ready)
```

## 2. Comportamento atual

### 2.1 Agendamento

- O monitor inicia no `lifespan` do FastAPI quando `LIVECLIPPER_CAPTURE_AUTO_START=true`.
- O intervalo é `LIVECLIPPER_CAPTURE_POLL_INTERVAL_SECONDS` (padrão: 5 s).
- A varredura síncrona roda em `asyncio.to_thread`, sem bloquear o event loop.
- Um `asyncio.Lock` impede duas varreduras simultâneas.
- No shutdown, o monitor é sinalizado, aguardado e o engine é descartado.
- Também é possível disparar uma varredura manual: `POST /api/v1/capture/scan` (opcional `?source_id=`).

### 2.2 Regra de estabilidade

Um arquivo só é registrado quando:

1. a extensão está na allowlist da fonte (ou na global, quando a fonte não informa);
2. o tamanho é maior que zero;
3. `modified_at <= now - LIVECLIPPER_CAPTURE_SETTLE_SECONDS` (padrão: 20 s);
4. o caminho absoluto ainda não existe em `recordings`.

Arquivos vazios são contabilizados como `ignored`; arquivos recentes como `unstable`; caminhos já persistidos como `duplicates`.

### 2.3 Deduplicação e concorrência

- A identidade é o caminho absoluto (`UNIQUE(path)`).
- Se duas varreduras concorrerem, a segunda recebe `IntegrityError` e o scanner contabiliza duplicidade sem quebrar o lote.
- Fontes diferentes apontando para a mesma pasta podem disputar o mesmo caminho: a primeira vence. A recomendação é **uma pasta por fonte**.

### 2.4 Diagnóstico

- `GET /api/v1/capture/status` retorna `running`, intervalo, último scan, último sucesso e último erro.
- `POST /api/v1/capture/scan` retorna, por fonte: `scanned_files`, `registered_total`, `duplicates`, `unstable`, `ignored` e `error`.
- `GET /health` inclui o estado resumido do monitor.

## 3. Limitações conhecidas

| Limitação | Efeito | Mitigação atual/futura |
| --- | --- | --- |
| Polling | Latência de até um intervalo | Reduzir intervalo; futuro evento do OBS |
| Heurística por `mtime` | Arquivo pausado pode parecer estável | Aumentar `settle`; futuro evento de fim de gravação |
| Sem metadados de mídia | Catálogo não sabe duração/codecs | FFprobe na fase de detecção |
| Sem retenção | Pasta cresce indefinidamente | Política de retenção na fase de operação |
| Sem detecção de remoção | Arquivo apagado continua no banco | Reconciliador futuro |
| Sem sessão explícita | Arquivos da mesma captura não são relacionados | `capture_sessions` na fase de detecção |
| Sem remux automático | `.mkv` não é convertido | Desnecessário: o sistema não gera clipes |
| Sem autenticação | API local/confiável apenas | Autenticação antes de exposição remota |

## 4. Evoluções futuras

### 4.1 Notificação por evento (preferencial)

Integrar o OBS WebSocket para reagir a `RecordStateChanged` e disparar a varredura imediatamente. O evento reduz a latência, mas **não substitui** a validação por arquivo. Ver [`obs-websocket.md`](obs-websocket.md).

### 4.2 Observação do filesystem

Adicionar `watchdog` (inotify no Linux, FSEvents no macOS, ReadDirectoryChangesW no Windows) para detectar criação/fechamento de arquivos. Regras:

- eventos são gatilhos; a estabilidade continua sendo validada;
- debounce para ignorar múltiplos eventos do mesmo arquivo;
- fallback para polling quando o observador falhar;
- cuidado com diretórios de rede, onde notificações são inconsistentes.

### 4.3 Metadados e validação de mídia

Na fase de detecção, usar FFprobe para validar e persistir:

- duração, resolução, fps, codecs;
- faixas de áudio e canais;
- taxa de amostragem e possibilidade de extração de áudio;
- checksum/tamanho para detectar arquivo truncado.

Um arquivo só seria marcado como `ready` após validação mínima. Falhas iriam para `failed` com `error_message`.

### 4.4 Retenção e armazenamento

- Definir retenção por dias, tamanho total ou ambos.
- Nunca apagar arquivo com autorização ativa sem confirmação.
- Mover para quarentena antes de remover; registrar auditoria.
- Monitorar espaço livre e pausar a ingestão quando o limite for atingido.
- Política configurável por variáveis de ambiente, com valores seguros por padrão.

### 4.5 Reconcilição do catálogo

- Detectar arquivos removidos/renomeados fora do LiveClipper.
- Marcar como `missing` (novo estado) em vez de apagar o histórico.
- Recalcular tamanho/mtime quando o arquivo mudar.
- Evitar que um mesmo conteúdo remuxado (`.mkv` + `.mp4`) seja contado duas vezes: usar diretório de remux separado ou checksum.

### 4.6 Múltiplas origens

O contrato `SourceAdapter` e o registro em `app/sources/factory.py` permitem adicionar origens sem alterar o monitor. A evolução prevista é persistir o **tipo de adaptador por fonte** (nova coluna + migração Alembic), mantendo `obs_directory` como padrão.

### 4.7 Sessões de captura

O catálogo atual relaciona arquivos, mas não sabe quais pertencem à mesma captura. A fase de detecção introduzirá `capture_sessions`:

- cada sessão tem um `started_at` que serve de instante zero;
- cada `recording` aponta para uma sessão (`session_id`) e recebe `segment_index`, `start_offset_seconds` e `duration_seconds`;
- os tempos de `clip_candidates` são relativos ao início da sessão;
- sem OBS WebSocket, a sessão pode ser inferida pela proximidade temporal e pela duração obtida com FFprobe;
- a migração é aditiva: registros legados permanecem válidos com `session_id` nulo.

Detalhes em [`architecture.md`](architecture.md) e [`PROJECT_SPEC.md`](PROJECT_SPEC.md).

## 5. Configuração recomendada

```env
LIVECLIPPER_OBS_RECORDINGS_DIR=./data/obs
LIVECLIPPER_CAPTURE_POLL_INTERVAL_SECONDS=5
LIVECLIPPER_CAPTURE_SETTLE_SECONDS=20
LIVECLIPPER_CAPTURE_AUTO_START=true
```

- **Gravações grandes:** aumentar `settle` para 30–60 s.
- **Baixa latência:** reduzir polling para 2–5 s e manter `settle` seguro.
- **Muitas fontes:** usar uma pasta por fonte e monitorar o custo de I/O.

## 6. Critérios de aceite futuros

- [ ] Evento de fim de gravação dispara varredura sem depender do intervalo.
- [ ] Arquivo só é `ready` após validação de mídia.
- [ ] Gravações da mesma captura são associadas à mesma sessão.
- [ ] Retenção auditável e reversível.
- [ ] Arquivo removido é reconciliado sem perder histórico.
- [ ] Fallback para polling permanece funcional.
- [ ] Testes cobrem eventos duplicados, fora de ordem, arquivo truncado e falha do observador.

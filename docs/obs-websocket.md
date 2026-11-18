# Integração futura com o OBS WebSocket

> **Estado: não implementada.** Este documento descreve o desenho previsto. Nenhuma conexão WebSocket é aberta atualmente, nenhuma dependência nova foi adicionada e nenhum comando é enviado ao OBS.

## 1. Por que não usar agora

A captura atual ingere arquivos gravados pelo OBS. Para isso, ler o diretório é suficiente, portátil e não exige habilitar servidor, senha ou plugin no OBS. O WebSocket adiciona valor quando for necessário **reagir a eventos** (captura iniciada/parada), **abrir/fechar sessões com precisão** ou **controlar** o OBS (iniciar/parar gravação). Esses casos pertencem a uma fase futura e serão implementados somente depois de estabilizar a ingestão por arquivos.

O que já existe hoje, sem conexão:

- `LIVECLIPPER_OBS_WEBSOCKET_URL` e `LIVECLIPPER_OBS_WEBSOCKET_PASSWORD` em `app/config.py` e `.env.example` (a senha é `SecretStr`);
- o contrato `ObsClient` em `app/obs/client.py`;
- `GET /api/v1/obs/status`, que apenas inspeciona a configuração local e informa `websocket_url`. A senha **nunca** é retornada.

## 2. Objetivos da integração

1. Saber quando uma gravação começou e terminou, sem depender apenas de `mtime`.
2. Consultar o diretório de gravação configurado no OBS e validar a configuração da fonte.
3. Opcionalmente, iniciar e parar gravações de forma controlada, sempre com confirmação do operador.
4. Diagnosticar conexão, versão e estado do OBS pela API.

Não objetivos:

- Substituir a leitura de arquivos. O scanner continua sendo a fonte de verdade do catálogo.
- Baixar transmissões ou acessar conteúdo protegido.
- Controlar cenas, fontes ou áudio sem necessidade aprovada.

## 3. Protocolo e configuração no OBS

- Protocolo previsto: **OBS WebSocket v5** (o mesmo usado pelo OBS Studio 28+).
- Endereço padrão: `ws://127.0.0.1:4455`.
- No OBS: **Ferramentas → Configurações do servidor WebSocket** (ou **Tools → WebSocket Server Settings**):
  1. habilitar o servidor;
  2. manter escuta em `127.0.0.1` quando o OBS e o LiveClipper estiverem na mesma máquina;
  3. definir uma senha forte;
  4. não expor a porta 4455 diretamente na internet.
- Configuração correspondente no `.env`:

```env
LIVECLIPPER_OBS_WEBSOCKET_URL=ws://127.0.0.1:4455
LIVECLIPPER_OBS_WEBSOCKET_PASSWORD=uma-senha-forte
```

Se o OBS usar TLS ou um reverse proxy, usar `wss://`. Em rede separada, restringir por firewall/VPN.

## 4. Autenticação e sessão

O protocolo v5 usa um handshake com `Hello`, desafio (`authentication.challenge`) e salt (`authentication.salt`). A resposta é calculada com SHA-256 em Base64 sobre `senha + salt` e depois sobre `resultado + challenge`. Regras de implementação:

- nunca registrar a senha nem o valor calculado em logs;
- não incluir a senha em respostas da API;
- tratar `Hello` sem autenticação quando o OBS não exigir senha, mas manter a opção configurada;
- enviar `Identify` com `rpcVersion: 1` e as assinaturas de evento necessárias;
- validar a versão do OBS e falhar com mensagem clara se o servidor não suportar v5.

Biblioteca: ainda **não escolhida**. A implementação futura deve preferir um cliente assíncrono mantido e compatível com v5 (por exemplo, uma dependência dedicada) em vez de reimplementar o protocolo. A escolha será registrada em `pyproject.toml` apenas na fase em que for usada.

## 5. Operações previstas

### 5.1 Leitura (primeira etapa da integração)

| Operação | Uso |
| --- | --- |
| `GetVersion` | Diagnóstico de versão e compatibilidade. |
| `GetRecordStatus` | Saber se está gravando, pausado e o caminho do arquivo atual. |
| `GetRecordDirectory` | Conferir se o diretório do OBS coincide com o da fonte. |
| Evento `RecordStateChanged` | Detectar início, pausa, retomada e fim da gravação. |
| Evento de troca de arquivo (quando disponível) | Identificar o novo arquivo sem polling. |

### 5.2 Controle (etapa posterior, opcional)

| Operação | Cuidado |
| --- | --- |
| `StartRecord` | Exigir confirmação explícita e fonte autorizada ativa. |
| `StopRecord` | Registrar quem solicitou e o motivo. |
| `ToggleRecord` / pausa | Evitar uso acidental; preferir operações idempotentes. |
| Replay buffer | Avaliar somente se necessário para reduzir latência; não é requisito da detecção. |

Comandos de controle só entram depois de autenticação na API e de um fluxo de confirmação. A API da Fase 1 não tem autenticação e, por isso, não deve ganhar comandos remotos ainda.

## 6. Fluxo futuro de eventos

```text
OBS (WebSocket v5)
   │ RecordStateChanged (STARTED)
   ▼
app.obs.client (conexão + reconexão)
   │ emite evento interno
   ▼
app.capture.monitor / orquestrador
   │ agenda uma varredura da fonte correspondente
   ▼
scanner (regra de estabilidade + deduplicação)
   │
   ▼
recordings (status=ready)
```

O evento é um **gatilho**, não uma prova de que o arquivo está completo. Mesmo com `RecordStateChanged (STOPPED)`, o scanner deve confirmar existência, tamanho, extensão e estabilidade antes de persistir. Isso mantém a integridade mesmo se o evento se perder ou a conexão cair.

## 7. Reconexão e resiliência

- Reconectar com backoff exponencial (por exemplo, 1 s, 2 s, 4 s… até um teto de 30 s) e jitter.
- Não bloquear o event loop durante tentativas; a conexão roda em task própria.
- Limitar tentativas/logs para não inundar o arquivo de log.
- Expor estado em `/health` ou em um futuro `/api/v1/obs/connection`: `disconnected`, `connecting`, `connected`, `error`.
- Se o WebSocket cair, o monitor por arquivos continua funcionando.
- A reconexão não deve duplicar eventos nem registrar o mesmo arquivo duas vezes; a restrição `UNIQUE(path)` permanece como última defesa.

## 8. Segurança

- Escutar o OBS WebSocket apenas em loopback ou rede confiável.
- Nunca versionar a senha; usar `.env` ignorado ou secret manager.
- A senha é carregada como `SecretStr`; ler somente com `get_secret_value()` no handshake.
- Não expor a senha em logs, traces, respostas HTTP ou mensagens de erro.
- Validar comandos recebidos pela API com autenticação e autorização antes de encaminhá-los ao OBS.
- Auditar comandos de controle (quem, quando, qual fonte, qual ação).
- Não implementar comandos que contornem proteções da plataforma ou capturem conteúdo não autorizado.

## 9. Estratégia de testes futura

- Testar o cliente contra um **servidor WebSocket falso** (handshake, autenticação, eventos), sem exigir OBS real.
- Cobrir: `Hello` com e sem autenticação, senha inválida, queda de conexão, reconexão, evento duplicado e evento fora de ordem.
- Manter os testes atuais de ingestão por arquivos independentes do WebSocket.
- Testar que a senha não aparece em logs nem em respostas da API.

## 10. Critérios para iniciar a implementação

1. Fase 1 estável e com testes verdes.
2. Necessidade concreta de evento ou controle remoto validada.
3. Biblioteca v5 escolhida e fixada em `pyproject.toml`.
4. Autenticação da API definida, caso haja comandos de controle.
5. Documentação de segurança e auditoria aprovada.

Até lá, a integração permanece apenas como contrato e configuração.

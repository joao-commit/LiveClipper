# Configuração do OBS Studio (Fase 1)

## Pré-requisitos

- Autorização explícita do criador para capturar e reutilizar o conteúdo.
- OBS Studio instalado.
- Uma pasta local dedicada às gravações, por exemplo `./data/obs` ou uma pasta por criador.

## 1. Configurar a saída de gravação

No OBS:

1. Abra **Configurações → Saída**.
2. Em **Modo de saída**, escolha **Avançado** (ou Simples, se preferir).
3. Em **Gravação**:
   - **Caminho de gravação:** a pasta configurada no LiveClipper, por exemplo `/home/usuario/projeto_clipador/data/obs`.
   - **Formato:** `mkv` é recomendado por resistir melhor a encerramentos inesperados. O LiveClipper aceita `.mkv`, `.mp4`, `.mov`, `.flv` e `.ts` por padrão.
   - **Gerar arquivo com carimbo de data/hora:** recomendado; evita sobrescrita.
4. Em **Áudio**, garanta que a faixa do conteúdo autorizado esteja sendo gravada.
5. Faça uma gravação curta de teste e confirme que o arquivo aparece na pasta.

O nome do arquivo é livre; o LiveClipper usa o caminho absoluto como identidade.

> Se o OBS estiver configurado para **remuxar** a gravação para MP4, a pasta pode acabar com dois arquivos do mesmo conteúdo (`.mkv` e `.mp4`). Como a deduplicação é por caminho, ambos seriam registrados. Escolha um único formato de gravação ou mantenha o remux em outra pasta.

## 2. Cenas e fontes

A captura deve ser feita da forma autorizada pelo criador. Um cenário comum:

- **Fonte:** navegador ou captura de janela com a transmissão autorizada;
- **Áudio:** saída de áudio do sistema ou dispositivo correspondente;
- **Cena:** composição que será gravada.

Não use o LiveClipper para burlar restrições da plataforma, DRM ou mecanismos de proteção.

## 3. Configurar o LiveClipper

No `.env`:

```env
LIVECLIPPER_OBS_RECORDINGS_DIR=./data/obs
LIVECLIPPER_CAPTURE_POLL_INTERVAL_SECONDS=5
LIVECLIPPER_CAPTURE_SETTLE_SECONDS=20
LIVECLIPPER_CAPTURE_AUTO_START=true
```

- **poll interval:** frequência da varredura.
- **settle:** tempo mínimo sem alteração para considerar a gravação encerrada. Aumente se o OBS demorar a finalizar arquivos grandes.

Cadastre a fonte pela API, com a referência de autorização:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/sources \
  -H 'Content-Type: application/json' \
  -d '{
    "name": "canal-autorizado",
    "platform": "youtube",
    "creator_name": "Criador Autorizado",
    "authorization_reference": "contrato-2026-001",
    "authorization_notes": "Permissão de captura e reutilização.",
    "authorization_confirmed": true,
    "watch_directory": "/home/usuario/projeto_clipador/data/obs"
  }'
```

## 4. Validar

```bash
curl http://127.0.0.1:8000/api/v1/obs/status
curl -X POST http://127.0.0.1:8000/api/v1/capture/scan
curl http://127.0.0.1:8000/api/v1/recordings
```

Após a gravação terminar e o período de settle passar, o arquivo deve aparecer com status `ready`.

## 5. Problemas comuns

| Sintoma | Verificação |
| --- | --- |
| `scanned_files=0` | Extensão não está na allowlist? Pasta correta? OBS realmente gravou? |
| Arquivo sempre `unstable` | OBS ainda está escrevendo ou o `settle` é curto demais. |
| `scanned_files>0`, `registered=0` | Veja `duplicates`, `unstable`, `ignored` no relatório de scan. |
| `diretório não encontrado` | O caminho da fonte não existe ou foi movido. |
| Duas fontes na mesma pasta | Evite: o `path` é único e a primeira fonte que registrar vence. Use uma pasta por fonte. |

## WebSocket do OBS

A Fase 1 **não** usa o WebSocket. `LIVECLIPPER_OBS_WEBSOCKET_URL` e a senha existem apenas como preparação para fases futuras (controle de gravação/replay buffer). Não é necessário habilitar o servidor WebSocket do OBS agora.

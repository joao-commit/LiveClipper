# Configuração do OBS Studio — janela do navegador e áudio

Este guia configura o OBS para capturar **uma janela autorizada do navegador** e o **áudio correspondente**, gravando em um diretório que o LiveClipper observa.

> **Autorização primeiro:** capture apenas conteúdo para o qual você possui permissão explícita de captura e reutilização. Não use o LiveClipper nem o OBS para contornar DRM, restrições de plataforma ou direitos de terceiros.

## 1. Pré-requisitos

- Autorização registrada (contrato, e-mail, termo ou ticket).
- OBS Studio instalado e atualizado.
- Navegador com o conteúdo autorizado aberto.
- Uma pasta local dedicada às gravações, por exemplo `./data/obs` ou uma pasta por criador.
- Espaço em disco suficiente para a duração prevista.

## 2. Configurar a saída de gravação

No OBS:

1. Abra **Configurações → Saída**.
2. Em **Modo de saída**, escolha **Avançado** para controlar encoder, qualidade e faixas; o modo **Simples** também funciona.
3. Em **Gravação**:
   - **Caminho de gravação:** a pasta configurada no LiveClipper, por exemplo `/home/usuario/projeto_clipador/data/obs`.
   - **Formato:** `mkv` é recomendado por resistir melhor a encerramentos inesperados. O LiveClipper aceita `.mkv`, `.mp4`, `.mov`, `.flv` e `.ts` por padrão.
   - **Gerar arquivo com carimbo de data/hora:** recomendado; evita sobrescrita.
   - **Encoder:** hardware (NVENC, Quick Sync, AMF) ou `x264`, conforme a máquina. Para clipes posteriores, prefira boa qualidade: 1080p ou resolução da janela, 30/60 fps e taxa adequada.
4. Em **Áudio**, garanta que a faixa do conteúdo autorizado esteja sendo gravada.
5. Faça uma gravação curta de teste e confirme que o arquivo aparece na pasta.

O nome do arquivo é livre; o LiveClipper usa o caminho absoluto como identidade.

> Se o OBS estiver configurado para **remuxar** a gravação para MP4, a pasta pode acabar com dois arquivos do mesmo conteúdo (`.mkv` e `.mp4`). Como a deduplicação é por caminho, ambos seriam registrados. Escolha um único formato ou mantenha o remux em outra pasta.

## 3. Capturar a janela do navegador

### 3.1 Preparar o navegador

- Abra a transmissão/conteúdo autorizado e deixe-o em reprodução.
- Mantenha a aba ativa e o som do navegador **não silenciado**.
- Feche notificações e abas com dados pessoais; use um perfil/janela dedicado.
- Evite minimizar a janela. Alguns métodos de captura deixam de renderizar janelas ocultas, minimizadas ou em outro espaço de trabalho. Prefira um monitor/área de trabalho dedicado.
- Se o conteúdo exigir interação inicial (aceitar cookies, iniciar reprodução), faça isso antes de gravar.

### 3.2 Adicionar a fonte no OBS

1. Na cena que será gravada, clique em **+** em **Fontes**.
2. Escolha a fonte de captura de janela adequada ao sistema:
   - **Windows:** **Captura de Janela** (*Window Capture*). Em versões recentes, o método **Windows 10 (1903 e superior)** usa Windows Graphics Capture e costuma funcionar melhor com navegadores acelerados por hardware.
   - **macOS:** **Captura de Tela do macOS** (*macOS Screen Capture*) com o modo **Janela**, ou **Captura de Janela** conforme a versão.
   - **Linux/X11:** **Captura de Janela (XSHM)**.
   - **Linux/Wayland:** captura via **PipeWire**, selecionando a janela no seletor do sistema.
3. Nomeie a fonte, por exemplo `navegador-canal-autorizado`.
4. Em **Propriedades**, selecione a janela do navegador. Se a lista estiver vazia, mantenha a janela aberta e clique em atualizar; em alguns casos é preciso reiniciar o OBS.
5. Se houver opção **Capturar áudio** na fonte de janela (Windows recente), ela pode ser usada; caso contrário, configure o áudio separadamente na seção 4.

### 3.3 Enquadrar

- Use **Transformar → Ajustar à tela** (*Fit to screen*) e depois ajuste manualmente.
- Para remover barra de endereço/abas, segure `Alt` (Windows/Linux) ou `Option` (macOS) e arraste as bordas para recortar (*crop*).
- Evite esticar a imagem: mantenha proporção para não distorcer o vídeo.
- Confira no preview se o conteúdo está nítido e sem elementos privados.

### 3.4 Alternativa: fonte Navegador (*Browser Source*)

Se você controla a página e a autorização permite, a fonte **Navegador** pode carregar uma URL diretamente, sem capturar a janela inteira. Porém:

- ela não funciona para todo conteúdo protegido ou que exija login/interação;
- pode falhar em páginas com DRM ou restrições de incorporação;
- não deve ser usada para contornar proteções.

Para o cenário deste projeto — capturar a janela do navegador e seu áudio — a **captura de janela** é o caminho padrão.

## 4. Capturar o áudio do navegador

O objetivo é gravar o áudio do conteúdo autorizado, sem capturar notificações, chamadas ou outros sons irrelevantes.

### 4.1 Windows

Opções, conforme a versão do OBS:

1. **Captura de Áudio do Aplicativo (BETA)** (*Application Audio Capture*): escolha o processo do navegador. É a opção mais isolada.
2. **Áudio da Área de Trabalho** (*Desktop Audio*): captura toda a saída do sistema. Simples, mas inclui notificações e outros aplicativos.
3. **Captura de Janela** com **Capturar áudio** habilitado, quando disponível.

Se usar áudio da área de trabalho, ative **Não Perturbe** e feche aplicativos que possam emitir som.

### 4.2 Linux

- **PipeWire:** use **Captura de Áudio do Aplicativo (PipeWire)** e selecione o fluxo do navegador. É a opção preferível.
- **Áudio da Área de Trabalho (PipeWire/PulseAudio):** captura a saída global. Simples, porém menos isolado.
- Em distribuições com PipeWire, o seletor pode pedir autorização para compartilhar o áudio do aplicativo.

### 4.3 macOS

- **Captura de Áudio do macOS** (*macOS Audio Capture*), quando disponível na versão do OBS, permite escolher o aplicativo.
- Alternativa: instalar um dispositivo de áudio virtual (por exemplo, BlackHole ou Loopback), criar um **Dispositivo de Múltiplas Saídas** e rotear o navegador para ele. Verifique licença e configuração do driver.
- Ajuste o atraso em **Propriedades Avançadas de Áudio → Deslocamento de sincronização** se o áudio ficar adiantado/atrasado.

### 4.4 Evitar áudio duplicado ou eco

- Não capture o mesmo áudio por duas fontes (por exemplo, aplicativo **e** área de trabalho) no mesmo mix.
- Se ouvir o conteúdo capturado pelos alto-falantes, use fones para evitar realimentação.
- **Monitorar e sair** (*Monitor and Output*) só deve ser usado com fones; caso contrário, deixe o monitoramento desligado.
- Confira no **Mixer de Áudio** se há dois medidores ativos para o mesmo som.

### 4.5 Níveis e faixas

- No mixer, ajuste o ganho para picos em torno de **-12 dB a -6 dB**, evitando clipping (vermelho).
- Em **Configurações → Saída → Avançado → Gravação**, habilite as faixas necessárias.
- Em **Propriedades Avançadas de Áudio**, atribua as fontes às faixas. Para compatibilidade, mantenha uma faixa com o mix completo; faixas separadas podem ser úteis no futuro, mas o LiveClipper ainda não as processa.
- O formato `.mkv` suporta múltiplas faixas; players e ferramentas posteriores podem selecionar a faixa desejada.

### 4.6 Teste de áudio

1. Grave 15–30 segundos.
2. Reproduza o arquivo e confirme que há áudio do navegador, sem eco, cortes ou silêncio.
3. Se possível, inspecione as faixas com `ffprobe` (ferramenta externa; não é dependência da Fase 1).
4. Verifique a sincronia entre imagem e som; ajuste o deslocamento se necessário.

## 5. Cenas, perfis e múltiplas fontes

- Prefira **uma cena por fonte autorizada** (por exemplo, `canal-a`, `canal-b`).
- Para cada criador, use um perfil com caminho de gravação próprio e uma pasta correspondente no LiveClipper.
- Não aponte duas fontes do LiveClipper para a mesma pasta: o caminho é único e a primeira fonte que registrar vence.
- Mantenha nomes de cenas e arquivos rastreáveis; isso facilita auditoria e retenção.

## 6. Configurar o LiveClipper

No `.env`:

```env
LIVECLIPPER_OBS_RECORDINGS_DIR=./data/obs
LIVECLIPPER_CAPTURE_POLL_INTERVAL_SECONDS=5
LIVECLIPPER_CAPTURE_SETTLE_SECONDS=20
LIVECLIPPER_CAPTURE_AUTO_START=true
```

- **poll interval:** frequência da varredura.
- **settle:** tempo mínimo sem alteração para considerar a gravação encerrada. Aumente se o OBS demorar a finalizar arquivos grandes.
- **SOURCE_ADAPTER:** mantenha `obs_directory` na Fase 1.

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

## 7. Validar

```bash
curl http://127.0.0.1:8000/api/v1/obs/status
curl -X POST http://127.0.0.1:8000/api/v1/capture/scan
curl http://127.0.0.1:8000/api/v1/recordings
```

Após a gravação terminar e o período de settle passar, o arquivo deve aparecer com status `ready`.

## 8. Problemas comuns

| Sintoma | Verificação |
| --- | --- |
| Tela preta na captura de janela | Método de captura incompatível com navegador acelerado; tente Windows Graphics Capture, PipeWire ou desative a aceleração de hardware do navegador. |
| Janela não aparece na lista | Mantenha a janela aberta e visível; reinicie o OBS; verifique permissões de captura de tela no sistema. |
| Sem áudio na gravação | Aba silenciada? Fonte de áudio correta? Faixa atribuída? Monitores/ganho? |
| Áudio duplicado ou eco | Duas fontes capturando o mesmo som; remova uma ou ajuste o mix. |
| Áudio fora de sincronia | Use o deslocamento de sincronização nas propriedades avançadas de áudio. |
| `scanned_files=0` | Extensão não está na allowlist? Pasta correta? OBS realmente gravou? |
| Arquivo sempre `unstable` | OBS ainda está escrevendo ou o `settle` é curto demais. |
| `scanned_files>0`, `registered=0` | Veja `duplicates`, `unstable`, `ignored` no relatório de scan. |
| `diretório não encontrado` | O caminho da fonte não existe ou foi movido. |
| Duas fontes na mesma pasta | Evite: o `path` é único. Use uma pasta por fonte. |

## 9. WebSocket do OBS

A Fase 1 **não** usa o WebSocket. `LIVECLIPPER_OBS_WEBSOCKET_URL` e a senha existem apenas como preparação. O desenho futuro está em [`obs-websocket.md`](obs-websocket.md). Não é necessário habilitar o servidor WebSocket do OBS agora.

## 10. Checklist antes de gravar

- [ ] Autorização de captura e reutilização registrada.
- [ ] Conteúdo autorizado aberto na janela correta.
- [ ] Captura de janela enquadrada, sem dados pessoais.
- [ ] Áudio do navegador sendo capturado por uma única fonte.
- [ ] Níveis sem clipping e sincronia conferida.
- [ ] Pasta de gravação correta, com espaço suficiente.
- [ ] Formato `.mkv` (ou um único formato) e carimbo de data/hora.
- [ ] Fonte cadastrada no LiveClipper com `authorization_reference`.
- [ ] Gravação de teste validada em `/api/v1/recordings`.

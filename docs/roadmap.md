# Roadmap

## Fase 1 — Fundação OBS (atual)

- [x] Estrutura de pacotes por responsabilidade
- [x] Configuração por ambiente
- [x] SQLite + SQLAlchemy
- [x] Cadastro de fontes com autorização obrigatória
- [x] Leitura de gravações locais do OBS
- [x] Monitor periódico com regra de estabilidade
- [x] API de health, fontes, captura e gravações
- [x] Testes automatizados

## Fase 2 — Catálogo e buffer

- Metadados de mídia com FFprobe (duração, codecs, resolução, faixas de áudio)
- Estratégia de buffer circular dos últimos minutos
- Política de retenção e limpeza de arquivos
- Migrações com Alembic
- Estado de processamento por gravação

## Fase 3 — Detecção

- Análise de energia/picos de áudio
- Transcrição com Faster-Whisper
- Leitura de chat somente quando houver autorização e acesso permitido
- Pontuação e janelas candidatas persistidas

## Fase 4 — Clipping

- Recorte com FFmpeg
- Conversão para 9:16 com OpenCV/FFmpeg
- Thumbnails e metadados do clipe
- Catálogo de artefatos em `output/`

## Fase 5 — Legendas

- Legendas a partir da transcrição
- Estilos, quebra de linha e sincronização
- Queima opcional no vídeo

## Fase 6 — Publicação

- OAuth 2.0 com escopo mínimo
- YouTube Data API v3
- Idempotência e agendamento
- Registro de resultado e tratamento de falhas

## Princípios permanentes

- Apenas conteúdo autorizado.
- Nenhum download de transmissão, extração de URL interna ou contorno de DRM.
- Dependências adicionadas somente na fase que as utiliza.
- Testes e documentação acompanham cada fase.

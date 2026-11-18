# Roadmap — LiveClipper 2.0

## Fase 1 — Fundação e catálogo de gravações (concluída)

- [x] Estrutura de pacotes por responsabilidade
- [x] Configuração por ambiente com Pydantic Settings
- [x] SQLite + SQLAlchemy
- [x] API FastAPI com health check
- [x] Cadastro de fontes autorizadas com referência de autorização
- [x] Leitura de gravações locais produzidas pelo OBS
- [x] Monitor periódico com regra de estabilidade
- [x] Contrato de origem de vídeo substituível (`SourceAdapter`)
- [x] API de health, fontes, captura, gravações e diagnóstico do OBS
- [x] Testes automatizados da ingestão e da segurança

## Fase 2 — Sessões, segmentos e processamento contínuo (planejada)

- Criar `capture_sessions` como referência temporal oficial:
  - `id`
  - `source_id`
  - `started_at`
  - `ended_at`
  - `status`
  - `created_at`
- Complementar `recordings`, de forma aditiva, com:
  - `session_id`
  - `duration_seconds`
  - `start_offset_seconds`
- Associar gravações estáveis à sessão correta.
- Usar `start_offset_seconds` para ordenar segmentos e calcular a posição de cada arquivo na transmissão.
- Definir inferência de sessão enquanto não houver OBS WebSocket.
- Introduzir migração com Alembic; não usar `create_all` para alterar tabelas existentes.
- Receber segmentos do OBS e enfileirá-los para análise.
- Definir política de reinício, lacuna e sessão incompleta.
- Testar continuidade, arquivos divididos, lacunas e dados legados sem sessão.

## Fase 3 — Análise de áudio e transcrição (planejada)

- Extrair áudio com FFmpeg em PCM mono 16 kHz.
- Validar duração, codecs e faixa de áudio com FFprobe.
- Analisar intensidade e variações sonoras.
- Integrar Faster-Whisper para transcrição de fala.
- Converter timestamps locais para o tempo relativo à sessão.
- Manter o chat do YouTube como fonte complementar opcional, somente por acesso oficial e autorizado.
- Não tornar análise visual por OpenCV obrigatória; o foco do MVP é áudio e transcrição.
- Testar extração, transcrição com duplo de teste e falhas de FFmpeg/FFprobe.

## Fase 4 — Identificação de momentos, delimitação e descrição (planejada)

- Identificar acontecimentos interessantes a partir de evidências de áudio e transcrição.
- Delimitar início e fim de cada candidato em segundos relativos à sessão.
- Evitar candidatos sobrepostos, vazios ou curtos demais.
- Aplicar duração mínima e máxima.
- Gerar descrição simples e objetiva.
- Calcular `score` interno para ordenação.
- Calibrar limiares e reduzir falsos positivos.

## Fase 5 — Persistência, API de consulta e validação do resultado (planejada)

- Criar `clip_candidates`:
  - `id`
  - `session_id`
  - `start_seconds`
  - `end_seconds`
  - `description`
  - `score`
  - `created_at`
- Aplicar FKs, índices e restrições de integridade:
  - `session_id` referencia `capture_sessions.id`;
  - `start_seconds >= 0`;
  - `end_seconds > start_seconds`;
  - `0 <= score <= 1`;
  - índice `(session_id, start_seconds)`.
- Persistir candidatos no SQLite.
- Expor consulta pela API com apenas início, fim e descrição.
- Validar resultados com revisão humana.
- Medir precisão, cobertura e utilidade dos candidatos.
- Documentar operação, retenção e reprocessamento.

## Fora do escopo — permanentemente

Estes itens não são fases futuras e não devem entrar no roadmap:

- Editor de vídeo.
- Recorte físico ou renderização.
- Shorts e conversão vertical 9:16.
- Legendas.
- Publicação no YouTube ou em qualquer plataforma.
- OAuth, upload e agendamento.
- Interface gráfica.
- Download de transmissões, URLs internas ou DRM.

## Limites da etapa atual

Esta correção é apenas documental e arquitetural. Não implementa detector, captura segmentada, transcrição, tabelas, migrações, dependências ou rotas de candidatos. Nenhum modelo, endpoint ou comportamento existente é alterado.

## Princípios permanentes

- Apenas conteúdo autorizado.
- Nenhum download de transmissão, extração de URL interna ou contorno de DRM.
- O produto entrega candidatos; a decisão de editar ou publicar é humana e externa.
- A sessão é a referência temporal oficial.
- Áudio e transcrição são o foco do MVP; análise visual não é obrigatória.
- Dependências adicionadas somente na fase que as utiliza.
- Migrações de banco não destrutivas.
- Testes e documentação acompanham cada fase.
- Nenhum módulo é preenchido com código fictício.

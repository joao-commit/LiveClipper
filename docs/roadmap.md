# Roadmap — LiveClipper 2.0

## Fase 0 — Fundação (concluída)

- [x] Estrutura de pacotes por responsabilidade
- [x] Configuração por ambiente com Pydantic Settings
- [x] SQLite + SQLAlchemy
- [x] API FastAPI com health check
- [x] Testes automatizados iniciais

## Fase 1 — Ingestão OBS (concluída)

- [x] Cadastro de fontes com autorização obrigatória
- [x] Leitura de gravações locais do OBS
- [x] Monitor periódico com regra de estabilidade
- [x] Contrato de origem de vídeo substituível e registro de adaptadores
- [x] Requisitos de segurança, autorização e higiene do Git
- [x] API de health, fontes, captura e gravações
- [x] Testes automatizados da ingestão

## Fase 2 — Revisão de escopo 2.0 (concluída)

- [x] Novo objetivo: detecção de momentos interessantes, sem edição/publicação
- [x] Detecção definida como módulo principal planejado (`app/detection`)
- [x] Pacotes de clipping e publicação marcados como fora do escopo
- [x] OpenCV excluído
- [x] FFmpeg/FFprobe e Faster-Whisper documentados como preparação futura
- [x] Modelo `clip_candidates` planejado
- [x] Tabela `capture_sessions` proposta para preservar a continuidade temporal
- [x] README e documentação de arquitetura, especificação e roadmap atualizados
- [x] Nenhuma alteração destrutiva no banco
- [x] Detector de picos ainda não implementado

## Fase 3 — Sessões, esquema e metadados (planejada)

- Criar `capture_sessions` com `started_at`, `ended_at`, status e vínculo com a fonte.
- Adicionar a `recordings`, de forma aditiva, `session_id`, `segment_index`, `start_offset_seconds` e `duration_seconds`.
- Introduzir migração com Alembic; não usar `create_all` para alterar tabelas existentes.
- Associar gravações estáveis a sessões, com inferência documentada enquanto não houver WebSocket.
- Validar duração, codecs e faixas de áudio com FFprobe.
- Criar a tabela `clip_candidates`.
- Criar repositório e endpoint de consulta retornando apenas início, fim e descrição.
- Testar continuidade, lacunas, arquivos divididos e dados legados sem sessão.

## Fase 4 — Análise de áudio e candidatos (planejada)

- Extrair PCM mono 16 kHz com FFmpeg em janelas configuráveis.
- Implementar detector de energia/picos (somente nesta fase).
- Integrar Faster-Whisper para transcrição com timestamps.
- Converter timestamps locais para o tempo relativo à sessão.
- Montar candidatos com duração mínima/máxima, supressão de sobreposição e score.
- Gerar descrição simples a partir da transcrição e/ou de regras de evidência.
- Persistir candidatos e expor a tabela para revisão humana.
- Testar extração, transcrição com duplo de teste, falhas de FFmpeg/FFprobe e limites de duração.

## Fase 5 — Operação e robustez (planejada)

- Calibrar limiar de picos, score e duração por tipo de conteúdo.
- Adicionar retenção de gravações e candidatos.
- Melhorar observabilidade da análise (status, erros, tempo de processamento).
- Avaliar processamento concorrente sem bloquear o monitor.
- Documentar procedimentos de reprocessamento e auditoria.
- Revisar segurança para eventual exposição remota da API.

## Fora do escopo — permanentemente

Estas funcionalidades não fazem parte do LiveClipper e não devem entrar em fases futuras:

- Edição, recorte ou renderização de vídeo.
- Geração de Shorts ou conversão para 9:16.
- Legendas, queima de texto ou sincronização.
- Publicação no YouTube ou em qualquer plataforma.
- OAuth, upload, agendamento e integração com APIs de publicação.
- OpenCV e processamento de imagem em tempo real.
- Download de transmissões, URLs internas, DRM ou bypass de plataforma.
- Interface gráfica.

## Limites da fase atual

A revisão de escopo não implementa detector de picos, transcrição, novas tabelas, migrações ou rotas de candidatos. Os pacotes `app.detection`, `app.clipping` e `app.publishing` permanecem sem funções executáveis. `app.clipping` e `app.publishing` são apenas marcadores históricos e não pertencem ao produto.

## Princípios permanentes

- Apenas conteúdo autorizado.
- Nenhum download de transmissão, extração de URL interna ou contorno de DRM.
- O produto entrega candidatos; a decisão de editar/publicar é humana e externa.
- Dependências adicionadas somente na fase que as utiliza.
- Migrações de banco não destrutivas.
- Testes e documentação acompanham cada fase.
- Nenhum módulo é preenchido com código fictício; funcionalidade só entra quando a fase correspondente for implementada.

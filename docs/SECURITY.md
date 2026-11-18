# Segurança e autorização

Este documento define as regras de segurança da Fase 1 e como cada requisito é aplicado no código, na configuração e no fluxo operacional.

## 1. Requisitos e controles

| Requisito | Controle atual | Onde |
| --- | --- | --- |
| Operar somente com conteúdo autorizado | Cadastro exige `authorization_confirmed: true` e `authorization_reference`; a varredura revalida referência e `authorized_at` antes de ingerir. | `app/sources/schemas.py`, `app/capture/scanner.py` |
| Não armazenar credenciais no código-fonte | Nenhuma credencial é versionada; segredos vêm de `.env`/ambiente. A senha do OBS usa `SecretStr`. | `app/config.py`, `.env.example` |
| Não enviar gravações ou tokens ao Git | `.gitignore` cobre `.env`, bancos, `data/`, `output/`, mídia e material secreto. | `.gitignore` |
| Não publicar automaticamente | Não há OAuth, upload, agendamento ou rota de publicação. O pacote `app.publishing` contém apenas o contrato futuro. | `app/publishing/__init__.py` |
| Não acessar fontes privadas/protegidas | A Fase 1 lê apenas arquivos locais de diretórios autorizados; não baixa streams, não usa cookies, não contorna DRM e não segue symlinks para fora da pasta. | `app/sources/local.py` |

## 2. Autorização de conteúdo

### 2.1 Regras de cadastro

Uma fonte só pode ser criada quando:

- `authorization_confirmed` é `true` de forma explícita;
- `authorization_reference` tem ao menos 3 caracteres e não é vazio;
- `watch_directory` existe, é um diretório e pode ser resolvido;
- as extensões são válidas.

O sistema **registra** a autorização; ele não valida a autenticidade jurídica do documento. O operador deve manter a evidência (contrato, e-mail, termo, ticket) arquivada e acessível para auditoria.

### 2.2 Defesa em profundidade na varredura

Antes de ingerir qualquer arquivo, o scanner verifica novamente:

```python
if (
    not source.authorization_reference
    or not source.authorization_reference.strip()
    or source.authorized_at is None
):
    return SourceScanReport(..., error="autorização de captura não confirmada...")
```

Isso protege contra registros **sem autorização válida** — referência ausente, vazia ou composta apenas por espaços. Inserções diretas no banco que fabriquem uma referência e uma data não são detectáveis pelo scanner; trate o arquivo SQLite como dado sensível e restrinja seu acesso no sistema operacional.

### 2.3 Responsabilidades do operador

- Obter autorização de **captura** e de **reutilização**.
- Limitar a captura ao conteúdo, período e finalidade autorizados.
- Respeitar direitos de terceiros (música, convidados, marcas) e a legislação aplicável.
- Remover gravações e dados quando a autorização expirar ou for revogada.
- Não usar o projeto para burlar termos de plataforma, DRM ou restrições de acesso.
- Não cadastrar fontes privadas ou protegidas sem permissão.

### 2.4 Limitação conhecida

O modelo atual guarda `authorized_at`, mas não uma data de expiração. A revogação é operacional: desabilitar a fonte, remover o diretório ou apagar os registros. Validade automática e trilha de auditoria estão previstas para uma fase futura.

## 3. Credenciais e segredos

### 3.1 Regras

- Nunca escrever senhas, tokens, chaves ou cookies no código, em testes, em documentos ou em exemplos.
- O único arquivo de configuração local é `.env`, ignorado pelo Git.
- `.env.example` contém apenas valores vazios ou não sensíveis.
- A senha do OBS WebSocket é carregada como `SecretStr`; `repr()`/`str()` não revelam o valor.
- A senha nunca é retornada por `/api/v1/obs/status`, logs ou mensagens de erro.
- Quando o cliente WebSocket for implementado, o valor só deve ser lido no momento da autenticação com `get_secret_value()` e nunca registrado.

### 3.2 Exemplo de configuração

```env
LIVECLIPPER_OBS_WEBSOCKET_URL=ws://127.0.0.1:4455
LIVECLIPPER_OBS_WEBSOCKET_PASSWORD=
```

Preencha a senha apenas no `.env` local, nunca no `.env.example`.

### 3.3 Rotação

Se uma credencial for exposta:

1. Revogue/rotacione a credencial no serviço de origem.
2. Remova o valor do `.env` e de qualquer histórico local.
3. Se foi commitada, remova do histórico com `git filter-repo` (ou ferramenta equivalente), force o push e avise os colaboradores.
4. Verifique forks, caches de CI e artefatos publicados.
5. Registre o incidente.

## 4. Higiene do repositório Git

O `.gitignore` bloqueia:

- `.env`, `.env.*` (exceto `.env.example`);
- bancos SQLite (`*.db`, `*.sqlite*`);
- `data/*` e `output/*` (exceto `.gitkeep`);
- gravações e mídia (`*.mkv`, `*.mp4`, `*.mov`, `*.flv`, `*.ts`, `*.m4v`, `*.webm`, áudio);
- material secreto (`*.pem`, `*.key`, `*.p12`, `*.pfx`, `client_secret*.json`, `credentials*.json`, `token*.json`, `secrets*.json`).

Antes de cada commit:

```bash
git status --short
git diff --cached --stat
git ls-files | grep -Ei '\.(env|mkv|mp4|mov|flv|ts|db|pem|key)$|token|secret' || true
```

Nunca use `git add -f` para mídia, bancos ou `.env`. Se uma gravação precisar ser compartilhada, use armazenamento externo autorizado, não o repositório.

## 5. Publicação desativada nesta fase

A Fase 1 **não publica** conteúdo:

- não há OAuth 2.0;
- não há upload para YouTube ou qualquer plataforma;
- não há agendamento, fila de publicação ou integração com APIs de terceiros;
- `httpx` existe apenas como dependência de desenvolvimento para o `TestClient`;
- `app/publishing` contém somente a descrição do contrato futuro.

A publicação só poderá ser implementada na Fase 6, com escopo mínimo de OAuth, autenticação da API, confirmação explícita do operador e auditoria. Nenhuma rota de publicação deve ser adicionada antes disso.

## 6. Fontes privadas ou protegidas

O projeto não acessa conteúdo restrito:

- não baixa transmissões;
- não extrai URLs internas, cookies, tokens de sessão ou manifests;
- não contorna DRM, paywall, geobloqueio ou autenticação de plataforma;
- não usa captura de tela para burlar proteções;
- não abre conexões de rede para obter mídia nesta fase.

A ingestão é estritamente local: o OBS grava um arquivo em um diretório autorizado e o LiveClipper lê metadados desse arquivo.

### 6.1 Contenção de diretório

O adaptador local:

- resolve o diretório observado;
- ignora nomes iniciados por `.`;
- ignora symlinks;
- verifica se o caminho resolvido está contido no diretório autorizado (`Path.is_relative_to`);
- ignora arquivos sem permissão de leitura;
- aceita apenas extensões da allowlist.

Essas regras impedem que um link simbólico dentro da pasta aponte para arquivos fora do escopo autorizado.

### 6.2 Limites

A contenção de caminho não substitui controles do sistema operacional. Recomenda-se:

- executar o LiveClipper com um usuário sem privilégios administrativos;
- dar acesso de leitura apenas às pastas autorizadas;
- não montar diretórios sensíveis no container/processo;
- manter o OBS e o LiveClipper na mesma máquina confiável.

## 7. API e rede

- A API da Fase 1 não tem autenticação e deve escutar em `127.0.0.1`.
- Não exponha a porta 8000 nem a porta 4455 do OBS diretamente na internet.
- Para acesso remoto, use autenticação, TLS, rate limiting e reverse proxy.
- Não habilite CORS amplo sem necessidade.
- O endpoint `/api/v1/obs/status` não retorna senha.

## 8. Logs

- Não registrar credenciais, tokens, cookies ou conteúdo de arquivos.
- Erros de fonte devem informar caminho e motivo, sem expor dados sensíveis.
- Em produção, restringir acesso aos logs e definir retenção.
- Revisar logs antes de compartilhá-los em issues.

## 9. Testes de segurança

A suíte cobre:

- senha do OBS não aparece em `repr`/`str` das configurações;
- `.env.example` não contém valores sensíveis preenchidos;
- `.gitignore` cobre ambiente, dados, mídia, bancos e chaves;
- não existem rotas de publicação/upload/YouTube/OAuth;
- scanner recusa fonte cuja autorização foi removida no banco;
- adaptador local ignora symlinks que apontam para fora da pasta autorizada.

Execute:

```bash
pytest tests/test_security.py
pytest
```

## 10. Checklist de revisão

- [ ] Nenhuma credencial, token ou gravação no diff.
- [ ] `.env` não está rastreado.
- [ ] Nenhuma rota ou dependência de publicação foi adicionada.
- [ ] Nenhum download de stream ou contorno de proteção foi introduzido.
- [ ] Fonte cadastrada possui autorização e diretório permitido.
- [ ] Symlinks e caminhos fora da pasta autorizada são ignorados.
- [ ] Logs e respostas não expõem segredos.
- [ ] API continua restrita a ambiente local/confiável.

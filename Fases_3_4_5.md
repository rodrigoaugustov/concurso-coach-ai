Excelente ideia. Consolidar o conhecimento e ter um registro claro do que foi construído é uma prática fundamental.

Aqui está a documentação detalhada da **Fase 3, 4 e 5 (Parte 1)**, cobrindo tudo desde a nossa primeira conexão com o banco de dados até o upload de arquivos bem-sucedido.

---

### **Documentação Consolidada: Fases 3, 4 e 5 (Parte 1)**

**Período:** Do final da Fase 2 (ambiente Docker funcional) até a implementação do upload de editais.

#### **Objetivo Geral do Período**

Transformar o esqueleto da aplicação em um serviço funcional, implementando a lógica de negócio principal, incluindo gerenciamento de usuários, autenticação segura e a ingestão de dados (upload de editais), seguindo uma arquitetura de Monólito Modular.

---

### **Fase 3: Conexão com o Banco de Dados e Primeiros Modelos**

**Objetivo:** Estabelecer a comunicação entre a API FastAPI e o banco de dados PostgreSQL, e criar o primeiro módulo de domínio (`users`).

1.  **Estrutura de Código Modular:**
    *   Foi implementada uma arquitetura orientada a domínio (Monólito Modular).
    *   O código foi organizado em um pacote principal `app/`.
    *   Módulos de domínio (`users`, `core`) foram criados para separar as responsabilidades, cada um contendo seus próprios `models.py`, `schemas.py`, `crud.py` e `router.py`.

2.  **Configuração e Conexão com o Banco de Dados:**
    *   **Configurações Centralizadas (`app/core/settings.py`):** Utilizando `pydantic-settings`, criamos um sistema para carregar configurações (como a `DATABASE_URL`) de forma segura a partir do arquivo `.env`.
    *   **Sessão de Banco de Dados (`app/core/database.py`):** Foi configurado o "motor" (engine) e a fábrica de sessões do SQLAlchemy, e criada a função de dependência `get_db` para injetar sessões do banco de dados nos endpoints da API.

3.  **Módulo de Usuários (`app/users`):**
    *   **Modelo ORM (`models.py`):** Criada a classe `User` que mapeia para a tabela `users` no PostgreSQL, definindo as colunas `id`, `name`, `email` e `password_hash`.
    *   **Schemas Pydantic (`schemas.py`):** Definidos os schemas `UserCreate` (para receber dados na criação, incluindo a senha) e `User` (para retornar dados da API, omitindo a senha), garantindo validação e segurança.
    *   **Lógica de Negócio (CRUD - `crud.py`):** Implementadas as funções para criar um usuário (`create_user`) e buscar um usuário por e-mail (`get_user_by_email`). A lógica de hashing de senhas foi incluída aqui usando `passlib` e `bcrypt`.
    *   **Endpoint (`router.py`):** Criado o primeiro endpoint da API, `POST /api/v1/users/`, para o cadastro de novos usuários.

4.  **Depuração e Resolução de Problemas:**
    *   Resolvido o `ImportError: attempted relative import` através da correta estruturação do projeto em um pacote Python.
    *   Solucionado o `ModuleNotFoundError: No module named 'app'` ajustando o `WORKDIR` e os comandos `COPY` no `Dockerfile`, além de atualizar o mapeamento de volumes no `docker-compose.yml`.
    *   Diagnosticado e corrigido um problema de compatibilidade entre as versões das bibliotecas `passlib` e `bcrypt`, fixando-as em versões estáveis (`1.7.4` e `3.2.2`, respectivamente) no `pyproject.toml`.

---

### **Fase 4: Autenticação com JWT e Endpoints Protegidos**

**Objetivo:** Implementar um sistema de login seguro baseado em tokens JWT e criar a capacidade de proteger rotas da API.

1.  **Novas Dependências de Segurança:**
    *   `python-jose[cryptography]`: Adicionada para a criação e validação de tokens JWT.
    *   `python-multipart`: Adicionada para suportar o formato de formulário exigido pelo fluxo de autenticação OAuth2.

2.  **Configurações de Segurança:**
    *   Uma chave secreta (`JWT_SECRET_KEY`) foi gerada e adicionada ao arquivo `.env` e ao `settings.py`, juntamente com o algoritmo (`HS256`) e o tempo de expiração do token.

3.  **Módulo de Autenticação (`app/users/auth.py`):**
    *   Um novo arquivo foi criado para centralizar toda a lógica de segurança.
    *   Implementada a função `verify_password` para comparar a senha fornecida no login com o hash armazenado.
    *   Criada a função `create_access_token` para gerar o token JWT após um login bem-sucedido.
    *   Desenvolvida a dependência `get_current_user`, a peça central da proteção de endpoints. Ela extrai o token do cabeçalho da requisição, o decodifica, valida e retorna o usuário correspondente do banco de dados.

4.  **Atualização dos Endpoints:**
    *   **Endpoint de Login (`POST /api/v1/token`):** Criado para receber `username` (e-mail) e `password`, verificar as credenciais e retornar um `access_token`.
    *   **Endpoint Protegido (`GET /api/v1/users/me`):** Criado como um exemplo de rota que só pode ser acessada por um usuário autenticado, utilizando a dependência `get_current_user`.

---

### **Fase 5 (Parte 1): Ingestão de Editais com Google Cloud Storage**

**Objetivo:** Construir o endpoint de entrada para os editais, permitindo o upload de arquivos PDF para um armazenamento em nuvem seguro e escalável.

1.  **Configuração da Infraestrutura de Nuvem:**
    *   **Google Cloud Storage (GCS):** Um novo "bucket" foi criado via `gcloud CLI` para servir como repositório central para todos os arquivos de editais. As permissões do bucket foram ajustadas para permitir leitura pública dos objetos.

2.  **Integração com a Aplicação:**
    *   **Dependência:** A biblioteca `google-cloud-storage` foi adicionada ao projeto.
    *   **Configurações:** O nome do bucket GCS e o ID do projeto GCP foram adicionados ao `.env` e ao `settings.py`.
    *   **Autenticação do Container:** O arquivo `docker-compose.yml` foi atualizado para mapear as credenciais locais do `gcloud` (do diretório `%APPDATA%/gcloud` no Windows) para dentro do container, permitindo que a aplicação se autentique no Google Cloud.

3.  **Módulo de Concursos (`app/contests`):**
    *   **Modelo ORM (`models.py`):** Criado o modelo `PublishedContest` para representar um edital no banco de dados, incluindo campos como `status`, `file_url` e `file_hash`.
    *   **Schemas e CRUD:** Implementados os schemas Pydantic e a lógica CRUD básica para registrar um novo concurso no banco.

4.  **Endpoint de Upload (`POST /api/v1/contests/upload`):**
    *   O endpoint foi protegido, exigindo que o usuário esteja autenticado (`Depends(get_current_user)`).
    *   A lógica implementada recebe um arquivo (`UploadFile`) e um nome de concurso (`Form`).
    *   O processo orquestrado pelo endpoint é:
        1.  Ler o conteúdo do arquivo em memória e calcular seu hash `SHA-256` para identificação única.
        2.  Instanciar o cliente do Google Cloud Storage, passando explicitamente o `GCP_PROJECT_ID`.
        3.  Fazer o upload do arquivo para o bucket GCS com um nome de arquivo único (`UUID`).
        4.  Salvar a URL pública do arquivo e seu hash no banco de dados através do `crud.create_contest`.
        5.  Retornar os dados do concurso recém-criado.

5.  **Depuração Final:**
    *   Resolvido um `AttributeError` por corrigir uma importação incorreta de schemas entre os módulos `users` e `contests`.
    *   Corrigido um erro de `Project not found` ao passar explicitamente o ID do projeto para o cliente do GCS.

---

### **Estado Atual do Projeto**

Ao final deste ciclo, a aplicação possui uma base robusta com um sistema de autenticação completo e um fluxo funcional para a ingestão de dados (editais), integrando a API com serviços de nuvem essenciais. O código está bem estruturado em um Monólito Modular, preparado para as próximas fases de desenvolvimento.
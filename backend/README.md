# Concurso Coach AI Backend

Este é o backend para o Concurso Coach AI, uma aplicação para auxiliar nos estudos para concursos públicos.

## Instalação

1. Crie um ambiente virtual:

   ```bash
   uv venv
   ```

2. Ative o ambiente virtual:

   - No Windows:
     ```bash
     .venv\Scripts\Activate.ps1
     ```
   - No macOS e Linux:
     ```bash
     source .venv/bin/activate
     ```

3. Instale as dependências:

   ```bash
   uv pip install -r requirements.txt
   ```

## Como Rodar

Para iniciar o servidor de desenvolvimento, execute o seguinte comando:

```bash
uvicorn main:app --reload
```

O servidor estará disponível em `http://127.0.0.1:8000`.

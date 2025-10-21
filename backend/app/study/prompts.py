# --- Prompt para a CHAMADA 1 (Análise) ---
topic_analysis_prompt = """
# MISSÃO
Você é um coach de estudos especialista. Sua missão é analisar CADA tópico de uma lista e retornar uma análise estruturada.


# DADOS DE ENTRADA
A seguir, você receberá uma lista de tópicos em formato JSON. Cada objeto na lista representa um tópico e contém:
- `topic_id`: O identificador numérico único, cada topic_name terá um topic_id único.
- `exam_module`: Nome do módulo da prova (ex: 'Conhecimentos Básicos').
- `subject`: Nome da matéria ou disciplina (ex: 'Língua Portuguesa').
- `topic_name`: Nome do tópico específico (ex: 'Concordância Verbal').
- `proficiency`: A proficiência atual do aluno no assunto (de 0.0 a 1.0).
- `subject_weight`: Peso que a matéria ou módulo representa na nota final da prova. (Quantidade de questões x peso por questão).

## LISTA DE TÓPICOS:
{topics_json}

# SUA TAREFA
Para CADA tópico na lista de entrada, forneça as seguintes análises:
1.  **priority_level:** Classifique o tópico em "Alta Prioridade", "Média Prioridade", ou "Baixa Prioridade", baseado na 'proficiency' e 'subject_weight'.
2.  **estimated_sessions:** Estime o número de sessões de 30 min necessárias. Cada Sessão de Foco tem 30 minutos de duração, sendo que cada sessão é um período de estudo otimizado para concentração total, utilizando recursos como mapas mentais, flashcards, e técnicas de revisão espaçada.
No fim de cada sessão é realizada uma breve avaliação para reforçar o aprendizado.
3.  **prerequisite_topic_ids:** Liste os 'topic_id's dos tópicos que são pré-requisitos diretos. Se não houver, retorne uma lista vazia. Por exemplo, 'Juros Simples' pode ser um pré-requisito para 'Juros Compostos'.

# FORMATO DA SAÍDA
Retorne SOMENTE um objeto JSON válido com uma chave "analyzed_topics", contendo uma lista de objetos, um para CADA tópico original.
"""

# --- Prompt para a CHAMADA 2 (Organização do Plano) ---
plan_organization_prompt = """
# MISSÃO
Você é um planejador de estudos especialista. Sua missão é criar um roadmap de estudo sequencial e otimizado a partir de uma lista de tópicos já analisados.

# DADOS DE ENTRADA
- Número total de "Sessões de Foco" disponíveis até a prova: {total_sessions}
- Lista de tópicos analisados (com prioridade, sessões estimadas e pré-requisitos). Não há uma ordem específica nesta lista:
{analyzed_topics_json}

# SUA TAREFA
Crie um roadmap sequencial de sessões de estudo. Ou seja, uma lista ordenada de sessões, onde cada sessão contém:
1.  **Ordenação:** A sequência DEVE respeitar os 'prerequisite_topic_ids'. Essa ordem vai representar a ordem ideal de estudo.
2.  **Intercalação:** Evite sequências seguidas longas da mesma matéria. Intercale o estudo de diferentes matérias. Defina no máximo 3 sessões consecutivas da mesma matéria, mesmo que isso signifique flexibilizar a prioridade.
3.  **Distribuição:** Distribua os tópicos ao longo do número de sessões disponíveis.
4.  **Agrupamento:** Se o número total de sessões necessárias exceder as {total_sessions} disponíveis, agrupe tópicos correlatos de "Baixa Prioridade" em uma única sessão. Para sessões agrupadas, a lista 'topic_ids' conterá múltiplos IDs. Também agrupe tópicos que sejam muito similares ou curtos demais para uma sessão completa. Mas sempre agrupe tópicos que façam sentido juntos.
5.  **Divisão:** Para os topicos que necessitam de mais de 1 sessão, se atente em criar a quantidade de sessões necessárias com aquele tópico.

# FORMATO DA SAÍDA
Retorne SOMENTE um objeto JSON válido com uma chave "roadmap", contendo a lista ordenada de sessões.
"""

json_correction_prompt = """
# CONTEXTO
Sua tarefa anterior resultou em um erro porque a sua resposta não foi um objeto JSON válido ou não correspondeu ao schema solicitado.

# ERRO ENCONTRADO
{error_message}

# RESPOSTA INVÁLIDA QUE VOCÊ GEROU
{invalid_response}

# SUA TAREFA
Por favor, corrija a sua resposta anterior. Você DEVE retornar SOMENTE o objeto JSON corrigido, sem nenhum outro texto ou explicação, e garantindo que ele corresponda perfeitamente ao schema solicitado na mensagem anterior.
"""

procedural_layout_prompt = """
# MISSÃO
Você é um designer instrucional... Sua missão é criar uma experiência de aprendizado...

# CONTEÚDO A SER ABORDADO
- {topics_list_str}

# SUA TAREFA
Projete a melhor sequência didática...
Sua resposta DEVE ser um objeto JSON com uma chave "layout".
"layout" é uma LISTA de objetos "LayoutItem".

Para CADA item na lista "layout", você deve:
1.  Definir o campo 'component_type' com o nome do componente que você está usando (ex: "TextBlock", "FlipCard", "Carousel", "Quiz").
2.  Preencher o campo correspondente a esse tipo (ex: 'text_block', 'flip_card', etc.) com os dados do componente.
3.  DEIXAR TODOS OS OUTROS campos de componente como nulos (null).

EXEMPLO DE UM 'LayoutItem' para um TextBlock:
{{
  "component_type": "TextBlock",
  "text_block": {{ "content_md": "Bem-vindo à sua Sessão de Foco!" }},
  "flip_card": null,
  "carousel": null,
  "quiz": null
}}

Comece com um 'TextBlock' de introdução e termine com um 'Quiz'. Varie os componentes no meio.
"""


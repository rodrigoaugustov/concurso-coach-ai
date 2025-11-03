# Guided Lesson API

Este módulo fornece endpoints para gerenciar sessões de aula guiada com um agente conversacional que atua como professor. O agente conduz lições interativas baseadas nos tópicos de estudo do usuário.

## Arquitetura

O sistema de aulas guiadas é composto por:

- **Agent**: IA conversacional baseada no Gemini 2.5 Flash que atua como professor
- **Session Management**: Gerenciamento de contexto e histórico de conversas
- **Database Storage**: Persistência do histórico de mensagens

## Endpoints

### 1. Iniciar Aula Guiada

```http
POST /guided-lesson/start
```

Inicia uma nova sessão de aula guiada com base nos tópicos de uma sessão de estudo.

#### Request Body

```json
{
  "session_id": 123,
  "session_number": 1,
  "summary": "Sessão sobre direito constitucional",
  "priority_level": "high",
  "priority_reason": "Tópico com baixa proficiência",
  "topics": [
    {
      "id": 1,
      "exam_module": "Direito Constitucional",
      "subject": "Princípios Fundamentais",
      "topic": "Fundamentos da República"
    },
    {
      "id": 2,
      "exam_module": "Direito Constitucional",
      "subject": "Direitos e Garantias",
      "topic": "Direitos Individuais"
    }
  ]
}
```

#### Response

```json
{
  "session_id": 123,
  "message": "Mensagem inicial do professor em formato JSON"
}
```

#### Códigos de Status
- `201 Created`: Sessão iniciada com sucesso
- `401 Unauthorized`: Usuário não autenticado
- `422 Unprocessable Entity`: Dados inválidos

### 2. Enviar Mensagem na Aula

```http
POST /guided-lesson/{session_id}/chat
```

Envia uma mensagem do usuário e recebe a resposta do agente professor.

#### Path Parameters
- `session_id` (int): ID da sessão de aula guiada

#### Request Body

```json
{
  "content": "Pode explicar melhor os princípios fundamentais?",
  "session_contents": {
    "session_id": 123,
    "session_number": 1,
    "summary": "Sessão sobre direito constitucional",
    "priority_level": "high",
    "priority_reason": "Tópico com baixa proficiência",
    "topics": [
      {
        "id": 1,
        "exam_module": "Direito Constitucional",
        "subject": "Princípios Fundamentais",
        "topic": "Fundamentos da República"
      }
    ]
  }
}
```

#### Response

```json
{
  "agent_response": "Resposta do professor em formato JSON",
  "history": [
    {
      "id": 1,
      "sender_type": "AI",
      "content": "Mensagem inicial do professor",
      "timestamp": "2025-11-02T22:14:00Z",
      "session_id": 123
    },
    {
      "id": 2,
      "sender_type": "USER",
      "content": "Pode explicar melhor os princípios fundamentais?",
      "timestamp": "2025-11-02T22:15:00Z",
      "session_id": 123
    },
    {
      "id": 3,
      "sender_type": "AI",
      "content": "Resposta do professor",
      "timestamp": "2025-11-02T22:15:30Z",
      "session_id": 123
    }
  ]
}
```

## Fluxo de Integração Frontend

Para integrar o frontend com a API de aulas guiadas, siga este fluxo:

### Passo 1: Obter Próxima Sessão de Estudo

Antes de iniciar uma aula guiada, obtenha os dados da próxima sessão de estudo:

```javascript
// Chama o endpoint de sessão de estudo
const studyResponse = await fetch('/study/next-session', {
  method: 'GET',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  }
});

const { main_session } = await studyResponse.json();
```

### Passo 2: Iniciar Aula Guiada

Use os dados da sessão como payload para iniciar a aula:

```javascript
// Inicia a aula guiada usando os dados da sessão
const lessonResponse = await fetch('/guided-lesson/start', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify(main_session) // Usa diretamente os dados da sessão
});

const { session_id, message } = await lessonResponse.json();

// O message vem em formato JSON, precisa fazer parse
const initialMessage = JSON.parse(message);
```

### Passo 3: Gerenciar Conversa

```javascript
// Função para enviar mensagem do usuário
async function sendUserMessage(sessionId, userMessage, sessionContents) {
  const response = await fetch(`/guided-lesson/${sessionId}/chat`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      content: userMessage,
      session_contents: sessionContents // Mantém os dados originais da sessão
    })
  });

  const { agent_response, history } = await response.json();
  
  // O agent_response vem em formato JSON, precisa fazer parse
  const parsedResponse = JSON.parse(agent_response);
  
  return { parsedResponse, history };
}
```

### Exemplo Completo de Integração

```javascript
class GuidedLessonManager {
  constructor(authToken) {
    this.token = authToken;
    this.sessionId = null;
    this.sessionContents = null;
  }

  async startGuidedLesson() {
    try {
      // 1. Obter próxima sessão de estudo
      const studyResponse = await fetch('/study/next-session', {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${this.token}`,
          'Content-Type': 'application/json'
        }
      });
      
      const { main_session } = await studyResponse.json();
      this.sessionContents = main_session;

      // 2. Iniciar aula guiada
      const lessonResponse = await fetch('/guided-lesson/start', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${this.token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(main_session)
      });

      const { session_id, message } = await lessonResponse.json();
      this.sessionId = session_id;
      
      // Parse da mensagem inicial
      const initialMessage = JSON.parse(message);
      
      return {
        sessionId: session_id,
        initialMessage: initialMessage
      };
    } catch (error) {
      console.error('Erro ao iniciar aula guiada:', error);
      throw error;
    }
  }

  async sendMessage(userMessage) {
    if (!this.sessionId || !this.sessionContents) {
      throw new Error('Sessão não iniciada');
    }

    try {
      const response = await fetch(`/guided-lesson/${this.sessionId}/chat`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${this.token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          content: userMessage,
          session_contents: this.sessionContents
        })
      });

      const { agent_response, history } = await response.json();
      
      return {
        agentResponse: JSON.parse(agent_response),
        conversationHistory: history
      };
    } catch (error) {
      console.error('Erro ao enviar mensagem:', error);
      throw error;
    }
  }
}

// Uso da classe
const lessonManager = new GuidedLessonManager(userToken);

// Iniciar aula
const { sessionId, initialMessage } = await lessonManager.startGuidedLesson();
console.log('Aula iniciada:', initialMessage);

// Enviar mensagens
const { agentResponse, conversationHistory } = await lessonManager.sendMessage('Oi professor!');
console.log('Resposta do professor:', agentResponse);
```

## Notas Importantes

1. **Autenticação**: Todos os endpoints requerem autenticação via JWT token
2. **Formato JSON**: As mensagens do agente são retornadas em formato JSON string e precisam ser parseadas
3. **Contexto da Sessão**: O `session_contents` deve ser mantido e enviado em todas as mensagens para preservar o contexto
4. **Session ID**: O ID da sessão é usado para manter a continuidade da conversa e acessar o histórico
5. **Histórico**: O histórico completo é retornado a cada mensagem, incluindo timestamps e tipos de remetente

## Estrutura dos Dados

### SenderType
- `USER`: Mensagem enviada pelo usuário
- `AI`: Mensagem enviada pelo agente professor

### Priority Level
- `high`: Alta prioridade
- `medium`: Média prioridade  
- `low`: Baixa prioridade

### Tópicos (ProgrammaticContent)
Cada tópico contém:
- `id`: Identificador único
- `exam_module`: Módulo do exame (ex: "Direito Constitucional")
- `subject`: Matéria específica (ex: "Princípios Fundamentais")
- `topic`: Tópico detalhado (ex: "Fundamentos da República")
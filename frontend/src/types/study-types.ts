// ===================================================================
// TIPOS PARA A GERAÇÃO DE LAYOUT PROCEDURAL DA SESSÃO DE ESTUDO
// Este arquivo espelha a estrutura do `ui_schemas.py` do backend.
// ===================================================================

// --- Definições dos Componentes Individuais ---

export interface TextBlock {
  content_md: string;
}

export interface FlipCard {
  front_text: string;
  back_text: string;
}

export interface CarouselItem {
  title: string;
  content: string;
}

export interface Carousel {
  items: CarouselItem[];
}

export interface QuizQuestion {
  question: string;
  options: string[];
  correct_answer: string;
  explanation: string;
}

export interface Quiz {
  questions: QuizQuestion[];
}


// ===================================================================
// Definição do "Container" LayoutItem e do Schema Principal
// ===================================================================

// Define os nomes de componentes válidos como um tipo literal
export type ComponentType = 'TextBlock' | 'FlipCard' | 'Carousel' | 'Quiz';

/**
 * Representa um único item no layout da aula.
 * Contém o tipo do componente e a carga útil de dados opcional correspondente.
 */
export interface LayoutItem {
  component_type: ComponentType;
  text_block?: TextBlock;
  flip_card?: FlipCard;
  carousel?: Carousel;
  quiz?: Quiz;
}

/**
 * A estrutura raiz da resposta da API para o layout procedural.
 * Contém a lista ordenada de componentes que constroem a aula.
 */
export interface ProceduralLayout {
  layout: LayoutItem[];
}


// ===================================================================
// TIPOS ADICIONAIS PARA O FLUXO DE ESTUDO (do dashboard, etc.)
// ===================================================================

// --- Tipos para Autenticação e Usuário ---
export interface User {
    id: number;
    name: string;
}

// --- Tipos para Concursos e Estrutura ---
export interface Contest {
    name: string;
}

export interface ContestRole {
    job_title: string;
    contest: Contest;
}

export interface UserSubscription {
  id: number;
  user_id: number;
  contest_role_id: number;
  role: ContestRole;
}

// --- Tipos para o Plano de Estudos e Sessões ---
export interface ProgrammaticContent {
    id: number;
    exam_module: string;
    subject: string;
    topic: string;
}

export interface StudySession {
    id: number;
    session_number: number;
    summary: string | null;
    priority_level: string;
    priority_reason: string | null;
    topics: ProgrammaticContent[];
    guided_lesson_started?: boolean; // Optional for backward compatibility
}

export interface NextSessionResponse {
    main_session: StudySession;
    review_session: StudySession | null;
}

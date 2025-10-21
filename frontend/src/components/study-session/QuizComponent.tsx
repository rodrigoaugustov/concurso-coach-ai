'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/Button';

// Tipos importados do nosso arquivo central de tipos
import type { QuizQuestion } from '@/types/study-types';

interface QuizProps {
  questions: QuizQuestion[];
}

export default function QuizComponent({ questions }: QuizProps) {
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
  const [selectedAnswer, setSelectedAnswer] = useState<string | null>(null);
  const [showResult, setShowResult] = useState(false);
  const [score, setScore] = useState(0);

  // Validação para evitar crash se a IA não retornar perguntas
  if (!questions || questions.length === 0) {
    return (
        <div className="p-8 bg-surface rounded-xl shadow-sm border border-border-color text-center">
            <p className="text-gray-500">O quiz para esta sessão não pôde ser carregado.</p>
        </div>
    );
  }

  const isQuizFinished = currentQuestionIndex >= questions.length;
  const currentQuestion = questions[currentQuestionIndex];
  
  const handleAnswerSelect = (option: string) => {
    if (showResult) return;
    setSelectedAnswer(option);
  };

  const handleCheckAnswer = () => {
    if (!selectedAnswer) return;
    if (selectedAnswer === currentQuestion.correct_answer) {
      setScore(prev => prev + 1);
    }
    setShowResult(true);
  };

  const handleNextQuestion = () => {
    setShowResult(false);
    setSelectedAnswer(null);
    setCurrentQuestionIndex(prev => prev + 1);
  };

  if (isQuizFinished) {
    return (
        <div className="bg-surface p-8 rounded-xl shadow-lg text-center border">
            <h3 className="text-2xl font-bold text-gray-900">Quiz Finalizado!</h3>
            <p className="mt-4 text-lg text-gray-700">
                Sua pontuação: <span className="font-bold text-brand">{score} de {questions.length}</span> acertos.
            </p>
            <div className="mt-6">
                <Button 
                  onClick={() => alert("Finalizar a Sessão de Estudo!")}
                  className="bg-green-600 hover:bg-green-700"
                >
                    Concluir Sessão
                </Button>
            </div>
        </div>
    );
  }

  return (
    <div className="bg-surface p-8 rounded-xl shadow-md border">
      <p className="text-sm font-semibold text-brand">
        Questão {currentQuestionIndex + 1} de {questions.length}
      </p>
      <h3 className="mt-2 text-2xl font-bold text-gray-900">{currentQuestion.question}</h3>
      
      <div className="mt-8 space-y-4">
        {currentQuestion.options.map((option, index) => {
          const isSelected = selectedAnswer === option;
          let stateClasses = 'border-gray-300 bg-white hover:bg-gray-50 text-gray-800'; // Padrão
          
          if (showResult) {
            if (option === currentQuestion.correct_answer) {
              stateClasses = 'border-green-500 bg-green-50 text-green-800'; // Resposta correta
            } else if (isSelected) {
              stateClasses = 'border-red-500 bg-red-50 text-red-800'; // Errada selecionada
            } else {
              stateClasses = 'border-gray-200 bg-gray-50 text-gray-500'; // Inativa após resultado
            }
          } else if (isSelected) {
            stateClasses = 'border-indigo-500 bg-indigo-50 ring-2 ring-indigo-500 text-indigo-800'; // Selecionada
          }

          return (
            <button
              key={index}
              onClick={() => handleAnswerSelect(option)}
              disabled={showResult}
              className={`w-full p-4 text-left rounded-lg border-2 font-medium transition-all duration-200 ${stateClasses}`}
            >
              {option}
            </button>
          );
        })}
      </div>

      {showResult && (
        <div className={`mt-6 p-4 rounded-lg text-base ${selectedAnswer === currentQuestion.correct_answer ? 'bg-green-50 text-green-800 border border-green-200' : 'bg-red-50 text-red-800 border border-red-200'}`}>
          <p className="font-bold">{selectedAnswer === currentQuestion.correct_answer ? 'Resposta Correta!' : 'Resposta Incorreta.'}</p>
          <p className="mt-2 text-gray-700">{currentQuestion.explanation}</p>
        </div>
      )}

      <div className="mt-8 flex justify-end">
        {showResult ? (
          <Button onClick={handleNextQuestion} className="bg-brand hover:bg-indigo-700">
            {currentQuestionIndex === questions.length - 1 ? 'Ver Resultado Final' : 'Próxima Questão'}
          </Button>
        ) : (
          <Button onClick={handleCheckAnswer} disabled={!selectedAnswer} className="bg-brand hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed">
            Verificar Resposta
          </Button>
        )}
      </div>
    </div>
  );
}
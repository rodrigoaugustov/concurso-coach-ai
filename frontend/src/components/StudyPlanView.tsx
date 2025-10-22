'use client';

import { useRouter } from 'next/navigation';
import { Button } from './ui/Button';
import type { NextSessionResponse } from '@/types/study-types';

interface StudyPlanViewProps {
  onGeneratePlan: () => void;
  isGeneratingPlan: boolean;
  nextSessionData: NextSessionResponse | null;
}

export default function StudyPlanView({ onGeneratePlan, isGeneratingPlan, nextSessionData }: StudyPlanViewProps) {
    const router = useRouter();

    const handleStartSession = () => {
        if (!nextSessionData?.main_session?.id) return;
        
        const sessionId = nextSessionData.main_session.id;
        const topicIds = nextSessionData.main_session.topics.map(t => t.id);

        if (topicIds.length === 0) return;

        router.push(`/study-session/${sessionId}?topic_ids=${topicIds.join(',')}`);
    };

    // --- RENDERIZAÇÃO CONDICIONAL DENTRO DO COMPONENTE ---
    
    // 1. Caso: O plano precisa ser gerado
    if (!nextSessionData) {
        return (
            <div className="text-center p-8 bg-white rounded-xl shadow-lg">
                <h2 className="text-2xl font-bold">Pronto para começar?</h2>
                <p className="mt-2 text-gray-600">Sua inscrição foi feita. Agora, vamos usar a IA para criar seu plano de estudos personalizado.</p>
                <Button onClick={onGeneratePlan} disabled={isGeneratingPlan} className="mt-6 text-lg py-3">
                    {isGeneratingPlan ? 'Gerando Plano com a IA...' : 'Gerar Meu Plano de Estudos'}
                </Button>
            </div>
        );
    }
    
    const { main_session, review_session } = nextSessionData;

    // 2. Caso: O plano existe e está pronto
    return (
        <div className="bg-surface p-8 rounded-xl shadow-md space-y-8">
            <div className="text-center p-4 bg-indigo-50 rounded-lg shadow-sm">
                <h2 className="text-md font-medium text-indigo-700">Sua Próxima Sessão de Foco</h2>
                <p className="mt-1 text-4xl font-extrabold tracking-tight text-indigo-900">
                    Sessão #{main_session.session_number}
                </p>
            </div>

            <div className="p-6 border border-gray-200 rounded-lg bg-white shadow-sm">
                <h3 className="font-semibold text-lg text-gray-900">Tópico Principal</h3>
                <p className="mt-2 text-gray-700">{main_session.summary || 'A IA irá gerar um resumo detalhado para você.'}</p>
                <ul className="mt-3 space-y-1 text-sm text-gray-700">
                    {main_session.topics.map(t => (
                        <li key={t.id} className="pl-5 relative before:content-['•'] before:absolute before:left-0 before:text-brand">
                            {t.topic}
                        </li>
                    ))}
                </ul>
                <p className="mt-3 text-xs text-gray-500 italic">Prioridade: {main_session.priority_level} - {main_session.priority_reason}</p>
            </div>
            
            {review_session && (
                <div className="p-6 bg-orange-50 border border-orange-200 rounded-lg animate-fade-in shadow-sm">
                    <h3 className="font-semibold text-lg text-orange-800">Revisão Rápida Recomendada</h3>
                    <ul className="mt-3 space-y-1 text-sm text-orange-700">
                        {review_session.topics.map(t => (
                            <li key={t.id} className="pl-5 relative before:content-['•'] before:absolute before:left-0 before:text-orange-600">
                                {t.topic}
                            </li>
                        ))}
                    </ul>
                </div>
            )}
            
            <Button onClick={handleStartSession} disabled={!main_session?.id} className="w-full py-3 text-lg bg-indigo-600 hover:bg-indigo-700 text-white font-bold rounded-md shadow-lg">
                Iniciar Sessão de Estudo
            </Button>
        </div>
    );
}
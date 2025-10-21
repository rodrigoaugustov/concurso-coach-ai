'use client';

import StudyPlanView from './StudyPlanView';
import { Button } from './ui/Button';
import type { NextSessionResponse } from '@/types/study-types';

interface StudyPlanManagerProps {
  // A prop 'userContestId' foi removida pois não era usada aqui.
  // Ela é usada no DashboardPage para a chamada de 'generate-plan'.
  nextSessionData: NextSessionResponse | null;
  onGeneratePlan: () => void;
  isGeneratingPlan: boolean;
  isLoading: boolean;
}

export default function StudyPlanManager({
  nextSessionData,
  onGeneratePlan,
  isGeneratingPlan,
  isLoading
}: StudyPlanManagerProps) {
    if (isLoading) {
        return (
            <div className="text-center p-8 bg-surface rounded-xl shadow-md">
                <h2 className="text-xl font-semibold animate-pulse text-brand">Verificando seu plano de estudos...</h2>
            </div>
        );
    }
    
    if (isGeneratingPlan) {
        return (
            <div className="text-center p-8 bg-surface rounded-xl shadow-md">
                <h2 className="text-xl font-semibold animate-pulse text-brand">
                    Gerando seu plano com a IA...
                </h2>
                <p className="mt-2 text-secondary">(Isso pode levar até um minuto, por favor, não feche esta página)</p>
            </div>
        );
    }

    if (!nextSessionData) {
        return (
            <div className="text-center p-8 bg-surface rounded-xl shadow-md">
                <h2 className="text-2xl font-bold text-primary">Pronto para começar?</h2>
                <p className="mt-2 text-secondary">Sua inscrição foi feita. Agora, vamos criar seu plano de estudos personalizado.</p>
                <Button onClick={onGeneratePlan} className="mt-6 text-lg py-3">
                    Gerar Meu Plano de Estudos
                </Button>
            </div>
        );
    }
    
    // --- CORREÇÃO PRINCIPAL ---
    // Agora estamos passando TODAS as props necessárias para o StudyPlanView.
    return <StudyPlanView 
              nextSessionData={nextSessionData} 
              onGeneratePlan={onGeneratePlan}
              isGeneratingPlan={isGeneratingPlan}
            />;
}
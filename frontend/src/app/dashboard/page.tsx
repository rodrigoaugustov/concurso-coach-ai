'use client';

// CORREÇÃO: 'useEffect' foi removido da importação, pois não é mais usado aqui.
import { useMemo, useState } from 'react'; 
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import OnboardingFlow from '@/components/OnboardingFlow';
import StudyPlanManager from '@/components/StudyPlanManager';
import PendingSelfAssessmentCTA from '@/components/PendingSelfAssessmentCTA';
import { Button } from '@/components/ui/Button';
import { useDashboardData } from '@/hooks/useDashboardData';
import { Select } from '@/components/ui/Select';
import UserMenu from '@/components/UserMenu';
import { ChevronDownIcon } from '@heroicons/react/20/solid';

export default function DashboardPage() {
  const router = useRouter();
  
  const { 
    user, 
    subscriptions, 
    pendingSelfAssessments,
    isLoading, 
    error, 
    activeSubscriptionId, 
    setActiveSubscriptionId,
    nextSession,
    fetchNextSession
  } = useDashboardData();
  
  const [isGeneratingPlan, setIsGeneratingPlan] = useState(false);
  const [showPlanSelect, setShowPlanSelect] = useState(false);

  // Mostra CTA apenas se a inscrição ATIVA estiver na lista de pendentes
  const activePendingAssessments = useMemo(() => {
    if (!activeSubscriptionId) return [] as typeof pendingSelfAssessments;
    return pendingSelfAssessments.filter(p => p.id === activeSubscriptionId);
  }, [pendingSelfAssessments, activeSubscriptionId]);

  const handleGeneratePlan = async () => {
    if (!activeSubscriptionId) return;
    
    setIsGeneratingPlan(true);
    const token = localStorage.getItem('accessToken');
    const apiUrl = process.env.NEXT_PUBLIC_API_URL;

    try {
      const response = await fetch(`${apiUrl}/study/user-contests/${activeSubscriptionId}/generate-plan`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` },
      });
      if (!response.ok) throw new Error("A IA falhou em gerar o plano. Tente novamente mais tarde.");
      
      if (token) {
        // Força a recarga dos dados da próxima sessão após o plano ser gerado
        await fetchNextSession(activeSubscriptionId, token);
      }

    } catch (err) {
      console.error(err);
      // TODO: Mostrar um erro para o usuário com um toast/alert
    } finally {
      setIsGeneratingPlan(false);
    }
  };
  
  const renderContent = () => {
    if (subscriptions.length === 0) {
      return <OnboardingFlow />;
    }
    if (activeSubscriptionId) {
      const hasPendingForActive = activePendingAssessments.length > 0;
      return (
        <>
          {/* CTA para autoavaliação pendente SOMENTE da inscrição ativa */}
          <PendingSelfAssessmentCTA 
            pendingAssessments={activePendingAssessments} 
            className="mb-6"
          />
          
          <StudyPlanManager 
            nextSessionData={nextSession}
            onGeneratePlan={handleGeneratePlan}
            isGeneratingPlan={isGeneratingPlan}
            isLoading={isLoading}
            hasPendingSelfAssessment={hasPendingForActive}
          />
        </>
      );
    }
    return (
      <>
        {/* Quando nenhuma inscrição ativa estiver selecionada, mantém a lista completa */}
        <PendingSelfAssessmentCTA 
          pendingAssessments={pendingSelfAssessments} 
          className="mb-6"
        />
        
        <p className="text-center text-gray-500 py-20">Selecione um plano de estudo para começar.</p>
      </>
    );
  };
  
  if (isLoading && !user) {
    return (
        <div className="flex items-center justify-center min-h-screen bg-gray-50">
            <p className="text-gray-500">Carregando seu painel...</p>
        </div>
    );
  }

  if (error) {
    return <div className="text-red-500 text-center p-8">Erro: {error}</div>;
  }
  
  return (
    <div className="min-h-screen bg-background">
      <header className="bg-surface shadow-sm sticky top-0 z-10 border-b border-gray-200">
        <div className="max-w-7xl mx-auto py-4 px-6 sm:px-8 lg:px-10 flex justify-between items-center">
          <div className="flex items-center">
            <h1 className="text-xl md:text-2xl font-bold text-gray-900">
              Olá, {user?.name}!
            </h1>
            {subscriptions.length > 0 && (
              <div className="relative ml-3">
                <button
                  className="flex items-center gap-1 text-sm font-medium text-gray-700 hover:text-gray-900"
                  onClick={() => setShowPlanSelect(!showPlanSelect)}
                >
                  <span className="hidden sm:inline">Seu Plano:</span>
                  <span className="font-semibold text-indigo-600">
                    {subscriptions.find(sub => sub.id === activeSubscriptionId)?.role.contest.name || 'Nenhum Plano'}
                  </span>
                  <ChevronDownIcon className="h-4 w-4 text-gray-500" />
                </button>
                {showPlanSelect && (
                  <div className="absolute left-0 mt-2 w-64 origin-top-left rounded-md shadow-lg bg-white ring-1 ring-black ring-opacity-5 focus:outline-none z-50">
                    <div className="py-1" role="menu" aria-orientation="vertical" aria-labelledby="plan-menu-button" tabIndex={-1}>
                      {subscriptions.map(sub => (
                        <button
                          key={sub.id}
                          onClick={() => {
                            setActiveSubscriptionId(sub.id);
                            setShowPlanSelect(false);
                          }}
                          className="block w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 hover:text-gray-900"
                          role="menuitem"
                          tabIndex={-1}
                        >
                          {`${sub.role.contest.name} (${sub.role.job_title})`}
                        </button>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Right Section: Actions */}
          <div className="flex items-center gap-4">
            <Link href="/onboarding/start" passHref className="ml-5">
                <Button variant="outline" className="!w-auto text-nowrap">Nova Inscrição</Button>
            </Link>
            <UserMenu />
          </div>
        </div>
      </header>
      <main>
        <div className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
          {renderContent()}
        </div>
      </main>
    </div>
  );
}

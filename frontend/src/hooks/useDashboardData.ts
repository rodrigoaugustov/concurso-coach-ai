'use client';

import { useEffect, useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import type { UserSubscription, NextSessionResponse, User } from '@/types/study-types';

export function useDashboardData() {
  const router = useRouter();
  
  // Estados de dados
  const [user, setUser] = useState<User | null>(null);
  const [subscriptions, setSubscriptions] = useState<UserSubscription[]>([]);
  const [pendingSelfAssessments, setPendingSelfAssessments] = useState<UserSubscription[]>([]);
  const [activeSubscriptionId, setActiveSubscriptionId] = useState<number | null>(null);
  const [nextSession, setNextSession] = useState<NextSessionResponse | null>(null);
  
  // Estados de controle da UI
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  // Usamos useCallback para memoizar a função e evitar recriações desnecessárias
  const fetchNextSession = useCallback(async (subId: number, token: string) => {
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL;
      const response = await fetch(`${apiUrl}/study/user-contests/${subId}/next-session`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      if (response.status === 404) {
        setNextSession(null); // Plano não gerado ou concluído
        return;
      }
      if (!response.ok) {
        throw new Error("Falha ao buscar a próxima sessão.");
      }
      
      const data = await response.json();
      setNextSession(data);
    } catch (err) {
      console.error("Erro em fetchNextSession:", err);
      // Mantemos o erro local, pois um erro aqui não é fatal para o dashboard inteiro
      setNextSession(null); 
    }
  }, []);

  // Função para buscar pending self-assessments
  const fetchPendingSelfAssessments = useCallback(async (token: string) => {
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL;
      const response = await fetch(`${apiUrl}/study/user-contests/pending-self-assessment`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      if (response.ok) {
        const data = await response.json();
        setPendingSelfAssessments(data);
      } else {
        console.error("Falha ao buscar pending self-assessments");
        setPendingSelfAssessments([]);
      }
    } catch (err) {
      console.error("Erro ao buscar pending self-assessments:", err);
      setPendingSelfAssessments([]);
    }
  }, []);

  // Efeito principal para buscar dados iniciais (usuário e inscrições)
  useEffect(() => {
    let isMounted = true;
    const token = localStorage.getItem('accessToken');
    if (!token) {
      router.push('/sign-in');
      return;
    }

    const fetchInitialData = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL;
        const headers = { 'Authorization': `Bearer ${token}` };
        
        const [userResponse, subsResponse] = await Promise.all([
          fetch(`${apiUrl}/me`, { headers }),
          fetch(`${apiUrl}/study/user-contests/`, { headers })
        ]);

        if (!userResponse.ok) throw new Error("Sessão inválida. Por favor, faça o login novamente.");
        
        if (isMounted) {
          const userData = await userResponse.json();
          setUser(userData);

          if (subsResponse.ok) {
            const subsData = await subsResponse.json();
            setSubscriptions(subsData);
            // Define a inscrição ativa se ainda não houver uma
            if (subsData.length > 0 && activeSubscriptionId === null) {
              const firstSubId = subsData[0].id;
              setActiveSubscriptionId(firstSubId);
              // Dispara a busca da próxima sessão para a inscrição recém-ativada
              fetchNextSession(firstSubId, token);
            }
            // Busca pending self-assessments sempre
            await fetchPendingSelfAssessments(token);
          }
        }
      } catch (err) {
        if (isMounted) {
          setError(err instanceof Error ? err.message : "Erro desconhecido ao carregar dados.");
          localStorage.removeItem('accessToken');
          router.push('/sign-in');
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    };
    
    fetchInitialData();

    return () => { isMounted = false; };
  }, [router, activeSubscriptionId, fetchNextSession, fetchPendingSelfAssessments]); // O hook agora reage à mudança de inscrição

  // Função para mudar a inscrição ativa e buscar os dados da nova sessão
  const handleSetActiveSubscriptionId = (id: number) => {
    setIsLoading(true);
    setNextSession(null); // Limpa a sessão antiga
    setActiveSubscriptionId(id);
    const token = localStorage.getItem('accessToken'); // Get token here
    if (token) {
      fetchNextSession(id, token); // Call fetchNextSession directly
    }
  };

  // Função para recarregar pending assessments (chamada após completar autoavaliação)
  const refreshPendingAssessments = useCallback(() => {
    const token = localStorage.getItem('accessToken');
    if (token) {
      fetchPendingSelfAssessments(token);
    }
  }, [fetchPendingSelfAssessments]);

  return { 
    user, 
    subscriptions, 
    pendingSelfAssessments,
    activeSubscriptionId, 
    setActiveSubscriptionId: handleSetActiveSubscriptionId, // Expõe a função segura
    nextSession,
    fetchNextSession, // Expõe para recarregar manualmente se necessário
    refreshPendingAssessments, // Nova função para recarregar pending assessments
    isLoading, 
    error 
  };
}
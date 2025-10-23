'use client';

import { useEffect, useLayoutEffect, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/Button';
import Link from 'next/link';

// Tipo para armazenar a proficiência de cada matéria
type ProficiencyState = {
  [subject: string]: number;
};

// Hook simples de debounce para submissão
function useDebouncedSubmit<T extends (...args: any[]) => Promise<void> | void>(
  submitFn: T,
  delayMs: number
) {
  const timerRef = useRef<NodeJS.Timeout | null>(null);
  return async (...args: Parameters<T>) => {
    if (timerRef.current) {
      clearTimeout(timerRef.current);
    }
    await new Promise<void>((resolve) => {
      timerRef.current = setTimeout(() => resolve(), delayMs);
    });
    await submitFn(...args);
  };
}

interface Props { initialId: string | null }

export default function ProficiencyClientPage({ initialId }: Props) {
  const router = useRouter();

  // Ref como fonte de verdade: não dispara re-render e não depende de hooks de URL
  const userContestIdRef = useRef<string | null>(null);

  const [subjects, setSubjects] = useState<string[]>([]);
  const [proficiencies, setProficiencies] = useState<ProficiencyState>({});
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [isDuplicateSubmission, setIsDuplicateSubmission] = useState(false);
  const [statusMessage, setStatusMessage] = useState('Carregando matérias...');
  const lastClickRef = useRef<number>(0);

  // Montagem: valida ID, fixa ref e estabiliza URL antes de qualquer render subsequente
  useLayoutEffect(() => {
    if (!initialId) {
      setError('ID da inscrição não encontrado. Por favor, comece o processo novamente.');
      setIsLoading(false);
      return;
    }
    userContestIdRef.current = initialId;
    // Estabiliza a URL mantendo o query param (sem scroll)
    router.replace(`/onboarding/proficiency?user_contest_id=${initialId}`, { scroll: false });
  }, [initialId, router]);

  // Busca das matérias usando o ID persistido em ref
  useEffect(() => {
    const id = userContestIdRef.current;
    if (!id) return;

    const fetchSubjects = async () => {
      try {
        const token = localStorage.getItem('accessToken');
        const apiUrl = process.env.NEXT_PUBLIC_API_URL;

        const response = await fetch(`${apiUrl}/study/user-contests/${id}/subjects`, {
          headers: { 'Authorization': `Bearer ${token}` },
        });

        if (!response.ok) {
          throw new Error('Falha ao buscar as matérias do concurso.');
        }

        const data = await response.json();
        setSubjects(data);
        
        const initialProficiencies = data.reduce((acc: ProficiencyState, subject: string) => {
          acc[subject] = 0.5; // Inicializa no meio
          return acc;
        }, {} as ProficiencyState);
        setProficiencies(initialProficiencies);

      } catch (err) {
        if (err instanceof Error) setError(err.message);
      } finally {
        setIsLoading(false);
      }
    };

    fetchSubjects();
  }, []);

  const handleProficiencyChange = (subject: string, value: number) => {
    setProficiencies(prev => ({ ...prev, [subject]: value }));
  };

  const submitCore = async (e: React.FormEvent) => {
    e.preventDefault();
    if (isSubmitting) return; // lock imediato

    setIsSubmitting(true);
    setError('');
    setIsDuplicateSubmission(false);

    const id = userContestIdRef.current;
    if (!id) {
      setError('ID da inscrição não encontrado.');
      setIsSubmitting(false);
      return;
    }

    try {
      const token = localStorage.getItem('accessToken');
      const apiUrl = process.env.NEXT_PUBLIC_API_URL;
      const headers = { 
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
      };
      
      setStatusMessage('Salvando sua avaliação...');
      const proficiencyPayload = {
          proficiencies: Object.entries(proficiencies).map(([subject, score]) => ({
              subject,
              score,
          })),
      };
      const proficiencyResponse = await fetch(`${apiUrl}/study/user-contests/${id}/proficiency`, {
          method: 'POST',
          headers: headers,
          body: JSON.stringify(proficiencyPayload),
      });

      if (proficiencyResponse.status === 409) {
        const errorData = await proficiencyResponse.json();
        setError(errorData.detail || 'Você já enviou sua autoavaliação para esta inscrição.');
        setIsDuplicateSubmission(true);
        setIsSubmitting(false);
        return;
      }

      if (!proficiencyResponse.ok) {
          throw new Error('Falha ao salvar sua autoavaliação.');
      }
      
      setStatusMessage('Gerando seu plano de estudos personalizado com a IA... (Isso pode levar até um minuto)');
      const planResponse = await fetch(`${apiUrl}/study/user-contests/${id}/generate-plan`, {
          method: 'POST',
          headers: headers,
          timeout: 300000,
      } as RequestInit);
      
      if (!planResponse.ok) {
          throw new Error('A IA falhou em gerar o plano. Você pode tentar novamente no dashboard.');
      }

      router.push('/dashboard');

    } catch (err) {
      if (err instanceof Error) setError(err.message);
    } finally {
      setIsSubmitting(false);
    }
  };

  if (isLoading) {
    return (
        <div className='flex items-center justify-center min-h-screen'>
            <p>{statusMessage}</p>
        </div>
    );
  }

  return (
    <div className='flex items-center justify-center min-h-screen bg-background py-12'>
      <div className='w-full max-w-2xl p-8 space-y-6 bg-surface rounded-xl shadow-md'>
        <div className='text-center'>
          <h1 className='text-3xl font-extrabold text-primary'>Autoavaliação de Conhecimento</h1>
          <p className='mt-2 text-md text-secondary'>Seja honesto! Isso é crucial para criarmos o melhor plano para você.</p>
        </div>
        
        {isDuplicateSubmission ? (
          <div className='text-center p-8 bg-amber-50 border border-amber-200 rounded-lg'>
            <div className='flex items-center justify-center mb-4'>
              <svg className='h-8 w-8 text-amber-400' viewBox='0 0 20 20' fill='currentColor'>
                <path fillRule='evenodd' d='M8.257 3.099c..' />
              </svg>
            </div>
            <h3 className='text-lg font-semibold text-amber-800 mb-2'>Autoavaliação Já Enviada</h3>
            <p className='text-amber-700 mb-4'>{error}</p>
            <p className='text-sm text-amber-600 mb-6'>
              Sua autoavaliação anterior ainda está válida. Você pode acessar seu plano de estudos no dashboard.
            </p>
            <Link href='/dashboard' passHref>
              <Button className='bg-amber-600 hover:bg-amber-700 text-white'>
                Voltar ao Dashboard
              </Button>
            </Link>
          </div>
        ) : isSubmitting ? (
             <div className='text-center p-8'>
                <p className='text-lg font-semibold animate-pulse text-brand'>{statusMessage}</p>
            </div>
        ) : (
            <form onSubmit={submitCore}>
                <div className='space-y-6'>
                    {subjects.map(subject => (
                        <div key={subject} className='py-4 border-t border-border first:border-t-0'>
                            <label className='block text-md font-semibold text-primary'>{subject}</label>
                            <p className='text-sm text-secondary mb-3'>Arraste para indicar seu nível, de iniciante a avançado.</p>
                            <input
                                type='range'
                                min='0'
                                max='1'
                                step='0.1'
                                value={proficiencies[subject] ?? 0.5}
                                onChange={(e) => handleProficiencyChange(subject, parseFloat(e.target.value))}
                                className='w-full h-2 bg-border rounded-lg appearance-none cursor-pointer accent-brand'
                            />
                            <div className='flex justify-between text-xs text-secondary mt-1 px-1'>
                                <span>Iniciante</span>
                                <span>Intermediário</span>
                                <span>Avançado</span>
                            </div>
                        </div>
                    ))}
                </div>

                {error && !isDuplicateSubmission && <p className='text-sm text-red-600 text-center mt-4'>{error}</p>}
                
                <div className='pt-6'>
                    <Button type='submit' disabled={isSubmitting}>
                        Salvar e Gerar Meu Plano de Estudos
                    </Button>
                </div>
            </form>
        )}
      </div>
    </div>
  );
}

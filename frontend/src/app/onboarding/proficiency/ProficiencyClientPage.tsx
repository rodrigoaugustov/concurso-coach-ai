'use client';

import { useEffect, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { Button } from '@/components/ui/Button';

// Tipo para armazenar a proficiência de cada matéria
type ProficiencyState = {
  [subject: string]: number;
};

export default function ProficiencyClientPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const userContestId = searchParams.get('user_contest_id');

  const [subjects, setSubjects] = useState<string[]>([]);
  const [proficiencies, setProficiencies] = useState<ProficiencyState>({});
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [statusMessage, setStatusMessage] = useState('Carregando matérias...');

  useEffect(() => {
    if (!userContestId) {
      setError('ID da inscrição não encontrado. Por favor, comece o processo novamente.');
      setIsLoading(false);
      return;
    }

    const fetchSubjects = async () => {
      try {
        const token = localStorage.getItem('accessToken');
        const apiUrl = process.env.NEXT_PUBLIC_API_URL;

        const response = await fetch(`${apiUrl}/study/user-contests/${userContestId}/subjects`, {
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
        }, {});
        setProficiencies(initialProficiencies);

      } catch (err) {
        if (err instanceof Error) setError(err.message);
      } finally {
        setIsLoading(false);
      }
    };

    fetchSubjects();
  }, [userContestId]);

  const handleProficiencyChange = (subject: string, value: number) => {
    setProficiencies(prev => ({ ...prev, [subject]: value }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setError('');

    if (!userContestId) {
      setError("ID da inscrição não encontrado.");
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
      
      setStatusMessage("Salvando sua avaliação...");
      const proficiencyPayload = {
          proficiencies: Object.entries(proficiencies).map(([subject, score]) => ({
              subject,
              score,
          })),
      };
      const proficiencyResponse = await fetch(`${apiUrl}/study/user-contests/${userContestId}/proficiency`, {
          method: 'POST',
          headers: headers,
          body: JSON.stringify(proficiencyPayload),
      });

      if (!proficiencyResponse.ok) {
          throw new Error('Falha ao salvar sua autoavaliação.');
      }
      
      setStatusMessage("Gerando seu plano de estudos personalizado com a IA... (Isso pode levar até um minuto)");
      const planResponse = await fetch(`${apiUrl}/study/user-contests/${userContestId}/generate-plan`, {
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
        <div className="flex items-center justify-center min-h-screen">
            <p>{statusMessage}</p>
        </div>
    );
  }

  return (
    <div className="flex items-center justify-center min-h-screen bg-background py-12">
      <div className="w-full max-w-2xl p-8 space-y-6 bg-surface rounded-xl shadow-md">
        <div className="text-center">
          <h1 className="text-3xl font-extrabold text-primary">Autoavaliação de Conhecimento</h1>
          <p className="mt-2 text-md text-secondary">Seja honesto! Isso é crucial para criarmos o melhor plano para você.</p>
        </div>
        
        {isSubmitting ? (
             <div className="text-center p-8">
                <p className="text-lg font-semibold animate-pulse text-brand">{statusMessage}</p>
            </div>
        ) : (
            <form onSubmit={handleSubmit}>
                <div className="space-y-6">
                    {subjects.map(subject => (
                        <div key={subject} className="py-4 border-t border-border first:border-t-0">
                            <label className="block text-md font-semibold text-primary">{subject}</label>
                            <p className="text-sm text-secondary mb-3">Arraste para indicar seu nível, de iniciante a avançado.</p>
                            <input
                                type="range"
                                min="0"
                                max="1"
                                step="0.1"
                                value={proficiencies[subject] ?? 0.5}
                                onChange={(e) => handleProficiencyChange(subject, parseFloat(e.target.value))}
                                className="w-full h-2 bg-border rounded-lg appearance-none cursor-pointer accent-brand"
                            />
                            <div className="flex justify-between text-xs text-secondary mt-1 px-1">
                                <span>Iniciante</span>
                                <span>Intermediário</span>
                                <span>Avançado</span>
                            </div>
                        </div>
                    ))}
                </div>

                {error && <p className="text-sm text-red-600 text-center mt-4">{error}</p>}
                
                <div className="pt-6">
                    <Button type="submit" disabled={isSubmitting}>
                        Salvar e Gerar Meu Plano de Estudos
                    </Button>
                </div>
            </form>
        )}
      </div>
    </div>
  );
}
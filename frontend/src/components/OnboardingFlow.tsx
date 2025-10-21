// src/components/OnboardingFlow.tsx
'use client';

import { useEffect, useState } from 'react';
import { Select } from '@/components/ui/Select';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/Button';

// Vamos definir os tipos de dados que esperamos da API
interface ContestRole {
    id: number;
    job_title: string;
}

interface Contest {
    id: number;
    name: string;
    roles: ContestRole[];
}

export default function OnboardingFlow() {
    const [contests, setContests] = useState<Contest[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState('');
    const [selectedContestId, setSelectedContestId] = useState<number | null>(null);

    useEffect(() => {
        const fetchContests = async () => {
            try {
                const token = localStorage.getItem('accessToken');
                const apiUrl = process.env.NEXT_PUBLIC_API_URL;

                const response = await fetch(`${apiUrl}/contests/`, {
                    headers: { 'Authorization': `Bearer ${token}` },
                });

                if (!response.ok) {
                    throw new Error('Falha ao buscar os concursos disponíveis.');
                }

                const data = await response.json();
                setContests(data);
            } catch (err) {
                if (err instanceof Error) {
                    setError(err.message);
                }
            } finally {
                setIsLoading(false);
            }
        };

        fetchContests();
    }, []);

    const router = useRouter();

    const handleSubscribe = async (roleId: number) => {
        // Reutiliza o estado de loading para feedback visual
        setIsLoading(true);
        setError('');

        try {
            const token = localStorage.getItem('accessToken');
            if (!token) {
                throw new Error('Usuário não autenticado. Por favor, faça o login novamente.');
            }

            const apiUrl = process.env.NEXT_PUBLIC_API_URL;

            const response = await fetch(`${apiUrl}/study/subscribe/${roleId}`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                },
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Falha ao se inscrever no cargo.');
            }

            const subscriptionData = await response.json();
            console.log("Inscrição bem-sucedida:", subscriptionData);

            // Após o sucesso, redireciona para a página de proficiência, 
            // passando o ID da inscrição como um parâmetro de busca na URL.
            router.push(`/onboarding/proficiency?user_contest_id=${subscriptionData.id}`);

        } catch (err) {
            if (err instanceof Error) {
                setError(err.message);
            } else {
                setError("Ocorreu um erro desconhecido durante a inscrição.");
            }
        } finally {
            // Definimos isLoading como false aqui, embora o redirecionamento vá desmontar o componente.
            // É uma boa prática para cobrir casos onde o redirecionamento possa falhar.
            setIsLoading(false);
        }
    };

    if (isLoading) return <p>Buscando concursos disponíveis...</p>;
    if (error) return <p className="text-red-600">{error}</p>;
    if (contests.length === 0) return <p>Nenhum concurso processado disponível no momento.</p>;

    const selectedContest = contests.find(c => c.id === selectedContestId);

    return (
        <div className="bg-surface p-8 rounded-xl shadow-md space-y-8 max-w-2xl mx-auto">
            <div className="text-center">
                <h2 className="text-3xl font-extrabold text-primary">Comece sua Jornada</h2>
                <p className="mt-2 text-md text-secondary">Selecione o concurso e o cargo que você irá conquistar.</p>
            </div>

            {isLoading && <p className="text-center text-secondary">Buscando concursos disponíveis...</p>}
            {error && <p className="text-center text-red-600 font-medium">{error}</p>}
            {!isLoading && contests.length === 0 && <p className="text-center text-secondary">Nenhum concurso processado disponível no momento.</p>}

            {contests.length > 0 && (
                <div className="space-y-8">
                    {/* --- Seletor de Concurso --- */}
                    <div className="space-y-2">
                        <label htmlFor="contest-select" className="block text-lg font-semibold text-primary">
                            1. Selecione o Concurso Desejado
                        </label>
                        <Select
                            id="contest-select"
                            value={selectedContestId || ''}
                            onChange={(e) => setSelectedContestId(e.target.value ? Number(e.target.value) : null)}
                        >
                            <option value="">-- Escolha um concurso --</option>
                            {contests.map((contest) => (
                                <option key={contest.id} value={contest.id}>
                                    {contest.name}
                                </option>
                            ))}
                        </Select>
                    </div>

                    {/* --- Lista de Cargos --- */}
                    {selectedContest && (
                        <div className="space-y-4 animate-fade-in">
                            <h3 className="text-lg font-semibold text-primary">2. Escolha o Cargo</h3>
                            <ul className="space-y-3">
                                {selectedContest.roles.map((role) => (
                                    <li key={role.id} className="p-4 bg-surface-muted rounded-lg flex items-center justify-between transition hover:bg-indigo-100">
                                        <span className="font-semibold text-primary">{role.job_title}</span>
                                        <Button
                                            onClick={() => handleSubscribe(role.id)}
                                        >
                                            Selecionar
                                        </Button>
                                    </li>
                                ))}
                            </ul>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}
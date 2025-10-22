// src/components/OnboardingFlow.tsx
'use client';

import { useEffect, useMemo, useState } from 'react';
import { Select } from '@/components/ui/Select';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/Button';

// Tipos conforme API /study/available-roles (tornando contest opcional para robustez)
interface ContestBase { id: number; name: string }
interface ContestRole { id: number; job_title: string; contest?: ContestBase }

export default function OnboardingFlow() {
    const [roles, setRoles] = useState<ContestRole[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState('');
    const [selectedContestId, setSelectedContestId] = useState<number | ''>('');

    useEffect(() => {
        const fetchAvailableRoles = async () => {
            try {
                const token = localStorage.getItem('accessToken');
                const apiUrl = process.env.NEXT_PUBLIC_API_URL;
                const res = await fetch(`${apiUrl}/study/available-roles`, {
                    headers: { 'Authorization': `Bearer ${token}` },
                });
                if (!res.ok) throw new Error('Falha ao buscar cargos disponíveis para inscrição.');
                const raw = await res.json();
                // Normaliza/filtra itens inválidos (sem contest)
                const normalized: ContestRole[] = Array.isArray(raw)
                  ? raw.filter((r: any) => r && r.contest && typeof r.contest.id === 'number' && typeof r.contest.name === 'string')
                  : [];
                setRoles(normalized);
            } catch (e) {
                setError(e instanceof Error ? e.message : 'Erro ao carregar cargos disponíveis.');
            } finally {
                setIsLoading(false);
            }
        };
        fetchAvailableRoles();
    }, []);

    const router = useRouter();

    const contests = useMemo(() => {
        const map = new Map<number, string>();
        roles.forEach(r => {
            const cid = r?.contest?.id;
            const cname = r?.contest?.name;
            if (typeof cid === 'number' && typeof cname === 'string') {
                map.set(cid, cname);
            }
        });
        return Array.from(map.entries()).map(([id, name]) => ({ id, name }));
    }, [roles]);

    const filteredRoles = useMemo(() => {
        if (!selectedContestId) return [] as ContestRole[];
        const sel = Number(selectedContestId);
        return roles.filter(r => r?.contest?.id === sel);
    }, [roles, selectedContestId]);

    const handleSubscribe = async (roleId: number) => {
        setIsLoading(true);
        setError('');
        try {
            const token = localStorage.getItem('accessToken');
            if (!token) throw new Error('Usuário não autenticado. Faça login novamente.');
            const apiUrl = process.env.NEXT_PUBLIC_API_URL;
            const response = await fetch(`${apiUrl}/study/subscribe/${roleId}`, {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
            });

            if (response.status === 409) {
                setError('Você já está inscrito neste cargo. Acesse suas inscrições no painel principal.');
                return;
            }

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.detail || 'Falha ao se inscrever no cargo.');
            }

            const subscriptionData = await response.json();
            router.push(`/onboarding/proficiency?user_contest_id=${subscriptionData.id}`);
        } catch (e) {
            setError(e instanceof Error ? e.message : 'Ocorreu um erro desconhecido durante a inscrição.');
        } finally {
            setIsLoading(false);
        }
    };

    if (isLoading) return <p>Carregando cargos disponíveis...</p>;
    if (error) return <p className="text-red-600">{error}</p>;
    if (roles.length === 0) return <p>Não há cargos disponíveis para nova inscrição no momento.</p>;

    return (
        <div className="bg-surface p-8 rounded-xl shadow-md space-y-8 max-w-2xl mx-auto">
            <div className="text-center">
                <h2 className="text-3xl font-extrabold text-primary">Comece sua Jornada</h2>
                <p className="mt-2 text-md text-secondary">Selecione o concurso e o cargo disponíveis para inscrição.</p>
            </div>

            <div className="space-y-2">
                <label htmlFor="contest-select" className="block text-lg font-semibold text-primary">
                    1. Selecione o Concurso
                </label>
                <Select
                    id="contest-select"
                    value={selectedContestId}
                    onChange={(e) => setSelectedContestId(e.target.value ? Number(e.target.value) : '')}
                >
                    <option value="">-- Escolha um concurso --</option>
                    {contests.map(c => (
                        <option key={c.id} value={c.id}>{c.name}</option>
                    ))}
                </Select>
            </div>

            {selectedContestId && (
                <div className="space-y-4 animate-fade-in">
                    <h3 className="text-lg font-semibold text-primary">2. Escolha o Cargo</h3>
                    <ul className="space-y-3">
                        {filteredRoles.map(role => (
                            <li key={role.id} className="p-4 bg-surface-muted rounded-lg flex items-center justify-between transition hover:bg-indigo-100">
                                <span className="font-semibold text-primary">{role.job_title}</span>
                                <Button onClick={() => handleSubscribe(role.id)}>
                                    Selecionar
                                </Button>
                            </li>
                        ))}
                    </ul>
                </div>
            )}

            {error && (
                <div className="text-sm text-red-600">
                    {error}
                </div>
            )}
        </div>
    );
}

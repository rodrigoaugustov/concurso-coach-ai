'use client';

import { useEffect, useState } from 'react';
// CORREÇÃO: Adicionamos useParams às importações
import { useRouter, useParams } from 'next/navigation';

import TextBlockComponent from '@/components/study-session/TextBlockComponent';
import CarouselComponent from '@/components/study-session/CarouselComponent';
import FlipCardComponent from '@/components/study-session/FlipCardComponent';
import QuizComponent from '@/components/study-session/QuizComponent';

import type { ProceduralLayout, LayoutItem } from '@/types/study-types';

// CORREÇÃO: O componente agora NÃO recebe props. Isso elimina o erro de tipagem no build.
export default function StudySessionPage() {
    const router = useRouter();
    // CORREÇÃO: Usamos o hook useParams para obter o ID da sessão de forma segura.
    // O TypeScript infere automaticamente que pode ser string ou array de strings,
    // então forçamos para string pois sabemos nossa estrutura de rota.
    const params = useParams();
    const sessionId = params?.session_id as string;

    const [layout, setLayout] = useState<ProceduralLayout | null>(null);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        if (!sessionId) {
            // useParams pode demorar um tick para popular na primeira renderização
            return;
        }

        const getOrGenerateLayout = async () => {
            try {
                const token = localStorage.getItem('accessToken');
                if (!token) {
                    router.push('/sign-in');
                    return;
                }

                const apiUrl = process.env.NEXT_PUBLIC_API_URL;

                const response = await fetch(`${apiUrl}/study/sessions/${sessionId}/generate-layout`, {
                    method: 'POST',
                    headers: {
                        'Authorization': `Bearer ${token}`,
                        'Content-Type': 'application/json'
                    }
                });

                if (!response.ok) {
                    const errorData = await response.json();
                    throw new Error(errorData.detail || "Falha ao carregar o conteúdo da aula.");
                }

                const data: ProceduralLayout = await response.json();
                setLayout(data);

            } catch (err) {
                if (err instanceof Error) {
                    setError(err.message);
                } else {
                    setError("Ocorreu um erro desconhecido.");
                }
            } finally {
                setIsLoading(false);
            }
        };

        getOrGenerateLayout();
    }, [sessionId, router]);

    const renderComponent = (componentData: LayoutItem, index: number) => {
        switch (componentData.component_type) {
            case 'TextBlock':
                return componentData.text_block
                    ? <TextBlockComponent key={index} {...componentData.text_block} />
                    : null;
            case 'Carousel':
                return componentData.carousel
                    ? <CarouselComponent key={index} {...componentData.carousel} />
                    : null;
            case 'FlipCard':
                return componentData.flip_card
                    ? <FlipCardComponent key={index} {...componentData.flip_card} />
                    : null;
            case 'Quiz':
                return componentData.quiz
                    ? <QuizComponent key={index} {...componentData.quiz} />
                    : null;
            default:
                console.warn("Componente desconhecido ou com dados ausentes:", componentData);
                return (
                    <div key={index} className="p-4 my-4 bg-red-100 border border-red-300 rounded-lg">
                        <p className="font-semibold text-red-800">
                            Erro de Renderização: Componente &quot;{componentData.component_type}&quot; não pôde ser exibido.
                        </p>
                        <pre className="mt-2 text-xs text-red-700 bg-red-50 p-2 rounded overflow-auto">
                            {JSON.stringify(componentData, null, 2)}
                        </pre>
                    </div>
                );
        }
    };

    if (isLoading) {
        return (
            <div className="min-h-screen flex items-center justify-center text-center p-4 bg-gray-50">
                <div>
                    <h2 className="text-2xl font-semibold animate-pulse text-indigo-600">Gerando sua aula personalizada...</h2>
                    <p className="mt-2 text-gray-500">A IA está preparando o melhor conteúdo para você. Aguarde um momento.</p>
                </div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="min-h-screen flex items-center justify-center text-center p-4 text-red-600 bg-gray-50">
                <div>
                    <h2 className="text-2xl font-bold">Erro ao Carregar a Aula</h2>
                    <p className="mt-2">{error}</p>
                    <button
                        onClick={() => window.location.reload()}
                        className="mt-4 px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700"
                    >
                        Tentar Novamente
                    </button>
                </div>
            </div>
        );
    }

    if (!layout || layout.layout.length === 0) {
        return <div className="min-h-screen flex items-center justify-center bg-gray-50 text-gray-500">Não foi possível carregar o conteúdo desta aula.</div>;
    }

    return (
        <div className="bg-background min-h-screen">
            <div className="max-w-4xl mx-auto py-16 px-4 sm:px-6 lg:px-8">
                <div className="text-center mb-16">
                    <h1 className="text-4xl sm:text-5xl font-extrabold tracking-tight text-gray-900">
                        Sessão de Foco {layout.session_number !== undefined ? `#${layout.session_number + 1}` : ''}
                        {layout.title && `: ${layout.title}`}
                    </h1>
                    <p className="mt-4 text-lg text-gray-700">
                        Concentre-se no conteúdo abaixo para maximizar seu aprendizado.
                    </p>
                </div>
                <div className="space-y-12">
                    {layout.layout.map((component, index) => renderComponent(component, index))}
                </div>
            </div>
        </div>
    );
}
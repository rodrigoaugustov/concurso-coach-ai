// src/app/onboarding/proficiency/page.tsx

import { Suspense } from 'react';
import ProficiencyClientPage from './ProficiencyClientPage';

// Componente de carregamento para o Suspense
function Loading() {
  return (
    <div className="flex items-center justify-center min-h-screen bg-gray-50">
      <p className="text-gray-500">Carregando formulário de avaliação...</p>
    </div>
  );
}

export default function ProficiencyPage({ searchParams }: { searchParams: { user_contest_id?: string } }) {
  const initialId = searchParams?.user_contest_id ?? null;
  return (
    <Suspense fallback={<Loading />}>
      {/* Passa o ID via prop para o Client Component para evitar useSearchParams() */}
      <ProficiencyClientPage initialId={initialId} />
    </Suspense>
  );
}

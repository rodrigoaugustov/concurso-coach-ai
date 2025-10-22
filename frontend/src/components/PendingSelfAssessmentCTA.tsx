'use client';

import Link from 'next/link';
import { Button } from '@/components/ui/Button';
import type { UserSubscription } from '@/types/study-types';

interface PendingSelfAssessmentCTAProps {
  pendingAssessments: UserSubscription[];
  className?: string;
}

export default function PendingSelfAssessmentCTA({ 
  pendingAssessments, 
  className = "" 
}: PendingSelfAssessmentCTAProps) {
  if (pendingAssessments.length === 0) {
    return null;
  }

  return (
    <div className={`bg-amber-50 border border-amber-200 rounded-lg p-6 ${className}`}>
      <div className="flex items-start">
        <div className="flex-shrink-0">
          <svg className="h-5 w-5 text-amber-400" viewBox="0 0 20 20" fill="currentColor">
            <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
          </svg>
        </div>
        <div className="ml-3 flex-1">
          <h3 className="text-sm font-medium text-amber-800">
            {pendingAssessments.length === 1 
              ? 'Autoavaliação Pendente' 
              : `${pendingAssessments.length} Autoavaliações Pendentes`
            }
          </h3>
          <div className="mt-2 text-sm text-amber-700">
            <p className="mb-3">
              {pendingAssessments.length === 1
                ? 'Você tem uma inscrição que ainda não foi avaliada. Complete sua autoavaliação para gerar o plano de estudos personalizado.'
                : 'Você tem inscrições que ainda não foram avaliadas. Complete as autoavaliações para gerar seus planos de estudos personalizados.'
              }
            </p>
            
            {/* Lista das inscrições pendentes */}
            <div className="space-y-3">
              {pendingAssessments.map((subscription) => (
                <div key={subscription.id} className="bg-white rounded-md p-4 border border-amber-200">
                  <div className="flex items-center justify-between">
                    <div className="flex-1">
                      <h4 className="font-medium text-amber-900">
                        {subscription.role.contest.name}
                      </h4>
                      <p className="text-sm text-amber-600">
                        Cargo: {subscription.role.job_title}
                      </p>
                    </div>
                    <div className="ml-4">
                      <Link 
                        href={`/onboarding/proficiency?user_contest_id=${subscription.id}`}
                        passHref
                      >
                        <Button 
                          size="sm" 
                          className="bg-amber-600 hover:bg-amber-700 text-white font-medium px-4 py-2 rounded-md transition-colors"
                        >
                          Preencher Autoavaliação
                        </Button>
                      </Link>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
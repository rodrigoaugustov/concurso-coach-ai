// Em frontend/src/app/onboarding/start/page.tsx
import OnboardingFlow from '@/components/OnboardingFlow';

export default function StartOnboardingPage() {
    // Esta página simplesmente renderiza o fluxo de onboarding
    return (
        <div className="min-h-screen bg-gray-50 flex items-center justify-center py-12">
            <OnboardingFlow />
        </div>
    );
}
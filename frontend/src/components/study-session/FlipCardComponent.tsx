// src/components/study-session/FlipCardComponent.tsx
'use client';

import { useState } from 'react';

interface FlipCardProps {
  front_text: string;
  back_text: string;
}

export default function FlipCardComponent({ front_text, back_text }: FlipCardProps) {
  const [isFlipped, setIsFlipped] = useState(false);

  return (
    <div 
      className="w-full max-w-lg h-64 [perspective:1000px] cursor-pointer group transition-all duration-300 hover:-translate-y-1 hover:shadow-lg"
      onClick={() => setIsFlipped(!isFlipped)}
    >
      <div
        className="relative w-full h-full text-center transition-transform duration-700 [transform-style:preserve-3d]"
        style={{ transform: isFlipped ? 'rotateY(180deg)' : 'rotateY(0deg)' }}
      >
        {/* Frente */}
        <div className="absolute w-full h-full p-6 bg-surface border rounded-xl shadow-md flex items-center justify-center [backface-visibility:hidden]">
          <p className="text-xl font-semibold text-gray-900">{front_text}</p>
        </div>
        {/* Verso */}
        <div className="absolute w-full h-full p-6 bg-indigo-50 border border-indigo-200 rounded-xl shadow-md flex items-center justify-center [transform:rotateY(180deg)] [backface-visibility:hidden]">
          <p className="text-base text-gray-700">{back_text}</p>
        </div>
      </div>
    </div>
  );
}

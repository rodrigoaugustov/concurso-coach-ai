// src/components/study-session/CarouselComponent.tsx
'use client';
import { useState } from 'react';

interface CarouselItem {
  title: string;
  content: string;
}

interface CarouselProps {
  items: CarouselItem[];
}

export default function CarouselComponent({ items }: CarouselProps) {
  const [currentIndex, setCurrentIndex] = useState(0);

  const goToPrevious = () => {
    const isFirstSlide = currentIndex === 0;
    const newIndex = isFirstSlide ? items.length - 1 : currentIndex - 1;
    setCurrentIndex(newIndex);
  };

  const goToNext = () => {
    const isLastSlide = currentIndex === items.length - 1;
    const newIndex = isLastSlide ? 0 : currentIndex + 1;
    setCurrentIndex(newIndex);
  };

  if (!items || items.length === 0) return null;

  return (
    <div className="relative p-8 bg-surface rounded-xl shadow-md border overflow-hidden">
      <div className="text-center min-h-[12rem] flex flex-col justify-center px-12">
        <h3 className="text-2xl font-bold text-gray-900">{items[currentIndex].title}</h3>
        <p className="mt-2 text-base text-gray-700">{items[currentIndex].content}</p>
      </div>

      {/* Navegação */}
      <button
        onClick={goToPrevious}
        className="absolute top-1/2 left-4 -translate-y-1/2 bg-gray-200/70 hover:bg-gray-300 p-2 rounded-full shadow-md transition"
        aria-label="Slide anterior"
      >
        <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" /></svg>
      </button>
      <button
        onClick={goToNext}
        className="absolute top-1/2 right-4 -translate-y-1/2 bg-gray-200/70 hover:bg-gray-300 p-2 rounded-full shadow-md transition"
        aria-label="Próximo slide"
      >
        <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" /></svg>
      </button>

      {/* Indicadores de Posição */}
      <div className="absolute bottom-4 left-1/2 -translate-x-1/2 flex gap-2">
        {items.map((_, index) => (
          <div
            key={index}
            className={`h-2 w-2 rounded-full transition-colors ${currentIndex === index ? 'bg-brand' : 'bg-border'}`}
          />
        ))}
      </div>
    </div>
  );
}
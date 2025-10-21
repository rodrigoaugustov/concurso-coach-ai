// src/components/study-session/TextBlockComponent.tsx
import ReactMarkdown from 'react-markdown';

interface TextBlockProps {
  content_md: string;
}

export default function TextBlockComponent({ content_md }: TextBlockProps) {
  return (
    <article 
      className="prose prose-lg max-w-none p-8 bg-surface rounded-xl shadow-md border prose-headings:text-gray-900 prose-p:text-gray-700 prose-a:text-brand"
    >
      <ReactMarkdown>{content_md}</ReactMarkdown>
    </article>
  );
}
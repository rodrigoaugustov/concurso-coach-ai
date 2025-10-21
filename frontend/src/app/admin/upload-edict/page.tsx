'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Label } from '@/components/ui/Label';

export default function UploadEdictPage() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error' | 'info'; text: string } | null>(null);
  const router = useRouter();

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    if (event.target.files && event.target.files.length > 0) {
      setSelectedFile(event.target.files[0]);
      setMessage(null);
    }
  };

  const handleUpload = async () => {
    if (!selectedFile) {
      setMessage({ type: 'error', text: 'Por favor, selecione um arquivo PDF para upload.' });
      return;
    }

    setUploading(true);
    setMessage(null);

    const token = localStorage.getItem('accessToken');
    if (!token) {
      router.push('/sign-in');
      return;
    }

    const formData = new FormData();
    formData.append('file', selectedFile);

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL;
      const response = await fetch(`${apiUrl}/contests/upload`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          // 'Content-Type': 'multipart/form-data' // Fetch API sets this automatically with FormData
        },
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Falha no upload do edital.');
      }

      const result = await response.json();
      setMessage({ type: 'success', text: `Edital '${result.name}' enviado com sucesso! ID: ${result.id}. Processamento iniciado.` });
      setSelectedFile(null); // Clear selected file

    } catch (err) {
      if (err instanceof Error) {
        setMessage({ type: 'error', text: err.message });
      } else {
        setMessage({ type: 'error', text: 'Ocorreu um erro desconhecido durante o upload.' });
      }
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="min-h-screen bg-background flex flex-col items-center py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8 bg-white p-10 rounded-xl shadow-lg border border-gray-200">
        <div>
          <h2 className="mt-6 text-center text-3xl font-extrabold text-gray-900">
            Upload de Edital de Concurso
          </h2>
          <p className="mt-2 text-center text-sm text-gray-600">
            Envie um arquivo PDF para extração de dados e cadastro de novo concurso.
          </p>
        </div>

        <div className="space-y-4">
          <div>
            <Label htmlFor="edict-file" className="block text-sm font-medium text-gray-700">Arquivo do Edital (PDF)</Label>
            <Input
              id="edict-file"
              name="edict-file"
              type="file"
              accept=".pdf"
              onChange={handleFileChange}
              className="mt-1 block w-full text-sm text-gray-500
                file:mr-4 file:py-2 file:px-4
                file:rounded-md file:border-0
                file:text-sm file:font-semibold
                file:bg-indigo-50 file:text-indigo-600
                hover:file:bg-indigo-100"
            />
            {selectedFile && <p className="mt-2 text-sm text-gray-500">Arquivo selecionado: {selectedFile.name}</p>}
          </div>

          <Button
            onClick={handleUpload}
            disabled={!selectedFile || uploading}
            className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
          >
            {uploading ? 'Enviando...' : 'Fazer Upload e Processar'}
          </Button>
        </div>

        {message && (
          <div className={`p-3 rounded-md text-sm ${message.type === 'success' ? 'bg-green-100 text-green-800' : message.type === 'error' ? 'bg-red-100 text-red-800' : 'bg-blue-100 text-blue-800'}`}>
            {message.text}
          </div>
        )}
      </div>
    </div>
  );
}

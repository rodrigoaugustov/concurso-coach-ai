'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation'; // Hook para redirecionamento

export default function SignInPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const router = useRouter();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL;
      
      // O endpoint /token espera dados de formulário (x-www-form-urlencoded)
      const params = new URLSearchParams();
      params.append('username', email);
      params.append('password', password);

      const response = await fetch(`${apiUrl}/token`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: params,
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Email ou senha incorretos.');
      }

      const data = await response.json();
      
      // SALVANDO O TOKEN: Por simplicidade, usaremos localStorage.
      // Em uma aplicação real, usaríamos cookies (httpOnly) ou um gerenciador de estado.
      localStorage.setItem('accessToken', data.access_token);
      
      // Redireciona para uma página de dashboard (que ainda não criamos)
      router.push('/dashboard');

    } catch (err) {
      if (err instanceof Error) {
        setError(err.message);
    } else {
        setError('Ocorreu um erro desconhecido.');
    }
    }
  };

  return (
    <div className="flex items-center justify-center min-h-screen bg-gray-100">
      <div className="w-full max-w-md p-8 space-y-6 bg-white rounded-lg shadow-md">
        <h1 className="text-2xl font-bold text-center text-gray-900">Acessar sua Conta</h1>
        <form onSubmit={handleSubmit} className="space-y-6">
          <div>
            <label htmlFor="email" className="text-sm font-medium text-gray-700">Email</label>
            <input
              id="email"
              name="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full px-3 py-2 mt-1 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
            />
          </div>
          <div>
            <label htmlFor="password" className="text-sm font-medium text-gray-700">Senha</label>
            <input
              id="password"
              name="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-3 py-2 mt-1 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
            />
          </div>
          
          {error && <p className="text-sm text-red-600">{error}</p>}

          <div>
            <button
              type="submit"
              className="w-full px-4 py-2 font-medium text-white bg-indigo-600 rounded-md hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
            >
              Entrar
            </button>
          </div>
        </form>
        <p className="text-sm text-center text-gray-600">
          Não tem uma conta?{' '}
          <Link href="/sign-up" className="font-medium text-indigo-600 hover:text-indigo-500">
            Cadastre-se
          </Link>
        </p>
      </div>
    </div>
  );
}
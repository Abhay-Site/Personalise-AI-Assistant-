import type { Metadata } from 'next';
import './globals.css';
import { Sidebar } from '@/components/Sidebar';

export const metadata: Metadata = {
  title: 'Personal AI Assistant — AI Productivity Agent',
  description: 'An observable, memory-augmented AI productivity agent for Gmail, Calendar, and Drive.',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className="flex h-screen overflow-hidden bg-[#0f1117] text-slate-200">
        {/* Sidebar navigation */}
        <Sidebar />

        {/* Main content area */}
        <main className="flex-1 flex flex-col overflow-hidden">
          {children}
        </main>
      </body>
    </html>
  );
}

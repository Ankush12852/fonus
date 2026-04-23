import type { Metadata } from 'next';
import { JetBrains_Mono } from 'next/font/google';
import './globals.css';

const jetbrainsMono = JetBrains_Mono({
  subsets: ['latin'],
  variable: '--font-jetbrains',
});

export const metadata: Metadata = {
  title: 'Fonus — DGCA AME Exam Coach',
  description:
    'AI-powered exam preparation for DGCA AME license. Covers all CAR 66 modules with official source documents.',
  keywords: 'DGCA AME exam, CAR 66, aviation maintenance engineer, exam preparation',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={`${jetbrainsMono.variable}`}>
      <body>{children}</body>
    </html>
  );
}

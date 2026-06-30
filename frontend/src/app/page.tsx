'use client';

import { PdfLibrary } from '@/components/pdf/PdfLibrary';
import { LandingHero } from '@/components/landing/LandingHero';
import { AppShell } from '@/components/layout/AppShell';
import { useHasSession } from '@/hooks/useSession';

export default function Home() {
  const hasSession = useHasSession();

  return <AppShell>{hasSession ? <PdfLibrary /> : <LandingHero />}</AppShell>;
}

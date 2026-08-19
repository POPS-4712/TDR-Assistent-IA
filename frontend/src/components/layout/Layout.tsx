/**
 * Main Layout component for Automation Center
 */

import { Outlet } from 'react-router-dom';
import { Header } from './Header';
import { Footer } from './Footer';
import { useSystem } from '../../hooks/useSystem';
import { ProfileProvider } from '../../contexts/ProfileContext';
import { FirstRunWizard } from '../onboarding/FirstRunWizard';

export function Layout() {
  const { systemStatus } = useSystem();

  return (
    <ProfileProvider>
      <div className="min-h-screen flex flex-col bg-gray-50">
        <Header systemStatus={systemStatus || undefined} />
        <main className="flex-1 w-full">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
            <Outlet />
          </div>
        </main>
        <Footer />
        <FirstRunWizard />
      </div>
    </ProfileProvider>
  );
}
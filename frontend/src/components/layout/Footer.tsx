/**
 * Footer component for Automation Center
 */

export function Footer() {
  return (
    <footer className="bg-gray-50 border-t border-gray-200 mt-auto">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
        <div className="flex flex-col md:flex-row items-center justify-between space-y-3 md:space-y-0">
          <div className="flex items-center space-x-4 text-sm text-gray-500">
            <span>Automation Center v1.0.0</span>
            <span className="hidden sm:inline">|</span>
            <span>Built with React, FastAPI, n8n & PostgreSQL</span>
          </div>
          <div className="flex items-center space-x-4 text-sm text-gray-500">
            <a href="#" className="hover:text-gray-700">Documentation</a>
            <span className="hidden sm:inline">|</span>
            <a href="#" className="hover:text-gray-700">API Reference</a>
            <span className="hidden sm:inline">|</span>
            <a href="#" className="hover:text-gray-700">Support</a>
          </div>
        </div>
      </div>
    </footer>
  );
}
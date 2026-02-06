import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'Farmers for Forests - Document Verification',
  description: 'AI-powered document verification for farmer onboarding. Supports Hindi, Marathi, and English.',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <div className="min-h-screen">
          {/* Header */}
          <header className="bg-forest-700 text-white shadow-lg">
            <div className="max-w-7xl mx-auto px-4 py-4 sm:px-6 lg:px-8">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  <span className="text-3xl">🌳</span>
                  <div>
                    <h1 className="text-xl font-bold">Farmers for Forests</h1>
                    <p className="text-forest-200 text-sm">Document Verification System</p>
                  </div>
                </div>
                <div className="hidden sm:flex items-center space-x-2 text-forest-200 text-sm">
                  <span>🇮🇳</span>
                  <span>Hindi • Marathi • English</span>
                </div>
              </div>
            </div>
          </header>
          
          {/* Main content */}
          <main>{children}</main>
          
          {/* Footer */}
          <footer className="bg-forest-800 text-forest-200 py-6 mt-auto">
            <div className="max-w-7xl mx-auto px-4 text-center text-sm">
              <p>Built for Cisco Tech for Social Good Hackathon 2026</p>
              <p className="mt-1 text-forest-400">Empowering rural farmers through AI-driven verification</p>
            </div>
          </footer>
        </div>
      </body>
    </html>
  )
}

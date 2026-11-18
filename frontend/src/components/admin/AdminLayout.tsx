import { useState } from 'react'
import { Outlet } from 'react-router-dom'
import { SelectedStoreProvider } from '../../contexts/SelectedStoreContext'
import { Header } from './Header'
import { Sidebar } from './Sidebar'

export function AdminLayout() {
  const [isSidebarOpen, setIsSidebarOpen] = useState(false)

  return (
    <SelectedStoreProvider>
      <div className="flex min-h-screen bg-gray-50">
        <Sidebar isOpen={isSidebarOpen} onClose={() => setIsSidebarOpen(false)} />
        <div className="flex w-full min-w-0 flex-1 flex-col">
          <Header onOpenSidebar={() => setIsSidebarOpen(true)} />
          <main className="w-full flex-1 overflow-y-auto p-6 sm:p-8">
            <Outlet />
          </main>
        </div>
      </div>
    </SelectedStoreProvider>
  )
}

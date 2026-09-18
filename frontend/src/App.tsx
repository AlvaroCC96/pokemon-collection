import { Route, Routes } from 'react-router-dom'
import { AddCardPage } from './pages/AddCardPage'
import { CardDetailPage } from './pages/CardDetailPage'
import { HomePage } from './pages/HomePage'

export function App() {
  return (
    <Routes>
      <Route path="/" element={<HomePage />} />
      <Route path="/cards/new" element={<AddCardPage />} />
      <Route path="/cards/:id" element={<CardDetailPage />} />
    </Routes>
  )
}

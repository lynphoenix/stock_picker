import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Layout from './components/Layout'
import StrategyWorkspace from './pages/StrategyWorkspace'
import DataMonitoring from './pages/DataMonitoring'
import Chat from './pages/Chat'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Navigate to="/chat" replace />} />
          <Route path="chat" element={<Chat />} />
          <Route path="strategy" element={<StrategyWorkspace />} />
          <Route path="data" element={<DataMonitoring />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}

export default App

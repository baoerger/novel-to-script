import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import ConvertPage from './pages/ConvertPage'
import YamlPreviewPage from './pages/YamlPreviewPage'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<div className="text-center py-20 text-gray-500">欢迎使用 AI 小说转剧本工具</div>} />
          <Route path="convert" element={<ConvertPage />} />
          <Route path="preview/:taskId?" element={<YamlPreviewPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}

export default App

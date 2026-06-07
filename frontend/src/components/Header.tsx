import { Link } from 'react-router-dom'

export default function Header() {
  return (
    <header className="bg-white border-b border-gray-200">
      <div className="max-w-6xl mx-auto px-4 h-14 flex items-center gap-6">
        <Link to="/" className="text-lg font-semibold text-gray-800 hover:text-indigo-600 transition-colors">
          Novel2Script
        </Link>
        <nav className="flex gap-4 text-sm text-gray-600">
          <Link to="/" className="hover:text-indigo-600 transition-colors">首页</Link>
        </nav>
      </div>
    </header>
  )
}

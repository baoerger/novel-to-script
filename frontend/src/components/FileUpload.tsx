import { useRef, useState, type DragEvent, type ChangeEvent } from 'react'

interface Props {
  onFile: (file: File) => void
  accept?: string
}

export default function FileUpload({ onFile, accept = '.txt,.docx' }: Props) {
  const [dragging, setDragging] = useState(false)
  const [filename, setFilename] = useState('')
  const inputRef = useRef<HTMLInputElement>(null)

  const handleFile = (file: File) => {
    setFilename(file.name)
    onFile(file)
  }

  const onDragOver = (e: DragEvent) => { e.preventDefault(); setDragging(true) }
  const onDragLeave = () => setDragging(false)
  const onDrop = (e: DragEvent) => {
    e.preventDefault()
    setDragging(false)
    const file = e.dataTransfer.files[0]
    if (file) handleFile(file)
  }
  const onChange = (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) handleFile(file)
  }

  return (
    <div
      className={`border-2 border-dashed rounded-lg p-10 text-center cursor-pointer transition-colors ${
        dragging ? 'border-indigo-500 bg-indigo-50' : 'border-gray-300 hover:border-gray-400'
      }`}
      onDragOver={onDragOver}
      onDragLeave={onDragLeave}
      onDrop={onDrop}
      onClick={() => inputRef.current?.click()}
    >
      <input ref={inputRef} type="file" accept={accept} onChange={onChange} className="hidden" />
      {filename ? (
        <div>
          <p className="text-sm text-gray-600">已选择文件</p>
          <p className="text-base font-medium text-gray-800 mt-1">{filename}</p>
          <p className="text-xs text-gray-400 mt-2">点击重新选择</p>
        </div>
      ) : (
        <div>
          <p className="text-sm text-gray-500">拖拽文件到此处，或点击选择</p>
          <p className="text-xs text-gray-400 mt-1">支持 .txt / .docx 格式，最大 10MB</p>
        </div>
      )}
    </div>
  )
}

import { useEffect, useState } from 'react'
import { Lightbox } from './Lightbox'

interface MultiPhotoPickerProps {
  id: string
  files: File[]
  onChange: (files: File[]) => void
  requireLiveCapture: boolean
  disabled?: boolean
  requiredLabel: string
}

export function MultiPhotoPicker({ id, files, onChange, requireLiveCapture, disabled, requiredLabel }: MultiPhotoPickerProps) {
  const [previewUrls, setPreviewUrls] = useState<string[]>([])
  const [lightboxIndex, setLightboxIndex] = useState<number | null>(null)

  useEffect(() => {
    const urls = files.map((file) => URL.createObjectURL(file))
    setPreviewUrls(urls)
    return () => {
      urls.forEach((url) => URL.revokeObjectURL(url))
    }
  }, [files])

  function handleFilesSelected(selected: FileList | null): void {
    if (!selected || selected.length === 0) return
    onChange([...files, ...Array.from(selected)])
  }

  function removeAt(index: number): void {
    onChange(files.filter((_, i) => i !== index))
    setLightboxIndex(null)
  }

  return (
    <div className="flex flex-col gap-1.5">
      <input
        id={id}
        type="file"
        accept="image/*"
        multiple
        capture={requireLiveCapture ? 'environment' : undefined}
        onChange={(event) => {
          handleFilesSelected(event.target.files)
          event.target.value = ''
        }}
        disabled={disabled}
        className="hidden"
      />
      <label
        htmlFor={id}
        className="flex cursor-pointer items-center justify-center gap-2 rounded-xl border-2 border-dashed border-emerald-300 bg-emerald-50 px-4 py-4 text-base font-semibold text-emerald-700 transition hover:bg-emerald-100"
      >
        <span className="sr-only">{requiredLabel}</span>
        {files.length > 0 ? 'Adicionar mais fotos' : 'Enviar Foto'}
      </label>

      {previewUrls.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {previewUrls.map((url, index) => (
            <div key={url} className="group relative">
              <button
                type="button"
                onClick={() => setLightboxIndex(index)}
                className="block"
              >
                <img
                  src={url}
                  alt={`Foto selecionada ${index + 1}`}
                  className="h-16 w-16 cursor-zoom-in rounded-lg border border-slate-200 object-cover"
                />
              </button>
              <button
                type="button"
                onClick={() => removeAt(index)}
                disabled={disabled}
                aria-label={`Remover foto ${index + 1}`}
                className="absolute -right-1.5 -top-1.5 flex h-5 w-5 items-center justify-center rounded-full bg-red-500 text-xs font-bold text-white shadow-sm transition hover:bg-red-600 disabled:cursor-not-allowed disabled:opacity-50"
              >
                ✕
              </button>
            </div>
          ))}
        </div>
      )}

      {lightboxIndex !== null && previewUrls[lightboxIndex] && (
        <Lightbox
          src={previewUrls[lightboxIndex]}
          alt={`Foto selecionada ${lightboxIndex + 1}`}
          onClose={() => setLightboxIndex(null)}
        />
      )}
    </div>
  )
}

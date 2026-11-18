import type { ReactNode } from 'react'
import { Modal } from '../Modal'

interface ConfirmDeleteModalProps {
  title: string
  message: ReactNode
  isSubmitting?: boolean
  errorMessage?: string | null
  onConfirm: () => void
  onClose: () => void
}

export function ConfirmDeleteModal({ title, message, isSubmitting, errorMessage, onConfirm, onClose }: ConfirmDeleteModalProps) {
  return (
    <Modal
      title={title}
      onClose={onClose}
      footer={
        <div className="flex justify-end gap-2">
          <button
            type="button"
            onClick={onClose}
            disabled={isSubmitting}
            className="rounded-lg border border-gray-200 px-4 py-2 text-sm font-medium text-gray-600 transition hover:bg-gray-100 disabled:cursor-not-allowed disabled:opacity-50"
          >
            Cancelar
          </button>
          <button
            type="button"
            onClick={onConfirm}
            disabled={isSubmitting}
            className="rounded-lg bg-red-500 px-4 py-2 text-sm font-semibold text-white transition hover:bg-red-600 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {isSubmitting ? 'Excluindo…' : 'Excluir'}
          </button>
        </div>
      }
    >
      <div className="flex flex-col gap-3">
        {errorMessage && (
          <p role="alert" className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-600">
            {errorMessage}
          </p>
        )}
        <p className="text-sm text-gray-600">{message}</p>
      </div>
    </Modal>
  )
}
